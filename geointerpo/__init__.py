"""geointerpo — spatial interpolation toolkit.

All imports are lazy: optional heavy dependencies (pykrige, meteostat, …)
are only loaded when the relevant class is first used.
"""

from __future__ import annotations

__version__ = "0.1.4"

# Canonical method list (mirrors ALL_METHODS in pipeline.py)
METHODS = [
    "idw",
    "kriging", "ok", "uk",
    "natural_neighbor",
    "spline", "spline_tension",
    "trend",
    "rbf",
    "nearest", "linear", "cubic",
    "gp", "rf", "gbm",
    "rk",
]


def __getattr__(name: str):
    _interpolators = {
        "IDWInterpolator", "RBFInterpolator", "KrigingInterpolator",
        "MLInterpolator", "GridDataInterpolator", "NaturalNeighborInterpolator",
        "SplineInterpolator", "TrendInterpolator", "RegressionKrigingInterpolator",
    }
    _sources = {"MeteostatSource", "OpenAQSource", "OpenMeteoSource"}

    if name in _interpolators:
        import importlib
        mod = importlib.import_module("geointerpo.interpolators")
        return getattr(mod, name)
    if name in _sources:
        import importlib
        mod = importlib.import_module("geointerpo.sources")
        return getattr(mod, name)
    if name == "compute_metrics":
        from geointerpo.validation.metrics import compute_metrics
        return compute_metrics
    if name == "Pipeline":
        from geointerpo.pipeline import Pipeline
        return Pipeline
    if name == "SearchRadius":
        from geointerpo.pipeline import SearchRadius
        return SearchRadius
    raise AttributeError(f"module 'geointerpo' has no attribute {name!r}")


__all__ = [
    # Core pipeline
    "Pipeline",
    "SearchRadius",
    # Interpolators
    "IDWInterpolator",
    "RBFInterpolator",
    "KrigingInterpolator",
    "MLInterpolator",
    "GridDataInterpolator",
    "NaturalNeighborInterpolator",
    "SplineInterpolator",
    "TrendInterpolator",
    "RegressionKrigingInterpolator",
    # Sources
    "MeteostatSource",
    "OpenAQSource",
    "OpenMeteoSource",
    # Validation
    "compute_metrics",
    # Constants
    "METHODS",
]
