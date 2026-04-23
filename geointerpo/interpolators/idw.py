from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from geointerpo.interpolators.base import BaseInterpolator


class IDWInterpolator(BaseInterpolator):
    """Inverse Distance Weighting interpolation.

    Automatically reprojects to UTM before fitting so distances are in metres.
    Uses a vectorized KD-tree query — ~50–200x faster than the naive loop on
    large grids.

    power:       distance decay exponent (default 2). Higher = more local.
    n_neighbors: max stations per prediction point (default: all stations).
    """

    _needs_metric = True

    def __init__(self, power: float = 2.0, n_neighbors: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.power = power
        self.n_neighbors = n_neighbors

    def _fit(self, xs, ys, values):
        self._src_values = np.asarray(values, dtype=float)
        self._tree = cKDTree(np.column_stack([xs, ys]))

    def _predict(self, xs, ys):
        k = min(self.n_neighbors or len(self._src_values), len(self._src_values))
        query = np.column_stack([xs, ys])
        dists, idxs = self._tree.query(query, k=k, workers=-1)

        if k == 1:
            dists = dists[:, np.newaxis]
            idxs = idxs[:, np.newaxis]

        exact_mask = dists[:, 0] == 0

        # weights: 0 where distance==0 to avoid division; handled below
        with np.errstate(divide="ignore", invalid="ignore"):
            weights = np.where(dists == 0, 0.0, dists ** (-self.power))

        weighted_sum = (weights * self._src_values[idxs]).sum(axis=1)
        total = weights.sum(axis=1)
        result = np.where(total > 0, weighted_sum / total, np.nan)

        # Exact station hits get the true station value
        if exact_mask.any():
            result[exact_mask] = self._src_values[idxs[exact_mask, 0]]

        return result
