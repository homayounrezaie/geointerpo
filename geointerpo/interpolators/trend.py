"""Trend Surface interpolation — mirrors ArcGIS Trend tool.

Fits a global polynomial of order 1–12 to the input points.  Unlike local
methods, Trend captures broad spatial patterns (gradients, domes) but ignores
local variation.

Two regression types (matching ArcGIS):
  LINEAR  — ordinary least-squares on continuous values.
  LOGISTIC — logistic regression for binary/proportion data (0–1 range).
"""

from __future__ import annotations

import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.pipeline import Pipeline as SKPipeline

from geointerpo.interpolators.base import BaseInterpolator


class TrendInterpolator(BaseInterpolator):
    """Global polynomial trend surface interpolation.

    Equivalent to ArcGIS Spatial Analyst → Trend tool.

    order: polynomial order 1–12 (1 = flat plane, 2 = paraboloid, …).
    regression_type: 'linear' (default) or 'logistic'.
    alpha: Ridge regularisation — prevents ill-conditioning for high orders.
    """

    # Trend is a global model fitted in geographic space; no UTM needed
    # (the degree is the same in any linear coordinate system).
    _needs_metric = False

    def __init__(
        self,
        order: int = 1,
        regression_type: str = "linear",
        alpha: float = 1e-3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not (1 <= order <= 12):
            raise ValueError("order must be between 1 and 12")
        if regression_type not in ("linear", "logistic"):
            raise ValueError("regression_type must be 'linear' or 'logistic'")
        self.order = order
        self.regression_type = regression_type
        self.alpha = alpha
        self._model = None

    def _fit(self, xs, ys, values):
        regressor = (
            Ridge(alpha=self.alpha)
            if self.regression_type == "linear"
            else LogisticRegression(C=1 / self.alpha, max_iter=500)
        )
        self._model = SKPipeline([
            ("poly", PolynomialFeatures(degree=self.order, include_bias=True)),
            ("reg", regressor),
        ])
        X = np.column_stack([xs, ys])
        self._model.fit(X, values)

    def _predict(self, xs, ys):
        X = np.column_stack([xs, ys])
        if self.regression_type == "logistic":
            return self._model.predict_proba(X)[:, 1]
        return self._model.predict(X)

    @property
    def rms_error(self) -> float:
        """RMS residual on training data (mirrors ArcGIS RMS output file)."""
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        X = np.column_stack([self._lons, self._lats])
        pred = self._model.predict(X)
        return float(np.sqrt(np.mean((self._values - pred) ** 2)))
