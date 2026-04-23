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
    if name == "ERA5Source":
        from geointerpo.sources.era5 import ERA5Source
        return ERA5Source
    if name == "NASAPowerSource":
        from geointerpo.sources.nasapower import NASAPowerSource
        return NASAPowerSource
    raise AttributeError(f"module 'geointerpo.sources' has no attribute {name!r}")


__all__ = ["MeteostatSource", "OpenAQSource", "OpenMeteoSource", "ERA5Source", "NASAPowerSource"]
