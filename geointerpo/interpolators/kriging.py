from __future__ import annotations

import numpy as np
import xarray as xr

from geointerpo.interpolators.base import BaseInterpolator, _utm_crs_for_bbox

try:
    from pykrige.ok import OrdinaryKriging
    from pykrige.uk import UniversalKriging
except ImportError as e:
    raise ImportError("Install pykrige: pip install 'geointerpo[kriging]'") from e


class KrigingInterpolator(BaseInterpolator):
    """Ordinary or Universal Kriging via pykrige.

    Automatically reprojects to UTM so the variogram range is in metres.

    mode: 'ordinary' or 'universal'
    variogram_model: 'linear', 'power', 'gaussian', 'spherical', 'exponential', 'hole-effect'
    nlags: number of variogram lags
    weight: weight variogram by pair count
    """

    _needs_metric = True

    def __init__(
        self,
        mode: str = "ordinary",
        variogram_model: str = "spherical",
        nlags: int = 6,
        weight: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.mode = mode
        self.variogram_model = variogram_model
        self.nlags = nlags
        self.weight = weight
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
            verbose=False,
            enable_plotting=False,
        )

    def _predict(self, xs, ys):
        z, _ = self._model.execute("points", xs, ys)
        return np.asarray(z)

    def predict(self, bbox, resolution: float = 0.1) -> xr.DataArray:
        """Use pykrige's faster native grid execution."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")

        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)

        # Build a metric grid, then pass xs/ys axes to pykrige grid execute
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs_flat, ys_flat = t.transform(lon_grid.ravel(), lat_grid.ravel())

        z, variance = self._model.execute("points", xs_flat, ys_flat)
        da = xr.DataArray(
            np.asarray(z).reshape(lat_grid.shape),
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            name=self.value_col,
            attrs={"crs": "EPSG:4326", "variance": np.asarray(variance).reshape(lat_grid.shape)},
        )
        return da

    @property
    def variogram_parameters(self) -> dict:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        return self._model.variogram_model_parameters
