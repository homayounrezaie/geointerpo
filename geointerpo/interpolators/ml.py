from __future__ import annotations

import numpy as np
import xarray as xr

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
except ImportError as e:
    raise ImportError("Install scikit-learn: pip install 'geointerpo[kriging]'") from e

from geointerpo.interpolators.base import BaseInterpolator


class MLInterpolator(BaseInterpolator):
    """ML-based spatial interpolation (GP / Random Forest / Gradient Boosting).

    Automatically reprojects to UTM for GP so the length-scale is in metres.

    method: 'gp' (Gaussian Process), 'rf' (Random Forest), 'gbm' (Gradient Boosting)
    covariates: optional array of shape (n_stations, k) with extra features.
                Columns must be in the same order when calling predict().
    covariates_fn: optional callable(xs, ys) -> np.ndarray of shape (N, k)
                   for on-the-fly covariate generation at prediction coordinates.
    """

    _needs_metric = True

    def __init__(self, method: str = "gp", covariates: np.ndarray | None = None,
                 covariates_fn=None, model_params: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.method = method
        self.covariates = covariates
        self.covariates_fn = covariates_fn
        self.model_params = model_params or {}
        self._model = None
        self._train_covariates = None

    def _build_features(self, xs, ys, covariates=None):
        base = np.column_stack([xs, ys])
        if covariates is not None:
            base = np.column_stack([base, covariates])
        elif self.covariates_fn is not None:
            extra = self.covariates_fn(xs, ys)
            base = np.column_stack([base, extra])
        return base

    def _fit(self, xs, ys, values):
        X = self._build_features(xs, ys, self.covariates)
        p = self.model_params
        if self.method == "gp":
            # length_scale in UTM metres — 50 km is a reasonable prior for spatial fields
            ls = p.get("length_scale", 50_000)
            kernel = ConstantKernel(1.0) * RBF(length_scale=ls,
                                               length_scale_bounds=(1e3, 1e7)) \
                     + WhiteKernel(noise_level=p.get("noise_level", 0.1))
            self._model = GaussianProcessRegressor(
                kernel=kernel,
                n_restarts_optimizer=p.get("n_restarts_optimizer", 5),
                alpha=p.get("alpha", 1e-10),
                normalize_y=True,
            )
        elif self.method == "rf":
            self._model = RandomForestRegressor(
                n_estimators=p.get("n_estimators", 200),
                max_depth=p.get("max_depth", None),
                random_state=42,
            )
        elif self.method == "gbm":
            self._model = GradientBoostingRegressor(
                n_estimators=p.get("n_estimators", 200),
                learning_rate=p.get("learning_rate", 0.1),
                max_depth=p.get("max_depth", 3),
                random_state=42,
            )
        else:
            raise ValueError(f"Unknown method '{self.method}'. Choose 'gp', 'rf', or 'gbm'.")
        self._model.fit(X, values)

    def _predict(self, xs, ys):
        X = self._build_features(xs, ys)
        return self._model.predict(X)

    def predict_with_std(self, bbox, resolution: float = 0.1):
        """GP only: returns (mean DataArray, std DataArray) — both in WGS-84."""
        if self.method != "gp":
            raise NotImplementedError("predict_with_std only available for method='gp'")
        if not self._fitted:
            raise RuntimeError("Call fit() before predict_with_std()")

        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs, ys = t.transform(lon_grid.ravel(), lat_grid.ravel())
        X = self._build_features(xs, ys)
        mean, std = self._model.predict(X, return_std=True)

        coords = {"lat": lats, "lon": lons}
        mean_da = xr.DataArray(mean.reshape(lat_grid.shape), dims=["lat", "lon"],
                               coords=coords, name=self.value_col,
                               attrs={"crs": "EPSG:4326"})
        std_da = xr.DataArray(std.reshape(lat_grid.shape), dims=["lat", "lon"],
                              coords=coords, name=f"{self.value_col}_std",
                              attrs={"crs": "EPSG:4326"})
        return mean_da, std_da
