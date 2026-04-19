from __future__ import annotations

import numpy as np
from scipy.interpolate import griddata
from geointerpo.interpolators.base import BaseInterpolator


class GridDataInterpolator(BaseInterpolator):
    """Scipy griddata interpolation: nearest neighbour, linear, or cubic.

    method: 'nearest', 'linear', 'cubic'
    fill_value: value used outside the convex hull of input points (linear/cubic only).
    """

    # griddata uses Euclidean distance, so metric coords are more correct for
    # 'nearest' and 'linear'; cubic works in any consistent coordinate system.
    _needs_metric = True

    def __init__(self, method: str = "linear", fill_value: float = float("nan"), **kwargs):
        super().__init__(**kwargs)
        self.method = method
        self.fill_value = fill_value

    def _fit(self, xs, ys, values):
        self._pts = np.column_stack([xs, ys])
        self._values = values

    def _predict(self, xs, ys):
        query = np.column_stack([xs, ys])
        return griddata(self._pts, self._values, query,
                        method=self.method, fill_value=self.fill_value)
