from __future__ import annotations

_MAP = {
    "IDWInterpolator":              "geointerpo.interpolators.idw",
    "RBFInterpolator":              "geointerpo.interpolators.rbf",
    "KrigingInterpolator":          "geointerpo.interpolators.kriging",
    "MLInterpolator":               "geointerpo.interpolators.ml",
    "GridDataInterpolator":         "geointerpo.interpolators.griddata",
    "NaturalNeighborInterpolator":  "geointerpo.interpolators.natural_neighbor",
    "SplineInterpolator":           "geointerpo.interpolators.spline",
    "TrendInterpolator":            "geointerpo.interpolators.trend",
    "RegressionKrigingInterpolator": "geointerpo.interpolators.regression_kriging",
    "CokrigingInterpolator":        "geointerpo.interpolators.cokriging",
    "SGSInterpolator":              "geointerpo.interpolators.sgs",
}


def __getattr__(name: str):
    if name in _MAP:
        import importlib
        mod = importlib.import_module(_MAP[name])
        return getattr(mod, name)
    raise AttributeError(f"module 'geointerpo.interpolators' has no attribute {name!r}")


__all__ = list(_MAP)
