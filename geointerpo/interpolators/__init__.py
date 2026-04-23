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


def _optional_import_placeholder(name: str, exc: ImportError):
    class _MissingOptionalDependency:
        __name__ = name
        __qualname__ = name
        __doc__ = f"{name} is unavailable because an optional dependency is missing."

        def __init__(self, *args, **kwargs):
            raise ImportError(str(exc)) from exc

    return _MissingOptionalDependency


def __getattr__(name: str):
    if name in _MAP:
        import importlib
        try:
            mod = importlib.import_module(_MAP[name])
            return getattr(mod, name)
        except ImportError as exc:
            return _optional_import_placeholder(name, exc)
    raise AttributeError(f"module 'geointerpo.interpolators' has no attribute {name!r}")


__all__ = list(_MAP)
