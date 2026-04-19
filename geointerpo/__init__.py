"""geointerpo — spatial interpolation toolkit.

All imports are lazy: optional heavy dependencies (pykrige, earthengine-api,
meteostat, …) are only loaded when the relevant class is first used.
"""

from __future__ import annotations

__version__ = "0.1.0"

# Canonical method list (mirrors ALL_METHODS in pipeline.py)
METHODS = [
    # ArcGIS tools
    "idw",
    "kriging", "ok", "uk",
    "natural_neighbor",
    "spline", "spline_tension",
    "trend",
    # Additional
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
    _validation = {"compute_metrics", "GEEValidator"}

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
    if name == "GEEValidator":
        from geointerpo.validation.gee_validator import GEEValidator
        return GEEValidator
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
    "GEEValidator",
    # Constants
    "METHODS",
]
