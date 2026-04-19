from typing import Optional
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geointerpo.sources.base import BaseDataSource, BBox

try:
    import openmeteo_requests
    import requests_cache
    from retry_requests import retry
except ImportError as e:
    raise ImportError("Install: pip install openmeteo-requests requests-cache retry-requests") from e


def _build_session():
    cache_session = requests_cache.CachedSession(".cache/openmeteo", expire_after=3600)
    return retry(cache_session, retries=5, backoff_factor=0.2)


class OpenMeteoSource(BaseDataSource):
    """Fetch historical weather data from Open-Meteo API (no API key required).

    Samples a regular grid of virtual stations within the bbox, then returns
    them as point data — ideal for testing interpolation against known ground truth.

    variable: any Open-Meteo daily variable, e.g.:
              'temperature_2m_mean', 'precipitation_sum', 'wind_speed_10m_max',
              'et0_fao_evapotranspiration', 'shortwave_radiation_sum'
    date: ISO date string, e.g. '2024-01-01'
    n_points: approximate number of sample points (grid resolution)
    """

    OPENMETEO_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(
        self,
        variable: str = "temperature_2m_mean",
        date: Optional[str] = None,
        n_points: int = 25,
    ):
        self.variable = variable
        self.date = date or (pd.Timestamp.today() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
        self.n_points = n_points

    def _sample_grid(self, bbox: BBox):
        min_lon, min_lat, max_lon, max_lat = bbox
        side = max(1, int(np.sqrt(self.n_points)))
        lons = np.linspace(min_lon, max_lon, side)
        lats = np.linspace(min_lat, max_lat, side)
        lon_g, lat_g = np.meshgrid(lons, lats)
        return lon_g.ravel(), lat_g.ravel()

    def fetch(self, bbox: BBox) -> gpd.GeoDataFrame:
        lons, lats = self._sample_grid(bbox)
        om = openmeteo_requests.Client(session=_build_session())

        params = {
            "latitude": lats.tolist(),
            "longitude": lons.tolist(),
            "daily": self.variable,
            "start_date": self.date,
            "end_date": self.date,
            "timezone": "UTC",
        }
        responses = om.weather_api(self.OPENMETEO_URL, params=params)

        rows = []
        for r, lon, lat in zip(responses, lons, lats):
            daily = r.Daily()
            if daily is None:
                continue
            vals = daily.Variables(0).ValuesAsNumpy()
            if vals is None or len(vals) == 0:
                continue
            val = float(vals[0])
            if np.isnan(val):
                continue
            rows.append({"lon": lon, "lat": lat, "value": val})

        if not rows:
            raise ValueError(f"No Open-Meteo data for '{self.variable}' on {self.date} in {bbox}")

        df = pd.DataFrame(rows)
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(r.lon, r.lat) for r in df.itertuples()],
            crs="EPSG:4326",
        )
        gdf.attrs["variable"] = self.variable
        gdf.attrs["source"] = "open-meteo"
        return gdf
