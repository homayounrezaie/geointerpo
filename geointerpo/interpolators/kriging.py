from __future__ import annotations

import numpy as np
import xarray as xr

from geointerpo.interpolators.base import BaseInterpolator

try:
    from pykrige.ok import OrdinaryKriging
    from pykrige.uk import UniversalKriging
except ImportError as e:
    raise ImportError("Install pykrige: pip install 'geointerpo[kriging]'") from e


class KrigingInterpolator(BaseInterpolator):
    """Ordinary or Universal Kriging via pykrige.

    Automatically reprojects to UTM so the variogram range is in metres.

    mode:                'ordinary' or 'universal'
    variogram_model:     'linear', 'power', 'gaussian', 'spherical', 'exponential', 'hole-effect'
    nlags:               number of variogram lags
    weight:              weight variogram by pair count
    anisotropy_scaling:  ratio of minor to major axis (1.0 = isotropic)
    anisotropy_angle:    angle of major axis in degrees (0 = North, clockwise)
    """

    _needs_metric = True

    def __init__(
        self,
        mode: str = "ordinary",
        variogram_model: str = "spherical",
        nlags: int = 6,
        weight: bool = False,
        anisotropy_scaling: float = 1.0,
        anisotropy_angle: float = 0.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.mode = mode
        self.variogram_model = variogram_model
        self.nlags = nlags
        self.weight = weight
        self.anisotropy_scaling = anisotropy_scaling
        self.anisotropy_angle = anisotropy_angle
        self._model = None

    def _fit(self, xs, ys, values):
        cls = OrdinaryKriging if self.mode == "ordinary" else UniversalKriging
        self._model = cls(
            xs,
            ys,
            values,
            variogram_model=self.variogram_model,
            nlags=self.nlags,
            weight=self.weight,
            anisotropy_scaling=self.anisotropy_scaling,
            anisotropy_angle=self.anisotropy_angle,
            verbose=False,
            enable_plotting=False,
        )

    def _predict(self, xs, ys):
        z, _ = self._model.execute("points", xs, ys)
        return np.asarray(z)

    def predict(self, bbox, resolution: float = 0.1) -> xr.DataArray:
        """Use pykrige's native grid execution for speed."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")
        if self.search_radius is not None:
            return super().predict(bbox, resolution=resolution)

        mean_da, _ = self._predict_grid(bbox, resolution)
        return mean_da

    def predict_with_variance(self, bbox, resolution: float = 0.1) -> tuple[xr.DataArray, xr.DataArray]:
        """Return (mean, variance) DataArrays — both in WGS-84.

        The variance surface shows where the kriging estimate is most uncertain
        (typically highest at locations far from any station).
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before predict_with_variance()")
        return self._predict_grid(bbox, resolution)

    def _predict_grid(self, bbox, resolution: float) -> tuple[xr.DataArray, xr.DataArray]:
        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)

        lon_grid, lat_grid = np.meshgrid(lons, lats)
        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs_flat, ys_flat = t.transform(lon_grid.ravel(), lat_grid.ravel())

        z, variance = self._model.execute("points", xs_flat, ys_flat)
        shape = lat_grid.shape
        coords = {"lat": lats, "lon": lons}

        mean_da = xr.DataArray(
            np.asarray(z).reshape(shape),
            dims=["lat", "lon"],
            coords=coords,
            name=self.value_col,
            attrs={"crs": "EPSG:4326", "variance": np.asarray(variance).reshape(shape)},
        )
        var_da = xr.DataArray(
            np.asarray(variance).reshape(shape),
            dims=["lat", "lon"],
            coords=coords,
            name=f"{self.value_col}_variance",
            attrs={"crs": "EPSG:4326"},
        )
        return mean_da, var_da

    @property
    def variogram_parameters(self) -> dict:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        return self._model.variogram_model_parameters
