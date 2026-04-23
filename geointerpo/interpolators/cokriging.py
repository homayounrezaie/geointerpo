"""Cokriging interpolator using gstools (External Drift Kriging).

Requires: pip install gstools

Cokriging uses a secondary correlated variable (e.g. elevation, NDVI, a
climatological normal) to improve primary-variable predictions.  This
implementation uses gstools' ExternalDriftKriging, which is equivalent to
Kriging with External Drift (KED) — a practical form of cokriging that assumes
the secondary variable is known at all prediction locations.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from geointerpo.interpolators.base import BaseInterpolator

try:
    import gstools as gs
except ImportError as e:
    raise ImportError(
        "Cokriging requires gstools: pip install gstools"
    ) from e


class CokrigingInterpolator(BaseInterpolator):
    """Kriging with External Drift — uses a secondary variable to guide interpolation.

    The secondary variable (drift) must be provided at station locations via
    ``secondary_col`` and at prediction locations via ``secondary_fn``.

    Typical use cases:
    - Primary = temperature,     drift = elevation (DEM)
    - Primary = precipitation,   drift = climatological normal
    - Primary = air quality,     drift = population density

    Parameters
    ----------
    secondary_col:  Column in the GeoDataFrame that contains secondary values.
    secondary_fn:   Callable(xs_utm, ys_utm) → 1D array of secondary values at
                    arbitrary UTM prediction locations.  Required for predict().
    variogram_model: 'Gaussian' | 'Spherical' | 'Exponential' | 'Stable' (default 'Gaussian').
    len_scale:      Variogram length scale in metres (default 100 km).
    var:            Variogram sill (default 1.0; auto-scaled to data).
    nugget:         Nugget (measurement error variance, default 0.0).
    fit_variogram:  If True, fit variogram parameters from the data (slower).
    """

    _needs_metric = True

    _MODELS = {
        "gaussian":     gs.Gaussian,
        "spherical":    gs.Spherical,
        "exponential":  gs.Exponential,
        "stable":       gs.Stable,
        "matern":       gs.Matern,
    }

    def __init__(
        self,
        secondary_col: str = "secondary",
        secondary_fn=None,
        variogram_model: str = "Gaussian",
        len_scale: float = 100_000,
        var: float = 1.0,
        nugget: float = 0.0,
        fit_variogram: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.secondary_col = secondary_col
        self.secondary_fn = secondary_fn
        self.variogram_model = variogram_model
        self.len_scale = len_scale
        self.var = var
        self.nugget = nugget
        self.fit_variogram = fit_variogram
        self._krige = None
        self._gs_model = None

    def fit(self, gdf):
        """Override to extract secondary variable before base fit."""
        import geopandas as gpd
        gdf = gdf.to_crs("EPSG:4326")
        if self.secondary_col not in gdf.columns:
            raise ValueError(
                f"Secondary column '{self.secondary_col}' not found. "
                f"Available columns: {list(gdf.columns)}"
            )
        self._secondary_at_stations = gdf[self.secondary_col].to_numpy(dtype=float)
        return super().fit(gdf)

    def _fit(self, xs, ys, values):
        model_cls = self._MODELS.get(self.variogram_model.lower(), gs.Gaussian)
        self._gs_model = model_cls(
            dim=2,
            var=self.var,
            len_scale=self.len_scale,
            nugget=self.nugget,
        )

        if self.fit_variogram:
            # Empirical variogram fitting using gstools
            try:
                bin_edges = np.linspace(0, self.len_scale * 2, 15)
                bin_center, gamma = gs.vario_estimate(
                    (xs, ys), values, bin_edges
                )
                self._gs_model.fit_variogram(bin_center, gamma, nugget=True)
            except Exception:
                pass  # Fall back to user-specified parameters

        self._krige = gs.krige.ExtDrift(
            self._gs_model,
            cond_pos=(xs, ys),
            cond_val=values,
            ext_drift=self._secondary_at_stations,
        )

    def _predict(self, xs, ys):
        if self.secondary_fn is None:
            raise RuntimeError(
                "secondary_fn is required for predict(). "
                "Provide a callable(xs_utm, ys_utm) → secondary_values."
            )
        secondary_at_pred = self.secondary_fn(xs, ys)
        field, _ = self._krige((xs, ys), ext_drift=secondary_at_pred)
        return np.asarray(field)

    def predict_with_variance(self, bbox, resolution: float = 0.1) -> tuple[xr.DataArray, xr.DataArray]:
        """Return (mean, variance) DataArrays — both in WGS-84."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict_with_variance()")
        if self.secondary_fn is None:
            raise RuntimeError("secondary_fn required for predict_with_variance()")

        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        shape = lat_grid.shape

        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs_flat, ys_flat = t.transform(lon_grid.ravel(), lat_grid.ravel())

        secondary_flat = self.secondary_fn(xs_flat, ys_flat)
        field, variance = self._krige((xs_flat, ys_flat), ext_drift=secondary_flat)

        coords = {"lat": lats, "lon": lons}
        mean_da = xr.DataArray(np.asarray(field).reshape(shape), dims=["lat", "lon"],
                               coords=coords, name=self.value_col, attrs={"crs": "EPSG:4326"})
        var_da = xr.DataArray(np.asarray(variance).reshape(shape), dims=["lat", "lon"],
                              coords=coords, name=f"{self.value_col}_variance",
                              attrs={"crs": "EPSG:4326"})
        return mean_da, var_da
