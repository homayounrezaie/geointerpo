"""Synthetic sample datasets — no network or API keys required.

Each function returns a GeoDataFrame ready to pass to any interpolator.
The data is procedurally generated with a reproducible seed so results are
deterministic across machines and Python versions.
"""

from __future__ import annotations

import numpy as np
import geopandas as gpd
from shapely.geometry import Point


def _make_stations(
    bbox: tuple[float, float, float, float],
    n: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = rng.uniform(min_lon, max_lon, n)
    lats = rng.uniform(min_lat, max_lat, n)
    return lons, lats


def load_temperature(
    bbox: tuple[float, float, float, float] = (5.0, 44.0, 25.0, 56.0),
    n_stations: int = 60,
    seed: int = 0,
) -> gpd.GeoDataFrame:
    """Synthetic daily mean temperature (°C) — Central Europe style.

    Signal: latitude gradient (cooler north) + longitude gradient (warmer east) + noise.
    """
    lons, lats = _make_stations(bbox, n_stations, seed)
    rng = np.random.default_rng(seed)
    values = (
        25.0
        - 0.5 * (lats - bbox[1])        # cooler toward north
        + 0.1 * (lons - bbox[0])         # slight east warming
        + rng.normal(0, 1.5, n_stations) # station-level noise
    )
    return gpd.GeoDataFrame(
        {"value": values, "station_id": [f"T{i:03d}" for i in range(n_stations)]},
        geometry=[Point(lo, la) for lo, la in zip(lons, lats)],
        crs="EPSG:4326",
    )


def load_precipitation(
    bbox: tuple[float, float, float, float] = (-10.0, 35.0, 30.0, 55.0),
    n_stations: int = 50,
    seed: int = 1,
) -> gpd.GeoDataFrame:
    """Synthetic daily precipitation (mm) — Western Europe style.

    Signal: higher precipitation in northwest, orographic effect, lognormal noise.
    """
    lons, lats = _make_stations(bbox, n_stations, seed)
    rng = np.random.default_rng(seed)
    signal = (
        8.0
        - 0.2 * (lons - bbox[0])         # drier toward east
        + 0.1 * (lats - bbox[1])          # wetter toward north
        + np.sin(np.radians(lons) * 3)    # pseudo-orographic wave
    )
    noise = rng.lognormal(0, 0.4, n_stations)
    values = np.clip(signal * noise, 0, None)
    return gpd.GeoDataFrame(
        {"value": values, "station_id": [f"P{i:03d}" for i in range(n_stations)]},
        geometry=[Point(lo, la) for lo, la in zip(lons, lats)],
        crs="EPSG:4326",
    )


def load_air_quality(
    bbox: tuple[float, float, float, float] = (68.0, 20.0, 90.0, 35.0),
    n_stations: int = 45,
    seed: int = 2,
) -> gpd.GeoDataFrame:
    """Synthetic PM2.5 air quality (µg/m³) — South Asia style.

    Signal: high in the densely populated Indo-Gangetic Plain (north),
    lower in coastal and elevated areas.
    """
    lons, lats = _make_stations(bbox, n_stations, seed)
    rng = np.random.default_rng(seed)
    # hotspot centred on ~77°E, 28°N (Delhi region)
    dist_hotspot = np.sqrt((lons - 77) ** 2 + (lats - 28) ** 2)
    signal = 120 * np.exp(-dist_hotspot / 6) + 20
    noise = rng.lognormal(0, 0.3, n_stations)
    values = np.clip(signal * noise, 5, 500)
    return gpd.GeoDataFrame(
        {"value": values, "station_id": [f"AQ{i:03d}" for i in range(n_stations)]},
        geometry=[Point(lo, la) for lo, la in zip(lons, lats)],
        crs="EPSG:4326",
    )
