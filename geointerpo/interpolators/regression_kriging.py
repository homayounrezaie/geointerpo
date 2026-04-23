"""Regression Kriging (RK): trend model + Kriging of residuals.

Workflow
--------
1. Fit a trend model (sklearn estimator) on (xs, ys[, covariates]) → trend.
2. Compute residuals = observed − trend.
3. Fit ordinary Kriging on the residuals.
4. Prediction = trend_prediction + kriging_prediction_of_residuals.

This separates the deterministic spatial trend from the stochastic variability,
which gives better results when a spatial gradient or covariate explains much
of the variance.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

try:
    from pykrige.ok import OrdinaryKriging
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import GradientBoostingRegressor
except ImportError as e:
    raise ImportError(
        "Install pykrige + scikit-learn: pip install 'geointerpo[kriging]'"
    ) from e

from geointerpo.interpolators.base import BaseInterpolator


class RegressionKrigingInterpolator(BaseInterpolator):
    """Regression Kriging: ML trend + Kriging of residuals.

    trend_model: any sklearn-compatible estimator, or one of:
                 'linear' (Ridge), 'gbm' (GradientBoosting).
    variogram_model: variogram for the residual Kriging step.
    covariates_fn: callable(xs, ys) → ndarray of shape (N, k) for extra features.
    """

    _needs_metric = True
    _supports_local_search = False

    def __init__(
        self,
        trend_model="linear",
        variogram_model: str = "spherical",
        covariates_fn=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.trend_model = trend_model
        self.variogram_model = variogram_model
        self.covariates_fn = covariates_fn
        self._trend = None
        self._kriging = None

    def _make_trend(self):
        if self.trend_model == "linear":
            return Ridge()
        if self.trend_model == "gbm":
            return GradientBoostingRegressor(n_estimators=100, random_state=42)
        return self.trend_model  # assume sklearn estimator

    def _features(self, xs, ys):
        base = np.column_stack([xs, ys])
        if self.covariates_fn is not None:
            base = np.column_stack([base, self.covariates_fn(xs, ys)])
        return base

    def _fit(self, xs, ys, values):
        X = self._features(xs, ys)
        self._trend = self._make_trend()
        self._trend.fit(X, values)
        residuals = values - self._trend.predict(X)
        self._kriging = OrdinaryKriging(
            xs, ys, residuals,
            variogram_model=self.variogram_model,
            verbose=False, enable_plotting=False,
        )

    def _predict(self, xs, ys):
        X = self._features(xs, ys)
        trend_pred = self._trend.predict(X)
        resid_pred, _ = self._kriging.execute("points", xs, ys)
        return trend_pred + np.asarray(resid_pred)

    def predict(self, bbox, resolution: float = 0.1) -> xr.DataArray:
        """Override to reproject grid coordinates before prediction."""
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")
        if self.search_radius is not None:
            return super().predict(bbox, resolution=resolution)

        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs, ys = t.transform(lon_grid.ravel(), lat_grid.ravel())
        values = self._predict(xs, ys).reshape(lat_grid.shape)

        return xr.DataArray(
            values,
            dims=["lat", "lon"],
            coords={"lat": lats, "lon": lons},
            name=self.value_col,
            attrs={"crs": "EPSG:4326"},
        )
