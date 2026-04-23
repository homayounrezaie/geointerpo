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

    def __init__(
        self,
        kernel: str = "thin_plate_spline",
        smoothing: float = 0.0,
        epsilon: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.kernel = kernel
        self.smoothing = smoothing
        self.epsilon = epsilon
        self._rbf = None

    def _fit(self, xs, ys, values):
        pts = np.column_stack([xs, ys])
        epsilon = self.epsilon
        if epsilon is None and self.kernel not in {"thin_plate_spline", "linear", "quintic", "cubic"}:
            if len(pts) > 1:
                diffs = pts[:, None, :] - pts[None, :, :]
                dists = np.sqrt((diffs ** 2).sum(axis=2))
                dists[dists == 0] = np.nan
                epsilon = float(np.nanmedian(dists))
            else:
                epsilon = 1.0
        self._rbf = ScipyRBF(
            pts,
            values,
            kernel=self.kernel,
            smoothing=self.smoothing,
            epsilon=epsilon,
        )

    def _predict(self, xs, ys):
        pts = np.column_stack([xs, ys])
        return self._rbf(pts)
