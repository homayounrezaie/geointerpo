"""Natural Neighbor interpolation (Sibson 1981).

Uses Voronoi tessellation: for each prediction point p, the weight given to
data point i equals the area that Voronoi cell i loses when p is inserted into
the diagram.  Points outside the convex hull of the data return NaN.

This is the same algorithm as ArcGIS Natural Neighbor.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import Voronoi, ConvexHull
from shapely.geometry import Polygon

from geointerpo.interpolators.base import BaseInterpolator


def _voronoi_polygons(vor: Voronoi, radius: float) -> list[Polygon | None]:
    """Return shapely Polygons for each finite Voronoi region."""
    center = vor.points.mean(axis=0)

    finite_polys = []
    for point_idx, region_idx in enumerate(vor.point_region):
        region = vor.regions[region_idx]
        if not region or -1 not in region:
            verts = vor.vertices[region]
            finite_polys.append(Polygon(verts))
        else:
            # Extend ridges to infinity using a far-away point
            new_verts = []
            for vert_idx in region:
                if vert_idx >= 0:
                    new_verts.append(vor.vertices[vert_idx].tolist())
                else:
                    # find the ridge that contains -1
                    for ridge_pts, ridge_verts in zip(vor.ridge_points, vor.ridge_vertices):
                        if -1 in ridge_verts and point_idx in ridge_pts:
                            other_vert = ridge_verts[ridge_verts.index(-1) ^ 1]
                            tangent = vor.points[ridge_pts[1]] - vor.points[ridge_pts[0]]
                            normal = np.array([-tangent[1], tangent[0]])
                            normal /= np.linalg.norm(normal)
                            midpoint = vor.points[ridge_pts].mean(axis=0)
                            if np.dot(midpoint - center, normal) < 0:
                                normal *= -1
                            far_pt = vor.vertices[other_vert] + normal * radius * 2
                            new_verts.append(far_pt.tolist())
            if len(new_verts) >= 3:
                from scipy.spatial import ConvexHull
                try:
                    hull = ConvexHull(new_verts)
                    ordered = [new_verts[i] for i in hull.vertices]
                    finite_polys.append(Polygon(ordered))
                except Exception:
                    finite_polys.append(None)
            else:
                finite_polys.append(None)
    return finite_polys


class NaturalNeighborInterpolator(BaseInterpolator):
    """Voronoi / Sibson natural neighbor interpolation.

    Computes weights as fractional area stolen from each neighbouring Voronoi
    cell when the prediction point is inserted.  Smooth, local, and exact at
    data locations.  Returns NaN outside the convex hull.

    Uses projected (UTM) coordinates for geometrically correct area calculations.
    """

    _needs_metric = True

    def _fit(self, xs, ys, values):
        self._xs = xs.copy()
        self._ys = ys.copy()
        self._values = values.copy()

    def _idw_fallback(self, xs, ys, power: float = 2.0) -> np.ndarray:
        """Vectorized IDW estimate."""
        xs = np.asarray(xs)
        ys = np.asarray(ys)
        d2 = (xs[:, None] - self._xs[None, :]) ** 2 + (ys[:, None] - self._ys[None, :]) ** 2
        w = 1.0 / np.maximum(d2, 1e-12) ** (power / 2)
        result = (w * self._values[None, :]).sum(axis=1) / w.sum(axis=1)
        # Exact match override
        exact = np.where(d2.min(axis=1) == 0)[0]
        for i in exact:
            result[i] = self._values[d2[i].argmin()]
        return result

    def _predict(self, xs, ys):
        results = np.full(len(xs), np.nan)

        # Convex hull of training data for outside-hull detection
        try:
            hull = ConvexHull(np.column_stack([self._xs, self._ys]))
            hull_poly = Polygon(
                np.column_stack([self._xs, self._ys])[hull.vertices]
            )
        except Exception:
            return self._idw_fallback(xs, ys)

        radius = (self._xs.max() - self._xs.min()) + (self._ys.max() - self._ys.min())

        outside = []
        for i, (qx, qy) in enumerate(zip(xs, ys)):
            from shapely.geometry import Point as SPoint

            if not hull_poly.contains(SPoint(qx, qy)):
                outside.append(i)
                continue

            # Insert query point and recompute Voronoi
            pts = np.vstack([np.column_stack([self._xs, self._ys]),
                             [[qx, qy]]])
            try:
                vor = Voronoi(pts)
            except Exception:
                continue

            polys = _voronoi_polygons(vor, radius)
            n_data = len(self._xs)
            query_poly = polys[n_data] if n_data < len(polys) else None
            if query_poly is None or not query_poly.is_valid:
                continue

            weights = np.zeros(n_data)
            for j in range(n_data):
                nbr_poly = polys[j]
                if nbr_poly is None or not nbr_poly.is_valid:
                    continue
                try:
                    overlap = query_poly.intersection(nbr_poly)
                    weights[j] = overlap.area
                except Exception:
                    pass

            total = weights.sum()
            if total > 0:
                results[i] = np.dot(weights / total, self._values)

        # Fill outside-hull points with IDW
        if outside:
            out_idx = np.array(outside)
            results[out_idx] = self._idw_fallback(xs[out_idx], ys[out_idx])

        # Fill any Voronoi failures inside the hull with IDW too
        still_nan = np.where(np.isnan(results))[0]
        if len(still_nan) > 0:
            results[still_nan] = self._idw_fallback(xs[still_nan], ys[still_nan])

        return results
