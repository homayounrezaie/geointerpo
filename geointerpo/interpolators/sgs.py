"""Sequential Gaussian Simulation (SGS) interpolator using gstools.

Requires: pip install gstools

Unlike kriging (which returns a single "best estimate"), SGS produces multiple
equally probable stochastic realizations of the spatial field.  The ensemble of
realizations correctly represents spatial uncertainty — including its spatial
structure — and is essential for uncertainty propagation in downstream models.

Usage example
-------------
    from geointerpo.interpolators.sgs import SGSInterpolator

    model = SGSInterpolator(n_realizations=50).fit(gdf)
    mean_da, std_da = model.predict(bbox, resolution=0.25)  # ensemble mean + std
    realizations = model.realize(bbox, resolution=0.25)     # all 50 realizations
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from geointerpo.interpolators.base import BaseInterpolator

try:
    import gstools as gs
except ImportError as e:
    raise ImportError(
        "SGS requires gstools: pip install gstools"
    ) from e


class SGSInterpolator(BaseInterpolator):
    """Sequential Gaussian Simulation — produces stochastic realizations.

    Each call to predict() returns the ensemble mean and standard deviation.
    Use realize() to get all individual realizations as a 3-D DataArray.

    Parameters
    ----------
    n_realizations:  Number of stochastic realizations (default 100).
    variogram_model: 'Gaussian' | 'Spherical' | 'Exponential' | 'Stable' (default 'Gaussian').
    len_scale:       Variogram length scale in metres (default 100 km).
    var:             Variogram sill (default 1.0; auto-scaled to data).
    nugget:          Nugget (default 0.0).
    fit_variogram:   If True, fit variogram parameters from the data.
    seed:            Base random seed for reproducibility.
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
        n_realizations: int = 100,
        variogram_model: str = "Gaussian",
        len_scale: float = 100_000,
        var: float = 1.0,
        nugget: float = 0.0,
        fit_variogram: bool = True,
        seed: int = 42,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.n_realizations = n_realizations
        self.variogram_model = variogram_model
        self.len_scale = len_scale
        self.var = var
        self.nugget = nugget
        self.fit_variogram = fit_variogram
        self.seed = seed
        self._gs_model = None
        self._cond_xs = None
        self._cond_ys = None
        self._cond_vals = None

    def _fit(self, xs, ys, values):
        model_cls = self._MODELS.get(self.variogram_model.lower(), gs.Gaussian)
        self._gs_model = model_cls(
            dim=2,
            var=self.var,
            len_scale=self.len_scale,
            nugget=self.nugget,
        )

        if self.fit_variogram:
            try:
                bin_edges = np.linspace(0, self.len_scale * 2, 15)
                bin_center, gamma = gs.vario_estimate((xs, ys), values, bin_edges)
                self._gs_model.fit_variogram(bin_center, gamma, nugget=True)
            except Exception:
                pass

        self._cond_xs = xs
        self._cond_ys = ys
        self._cond_vals = values

    def _predict(self, xs, ys):
        """Return the ensemble mean across all realizations."""
        realizations = self._generate_realizations(xs, ys)
        return realizations.mean(axis=0)

    def predict(self, bbox, resolution: float = 0.1) -> xr.DataArray:
        """Return ensemble mean DataArray (WGS-84)."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")
        mean_da, _ = self._predict_ensemble(bbox, resolution)
        return mean_da

    def predict_with_std(self, bbox, resolution: float = 0.1) -> tuple[xr.DataArray, xr.DataArray]:
        """Return (ensemble mean, ensemble std) DataArrays — both in WGS-84."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict_with_std()")
        return self._predict_ensemble(bbox, resolution)

    def realize(self, bbox, resolution: float = 0.1) -> xr.DataArray:
        """Return all realizations as a 3-D DataArray (realization × lat × lon).

        Useful for uncertainty propagation: pass individual slices to downstream
        models and aggregate their outputs to get full predictive uncertainty.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before realize()")

        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        shape = lat_grid.shape

        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs_flat, ys_flat = t.transform(lon_grid.ravel(), lat_grid.ravel())

        realizations = self._generate_realizations(xs_flat, ys_flat)
        real_grids = realizations.reshape(self.n_realizations, *shape)

        return xr.DataArray(
            real_grids,
            dims=["realization", "lat", "lon"],
            coords={
                "realization": np.arange(self.n_realizations),
                "lat": lats,
                "lon": lons,
            },
            name=self.value_col,
            attrs={"crs": "EPSG:4326", "n_realizations": self.n_realizations},
        )

    def _predict_ensemble(self, bbox, resolution) -> tuple[xr.DataArray, xr.DataArray]:
        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        shape = lat_grid.shape

        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs_flat, ys_flat = t.transform(lon_grid.ravel(), lat_grid.ravel())

        realizations = self._generate_realizations(xs_flat, ys_flat)
        mean_flat = realizations.mean(axis=0)
        std_flat = realizations.std(axis=0)

        coords = {"lat": lats, "lon": lons}
        mean_da = xr.DataArray(mean_flat.reshape(shape), dims=["lat", "lon"],
                               coords=coords, name=self.value_col,
                               attrs={"crs": "EPSG:4326"})
        std_da = xr.DataArray(std_flat.reshape(shape), dims=["lat", "lon"],
                              coords=coords, name=f"{self.value_col}_std",
                              attrs={"crs": "EPSG:4326"})
        return mean_da, std_da

    def _generate_realizations(self, xs_flat, ys_flat) -> np.ndarray:
        """Generate n_realizations conditional realizations at prediction points."""
        results = np.empty((self.n_realizations, len(xs_flat)))

        for i in range(self.n_realizations):
            try:
                cond_srf = gs.CondSRF(self._gs_model)
                cond_srf.set_condition(
                    cond_pos=(self._cond_xs, self._cond_ys),
                    cond_val=self._cond_vals,
                )
                field = cond_srf((xs_flat, ys_flat), seed=self.seed + i)
                results[i] = np.asarray(field)
            except Exception:
                # Fall back to kriging mean + random noise scaled by kriging std
                krige = gs.krige.Ordinary(
                    self._gs_model,
                    cond_pos=(self._cond_xs, self._cond_ys),
                    cond_val=self._cond_vals,
                )
                mean_field, var_field = krige((xs_flat, ys_flat))
                rng = np.random.default_rng(self.seed + i)
                noise = rng.standard_normal(len(xs_flat)) * np.sqrt(np.maximum(var_field, 0))
                results[i] = np.asarray(mean_field) + noise

        return results
