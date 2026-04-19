import numpy as np
from scipy.interpolate import RBFInterpolator as ScipyRBF
from geointerpo.interpolators.base import BaseInterpolator


class RBFInterpolator(BaseInterpolator):
    """Radial Basis Function interpolation via scipy.

    Automatically reprojects to UTM so the RBF length-scale is in metres.

    kernel: 'linear', 'thin_plate_spline', 'cubic', 'quintic', 'multiquadric',
            'inverse_multiquadric', 'inverse_quadratic', 'gaussian'
    smoothing: regularisation parameter (0 = exact interpolation).
    """

    _needs_metric = True

    def __init__(self, kernel: str = "thin_plate_spline", smoothing: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.kernel = kernel
        self.smoothing = smoothing
        self._rbf = None

    def _fit(self, xs, ys, values):
        pts = np.column_stack([xs, ys])
        self._rbf = ScipyRBF(pts, values, kernel=self.kernel, smoothing=self.smoothing)

    def _predict(self, xs, ys):
        pts = np.column_stack([xs, ys])
        return self._rbf(pts)
