from typing import Optional
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geointerpo.sources.base import BaseDataSource, BBox

try:
    import requests
except ImportError as e:
    raise ImportError("Install requests: pip install requests") from e

_OPENAQ_BASE = "https://api.openaq.org/v3"


class OpenAQSource(BaseDataSource):
    """Fetch air quality station data from OpenAQ v3 API (no key required for basic use).

    parameter: 'pm25', 'pm10', 'o3', 'no2', 'so2', 'co'
    date_from / date_to: ISO date strings, e.g. '2024-01-01'
    limit: max locations to fetch (default 1000)
    """

    PARAM_IDS = {
        "pm25": 2,
        "pm10": 1,
        "o3": 3,
        "no2": 5,
        "so2": 9,
        "co": 4,
    }

    def __init__(
        self,
        parameter: str = "pm25",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 1000,
        api_key: Optional[str] = None,
    ):
        self.parameter = parameter
        self.date_from = date_from or (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        self.date_to = date_to or pd.Timestamp.today().strftime("%Y-%m-%d")
        self.limit = limit
        self.headers = {"X-API-Key": api_key} if api_key else {}

    def fetch(self, bbox: BBox) -> gpd.GeoDataFrame:
        min_lon, min_lat, max_lon, max_lat = bbox
        param_id = self.PARAM_IDS.get(self.parameter)
        if param_id is None:
            raise ValueError(f"Unknown parameter '{self.parameter}'. Options: {list(self.PARAM_IDS)}")

        params = {
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "parameters_id": param_id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "limit": self.limit,
        }
        resp = requests.get(f"{_OPENAQ_BASE}/measurements", params=params, headers=self.headers, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])

        if not results:
            raise ValueError(f"No OpenAQ measurements found for '{self.parameter}' in bbox {bbox}")

        rows = []
        for r in results:
            coords = r.get("coordinates") or {}
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            val = r.get("value")
            if lat is None or lon is None or val is None:
                continue
            rows.append({
                "station_id": r.get("locationId"),
                "station_name": r.get("location"),
                "value": float(val),
                "unit": r.get("unit"),
                "date": r.get("date", {}).get("utc"),
                "lat": lat,
                "lon": lon,
            })

        if not rows:
            raise ValueError("All OpenAQ results lacked coordinate or value data")

        df = pd.DataFrame(rows)
        agg = df.groupby("station_id").agg(
            value=("value", "mean"),
            lat=("lat", "first"),
            lon=("lon", "first"),
            station_name=("station_name", "first"),
        ).reset_index()

        gdf = gpd.GeoDataFrame(
            agg,
            geometry=[Point(row.lon, row.lat) for row in agg.itertuples()],
            crs="EPSG:4326",
        )
        gdf.attrs["variable"] = self.parameter
        gdf.attrs["source"] = "openaq"
        return gdf
