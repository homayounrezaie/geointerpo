from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import copy
import warnings

import numpy as np
import xarray as xr
import geopandas as gpd
from pyproj import CRS


BBox = Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)

# Methods that require true metric distances (degrees are not meaningful units for them).
_METRIC_METHODS = frozenset(["idw", "rbf", "kriging", "gp"])


def _utm_crs_for_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> CRS:
    """Return the UTM CRS that best covers the centre of a WGS-84 bbox."""
    centre_lon = (min_lon + max_lon) / 2
    centre_lat = (min_lat + max_lat) / 2
    zone = int((centre_lon + 180) / 6) + 1
    hemisphere = "north" if centre_lat >= 0 else "south"
    epsg = 32600 + zone if hemisphere == "north" else 32700 + zone
    return CRS.from_epsg(epsg)


class BaseInterpolator(ABC):
    """Common interface for all interpolators.

    Spatial correctness
    -------------------
    Distance-based methods (IDW, RBF, Kriging, GP) automatically reproject
    input data to a local UTM CRS before fitting and transform prediction
    coordinates back before returning results.  The output DataArray is always
    in WGS-84 lon/lat.

    Cross-validation
    ----------------
    Uses blocked spatial CV: points are sorted by their position on a
    space-filling (H-index approximation via lat*lon sorting) curve, then
    split into k contiguous spatial blocks.  This avoids spatial
    autocorrelation leakage between train and test folds.
    """

    # Subclasses set this to True if they need metric coordinates.
    _needs_metric: bool = False
    _supports_local_search: bool = True

    def __init__(self, value_col: str = "value", search_radius=None):
        self.value_col = value_col
        self.search_radius = search_radius
        self._fitted = False
        self._proj_crs: Optional[CRS] = None
        self._search_crs: Optional[CRS] = None
        self._search_tree = None
        self._search_radius_warned = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, gdf: gpd.GeoDataFrame) -> "BaseInterpolator":
        """Fit on a GeoDataFrame with Point geometry and a scalar value column."""
        if self.value_col not in gdf.columns:
            raise ValueError(f"Column '{self.value_col}' not found in GeoDataFrame")

        gdf = gdf.to_crs("EPSG:4326")
        lons = gdf.geometry.x.to_numpy()
        lats = gdf.geometry.y.to_numpy()
        values = gdf[self.value_col].to_numpy(dtype=float)

        if self._needs_metric:
            self._proj_crs = _utm_crs_for_bbox(lons.min(), lats.min(), lons.max(), lats.max())
            xs, ys = self._project(lons, lats)
        else:
            xs, ys = lons, lats

        self._fit_xs = np.asarray(xs)
        self._fit_ys = np.asarray(ys)
        self._lons = lons
        self._lats = lats
        self._values = values
        self._fit(xs, ys, values)
        self._prepare_local_search(lons, lats)
        self._fitted = True
        return self

    def predict(self, bbox: BBox, resolution: float = 0.1) -> xr.DataArray:
        """Return interpolated grid as xarray.DataArray (WGS-84 lon/lat)."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        if self._needs_metric and self._proj_crs is not None:
            xs, ys = self._project(lon_grid.ravel(), lat_grid.ravel())
        else:
            xs, ys = lon_grid.ravel(), lat_grid.ravel()

        values = self._predict_points(xs, ys, lon_grid.ravel(), lat_grid.ravel())
        grid = values.reshape(lat_grid.shape)
        return xr.DataArray(
            grid,
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            name=self.value_col,
            attrs={"crs": "EPSG:4326"},
        )

    def cross_validate(self, gdf: gpd.GeoDataFrame, k: int = 5) -> dict:
        """Blocked spatial k-fold cross-validation.

        Points are sorted spatially (by lat then lon) before splitting into k
        contiguous blocks, so each fold contains a spatially coherent cluster
        rather than a random scatter.  This gives a more honest estimate of
        generalisation to unsampled locations.
        """
        from geointerpo.validation.metrics import compute_metrics

        gdf = gdf.to_crs("EPSG:4326").reset_index(drop=True)
        lons = gdf.geometry.x.to_numpy()
        lats = gdf.geometry.y.to_numpy()
        values = gdf[self.value_col].to_numpy(dtype=float)

        # Spatial sort: tile into a grid, assign block index per point
        order = np.lexsort((lons, lats))  # sort by lat, break ties by lon
        sorted_idx = np.array_split(order, k)

        preds = np.full_like(values, np.nan)
        for fold_test_idx in sorted_idx:
            train_idx = np.setdiff1d(np.arange(len(gdf)), fold_test_idx)
            if len(train_idx) < 2:
                continue
            clone = copy.deepcopy(self)
            clone.fit(gdf.iloc[train_idx].copy())
            if clone._needs_metric and clone._proj_crs is not None:
                xs_test, ys_test = clone._project(lons[fold_test_idx], lats[fold_test_idx])
            else:
                xs_test, ys_test = lons[fold_test_idx], lats[fold_test_idx]
            preds[fold_test_idx] = clone._predict_points(
                xs_test,
                ys_test,
                lons[fold_test_idx],
                lats[fold_test_idx],
            )

        mask = ~np.isnan(preds)
        return compute_metrics(values[mask], preds[mask])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _project(self, lons: np.ndarray, lats: np.ndarray):
        """Reproject WGS-84 lon/lat → local UTM metres."""
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        return t.transform(lons, lats)

    def _prepare_local_search(self, lons: np.ndarray, lats: np.ndarray) -> None:
        """Build a metric KD-tree for query-time neighbourhood selection."""
        self._search_tree = None
        if self.search_radius is None:
            return
        if not self._supports_local_search:
            if not self._search_radius_warned:
                warnings.warn(
                    f"{type(self).__name__} ignores search_radius and will use all stations.",
                    stacklevel=2,
                )
                self._search_radius_warned = True
            return

        from scipy.spatial import cKDTree

        self._search_crs = self._proj_crs or _utm_crs_for_bbox(
            float(lons.min()), float(lats.min()), float(lons.max()), float(lats.max())
        )
        self._search_xs, self._search_ys = self._search_project(lons, lats)
        pts = np.column_stack([self._search_xs, self._search_ys])
        self._search_tree = cKDTree(pts)

    def _search_project(self, lons: np.ndarray, lats: np.ndarray):
        """Project lon/lat coordinates into the metric search CRS."""
        from pyproj import Transformer

        t = Transformer.from_crs("EPSG:4326", self._search_crs, always_xy=True)
        return t.transform(lons, lats)

    def _predict_points(
        self,
        xs: np.ndarray,
        ys: np.ndarray,
        lons: np.ndarray,
        lats: np.ndarray,
    ) -> np.ndarray:
        """Predict at a list of already-prepared query coordinates."""
        if self.search_radius is None or self._search_tree is None:
            return self._predict(xs, ys)
        return self._predict_with_local_search(xs, ys, lons, lats)

    def _predict_with_local_search(
        self,
        xs: np.ndarray,
        ys: np.ndarray,
        lons: np.ndarray,
        lats: np.ndarray,
    ) -> np.ndarray:
        """Refit a local model per query point using the requested neighbourhood."""
        qx, qy = self._search_project(np.asarray(lons), np.asarray(lats))
        local_model = copy.deepcopy(self)
        local_model.search_radius = None
        local_model._search_tree = None
        results = np.full(len(xs), np.nan, dtype=float)

        for i, (xq, yq) in enumerate(zip(qx, qy)):
            idx = self._local_neighbor_indices(xq, yq)
            if idx.size == 0:
                continue
            try:
                local_model._fit(
                    self._fit_xs[idx],
                    self._fit_ys[idx],
                    self._values[idx],
                )
                pred = local_model._predict(np.asarray([xs[i]]), np.asarray([ys[i]]))
                results[i] = float(np.asarray(pred).reshape(-1)[0])
            except Exception:
                continue
        return results

    def _local_neighbor_indices(self, xq: float, yq: float) -> np.ndarray:
        """Return neighbour indices for one query point in search CRS units."""
        sr = self.search_radius
        if sr is None or self._search_tree is None:
            return np.arange(len(self._values))

        if sr.type == "variable":
            k = max(1, min(int(sr.n), len(self._values)))
            dist, idx = self._search_tree.query([xq, yq], k=k)
            dist = np.atleast_1d(dist)
            idx = np.atleast_1d(idx)
            return idx[np.isfinite(dist)].astype(int, copy=False)

        if sr.type == "fixed":
            if sr.distance_m is None or sr.distance_m <= 0:
                return np.array([], dtype=int)
            idx = self._search_tree.query_ball_point([xq, yq], r=float(sr.distance_m))
            return np.asarray(idx, dtype=int)

        raise ValueError("search_radius.type must be 'variable' or 'fixed'")

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _fit(self, xs: np.ndarray, ys: np.ndarray, values: np.ndarray) -> None:
        """Fit using projected (or lon/lat) coordinates."""
        ...

    @abstractmethod
    def _predict(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        """Predict at projected (or lon/lat) coordinates."""
        ...
