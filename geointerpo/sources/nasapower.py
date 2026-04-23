"""NASA POWER data source — free, no account required.

NASA POWER (Prediction Of Worldwide Energy Resources) provides daily/monthly
meteorological and solar data from 1981 onwards via a free REST API.

No API key or account is needed. Data is sampled at point locations within the
bbox and returned as a GeoDataFrame compatible with the geointerpo Pipeline.

API docs: https://power.larc.nasa.gov/docs/services/api/
"""

from __future__ import annotations

import math
import numpy as np
import geopandas as gpd
import requests
from shapely.geometry import Point

from geointerpo.sources.base import BaseDataSource, BBox

NASAPOWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# NASA POWER parameter names
NASAPOWER_VARIABLES = {
    "temperature":       "T2M",           # 2m air temperature (°C)
    "t2m":              "T2M",
    "t2m_max":          "T2M_MAX",
    "t2m_min":          "T2M_MIN",
    "dewpoint":         "T2MDEW",
    "wind_speed":       "WS2M",           # 2m wind speed (m/s)
    "wind_speed_10m":   "WS10M",
    "precipitation":    "PRECTOTCORR",    # corrected precipitation (mm/day)
    "solar_radiation":  "ALLSKY_SFC_SW_DWN",  # surface solar irradiance (kWh/m²/day)
    "humidity":         "RH2M",           # relative humidity (%)
    "pressure":         "PS",             # surface pressure (kPa)
    "evapotranspiration": "ET0",
}


class NASAPowerSource(BaseDataSource):
    """Fetch meteorological / solar data from the NASA POWER REST API.

    Samples a regular grid of virtual stations within the bbox.  No account or
    API key required — the API is rate-limited to ~30 req/min per IP.

    Parameters
    ----------
    variable:    Variable name. See NASAPOWER_VARIABLES for supported keys,
                 or pass a raw NASA POWER parameter string directly (e.g. 'T2M').
    date:        ISO date string 'YYYY-MM-DD'.
    community:   'RE' (renewable energy), 'AG' (agroclimatology), 'SB' (sustainable buildings).
    n_lat:       Number of latitude samples within bbox (default 5).
    n_lon:       Number of longitude samples within bbox (default 5).
    timeout:     HTTP request timeout in seconds (default 30).
    """

    def __init__(
        self,
        variable: str = "temperature",
        date: str = "2024-01-01",
        community: str = "RE",
        n_lat: int = 5,
        n_lon: int = 5,
        timeout: int = 30,
    ):
        self.variable = NASAPOWER_VARIABLES.get(variable, variable)
        self.date = date
        self.community = community
        self.n_lat = n_lat
        self.n_lon = n_lon
        self.timeout = timeout

    def fetch(self, bbox: BBox) -> gpd.GeoDataFrame:
        """Sample NASA POWER data on a grid and return a GeoDataFrame."""
        min_lon, min_lat, max_lon, max_lat = bbox

        lats = np.linspace(min_lat, max_lat, self.n_lat)
        lons = np.linspace(min_lon, max_lon, self.n_lon)

        records = []
        for lat in lats:
            for lon in lons:
                value = self._fetch_point(lat, lon)
                if value is not None and not math.isnan(value):
                    records.append({"lat": lat, "lon": lon, "value": value})

        if not records:
            raise ValueError(
                f"NASA POWER returned no valid data for variable '{self.variable}' "
                f"on {self.date} within bbox {bbox}."
            )

        gdf = gpd.GeoDataFrame(
            records,
            geometry=[Point(r["lon"], r["lat"]) for r in records],
            crs="EPSG:4326",
        )
        gdf.attrs["variable"] = self.variable
        gdf.attrs["source"] = "nasapower"
        gdf.attrs["date"] = self.date
        return gdf

    def _fetch_point(self, lat: float, lon: float) -> float | None:
        """Fetch a single point from the NASA POWER API."""
        params = {
            "parameters": self.variable,
            "community": self.community,
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "start": self.date.replace("-", ""),
            "end": self.date.replace("-", ""),
            "format": "JSON",
        }
        try:
            resp = requests.get(NASAPOWER_BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            param_data = data["properties"]["parameter"][self.variable]
            # date key format: YYYYMMDD
            date_key = self.date.replace("-", "")
            val = param_data.get(date_key)
            if val is None or val == -999:
                return None
            return float(val)
        except Exception:
            return None
