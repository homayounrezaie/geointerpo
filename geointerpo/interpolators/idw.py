import numpy as np
from geointerpo.interpolators.base import BaseInterpolator


class IDWInterpolator(BaseInterpolator):
    """Inverse Distance Weighting interpolation.

    Automatically reprojects to UTM before fitting so distances are in metres.

    power: distance decay exponent (default 2). Higher = more local influence.
    """

    _needs_metric = True

    def __init__(self, power: float = 2.0, **kwargs):
        super().__init__(**kwargs)
        self.power = power

    def _fit(self, xs, ys, values):
        self._src_xs = xs
        self._src_ys = ys
        self._src_values = values

    def _predict(self, xs, ys):
        results = np.empty(len(xs))
        for i, (x, y) in enumerate(zip(xs, ys)):
            dist = np.sqrt((self._src_xs - x) ** 2 + (self._src_ys - y) ** 2)
            exact = dist == 0
            if exact.any():
                results[i] = self._src_values[exact][0]
                continue
            w = 1.0 / dist ** self.power
            results[i] = np.sum(w * self._src_values) / np.sum(w)
        return results
