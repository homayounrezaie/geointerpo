from __future__ import annotations


def __getattr__(name: str):
    if name == "MeteostatSource":
        from geointerpo.sources.meteostat import MeteostatSource
        return MeteostatSource
    if name == "OpenAQSource":
        from geointerpo.sources.openaq import OpenAQSource
        return OpenAQSource
    if name == "OpenMeteoSource":
        from geointerpo.sources.openmeteo import OpenMeteoSource
        return OpenMeteoSource
    raise AttributeError(f"module 'geointerpo.sources' has no attribute {name!r}")


__all__ = ["MeteostatSource", "OpenAQSource", "OpenMeteoSource"]
