"""Bivariate spline interpolation — mirrors ArcGIS Spline tool.

Two variants:
  Regularized (default): minimises curvature → very smooth surface.
  Tension:               pulls surface toward a flat plane → less overshoot.

Both map to scipy SmoothBivariateSpline.  The 'weight' (smoothing) parameter
controls the degree of smoothing vs. fidelity to data points.
"""

from __future__ import annotations

import numpy as np
import numpy as np
from scipy.interpolate import SmoothBivariateSpline

from geointerpo.interpolators.base import BaseInterpolator


class SplineInterpolator(BaseInterpolator):
    """Bivariate spline interpolation (Regularized or Tension).

    Equivalent to ArcGIS Spatial Analyst → Spline tool.

    spline_type: 'regularized' (default) — minimises second-derivative energy.
                 'tension'     — adds a tension term (kx=ky=3, smaller smoothing).
    smoothing: smoothing factor s passed to SmoothBivariateSpline.
               0 = exact interpolation (overfits with noise).
               Larger values = smoother (ArcGIS default weight ≈ 0.1).
    n_points:  minimum number of points in each spline sub-region (ArcGIS: 12).
    """

    _needs_metric = True

    # ArcGIS default weights by type
    _DEFAULT_SMOOTHING = {"regularized": 0.1, "tension": 5.0}

    def __init__(
        self,
        spline_type: str = "regularized",
        smoothing: float | None = None,
        n_points: int = 12,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if spline_type not in ("regularized", "tension"):
            raise ValueError("spline_type must be 'regularized' or 'tension'")
        self.spline_type = spline_type
        self.smoothing = smoothing if smoothing is not None else self._DEFAULT_SMOOTHING[spline_type]
        self.n_points = n_points
        self._spline = None

    def _fit(self, xs, ys, values):
        kx = ky = 3 if self.spline_type == "regularized" else 2
        n = len(xs)
        while kx >= 1 and n < (kx + 1) * (ky + 1):
            kx -= 1
            ky -= 1
        if kx < 1:
            raise ValueError(
                f"Spline requires at least 4 data points, got {n}"
            )
        import warnings
        s = self.smoothing * np.var(values) * n
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self._spline = SmoothBivariateSpline(xs, ys, values, kx=kx, ky=ky, s=max(s, 1.0))

    def _predict(self, xs, ys):
        return self._spline.ev(xs, ys)
