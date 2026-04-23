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

    method:         'gp' (Gaussian Process), 'rf' (Random Forest), 'gbm' (Gradient Boosting)
    covariates:     optional array of shape (n_stations, k) with extra features.
    covariates_fn:  optional callable(xs, ys) -> np.ndarray of shape (N, k)
                    for on-the-fly covariate generation at prediction coordinates.
    """

    _needs_metric = True
    _supports_local_search = False

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

    def predict_with_uncertainty(
        self,
        bbox,
        resolution: float = 0.1,
        alpha: float = 0.1,
    ) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        """Return (mean, lower_bound, upper_bound) DataArrays at (1-alpha) coverage.

        GP:  uses the native posterior standard deviation.
        RF:  uses the distribution of predictions across individual trees
             (bootstrap percentile interval).
        GBM: uses MAPIE conformal prediction if mapie is installed,
             otherwise raises NotImplementedError.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before predict_with_uncertainty()")

        from pyproj import Transformer

        min_lon, min_lat, max_lon, max_lat = bbox
        lons = np.arange(min_lon, max_lon + resolution, resolution)
        lats = np.arange(min_lat, max_lat + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        shape = lat_grid.shape
        coords = {"lat": lats, "lon": lons}

        t = Transformer.from_crs("EPSG:4326", self._proj_crs, always_xy=True)
        xs, ys = t.transform(lon_grid.ravel(), lat_grid.ravel())
        X = self._build_features(xs, ys)

        if self.method == "gp":
            mean_flat, std_flat = self._model.predict(X, return_std=True)
            from scipy import stats as _stats
            z = _stats.norm.ppf(1 - alpha / 2)
            lower_flat = mean_flat - z * std_flat
            upper_flat = mean_flat + z * std_flat

        elif self.method == "rf":
            # Bootstrap interval: gather predictions from every tree
            tree_preds = np.array([tree.predict(X) for tree in self._model.estimators_])
            mean_flat = tree_preds.mean(axis=0)
            lower_flat = np.percentile(tree_preds, (alpha / 2) * 100, axis=0)
            upper_flat = np.percentile(tree_preds, (1 - alpha / 2) * 100, axis=0)

        elif self.method == "gbm":
            try:
                from mapie.regression import MapieRegressor
            except ImportError as e:
                raise ImportError(
                    "GBM uncertainty requires mapie: pip install mapie"
                ) from e
            # MAPIE split-conformal: refit on the training features
            # We reconstruct training features using stored _fit_xs/_fit_ys
            X_train = self._build_features(self._fit_xs, self._fit_ys)
            y_train = self._values
            mapie = MapieRegressor(estimator=self._model.__class__(
                **{k: getattr(self._model, k) for k in
                   ("n_estimators", "learning_rate", "max_depth") if hasattr(self._model, k)}
            ), method="plus", cv=5)
            mapie.fit(X_train, y_train)
            mean_flat, pi = mapie.predict(X, alpha=alpha)
            lower_flat = pi[:, 0, 0]
            upper_flat = pi[:, 1, 0]

        else:
            raise ValueError(f"Unsupported method '{self.method}'")

        def _da(flat, name):
            return xr.DataArray(flat.reshape(shape), dims=["lat", "lon"],
                                coords=coords, name=name, attrs={"crs": "EPSG:4326"})

        return (
            _da(mean_flat, self.value_col),
            _da(lower_flat, f"{self.value_col}_lower"),
            _da(upper_flat, f"{self.value_col}_upper"),
        )
