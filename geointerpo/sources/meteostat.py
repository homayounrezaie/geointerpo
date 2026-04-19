from datetime import date, datetime
from typing import Tuple, Union
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point as ShapelyPoint
from geointerpo.sources.base import BaseDataSource, BBox

try:
    from meteostat import stations as _stations_db, daily, hourly, monthly, Point as MeteoPoint, config as _meteostat_config
    _meteostat_config.block_large_requests = False
except ImportError as e:
    raise ImportError("Install meteostat: pip install meteostat") from e


class MeteostatSource(BaseDataSource):
    """Fetch weather station observations via meteostat (v2 API).

    variable: column name from meteostat data.
              daily options: 'temp', 'tmin', 'tmax', 'prcp', 'snwd', 'wspd', 'pres'
    freq: 'daily', 'hourly', or 'monthly'
    """

    FREQ_MAP = {"daily": daily, "hourly": hourly, "monthly": monthly}

    def __init__(
        self,
        variable: str = "temp",
        start: Union[str, date, datetime] = None,
        end: Union[str, date, datetime] = None,
        freq: str = "daily",
        radius_km: float = 500,
    ):
        # backward compat: tavg → temp
        if variable == "tavg":
            variable = "temp"
        self.variable = variable
        self.freq = freq
        self.radius_km = radius_km
        self.start = pd.Timestamp(start) if start else pd.Timestamp.today() - pd.Timedelta(days=1)
        self.end = pd.Timestamp(end) if end else self.start

    def fetch(self, bbox: BBox) -> gpd.GeoDataFrame:
        min_lon, min_lat, max_lon, max_lat = bbox
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Radius: use half-diagonal of bbox in meters, capped at radius_km
        import math
        diag_km = math.sqrt(((max_lat - min_lat) * 111) ** 2 + ((max_lon - min_lon) * 111 * math.cos(math.radians(center_lat))) ** 2) / 2
        radius_m = max(diag_km, self.radius_km) * 1000

        center_pt = MeteoPoint(center_lat, center_lon)
        station_df = _stations_db.nearby(center_pt, radius_m)

        if station_df.empty:
            raise ValueError(f"No meteostat stations found in bbox {bbox}")

        # Filter to stations within the bbox
        in_bbox = station_df[
            (station_df["latitude"] >= min_lat) & (station_df["latitude"] <= max_lat) &
            (station_df["longitude"] >= min_lon) & (station_df["longitude"] <= max_lon)
        ]
        if not in_bbox.empty:
            station_df = in_bbox

        station_ids = station_df.index.tolist()
        start_dt = self.start.date() if hasattr(self.start, "date") else self.start
        end_dt = self.end.date() if hasattr(self.end, "date") else self.end

        ts_cls = self.FREQ_MAP[self.freq]
        ts = ts_cls(station_ids, start_dt, end_dt)
        data = ts.fetch()

        if data.empty:
            raise ValueError(f"No {self.freq} data for variable '{self.variable}' in bbox {bbox}")

        # Normalise column name (Parameter enum → string)
        data.columns = [c.value if hasattr(c, "value") else str(c) for c in data.columns]

        if self.variable not in data.columns:
            available = [c for c in data.columns if data[c].notna().any()]
            raise ValueError(
                f"Variable '{self.variable}' not found. Available: {available}"
            )

        data = data.reset_index()
        time_col = "time" if "time" in data.columns else data.columns[1]
        agg = data.groupby("station")[self.variable].mean().dropna().rename("value")

        merged = agg.to_frame().join(
            station_df[["latitude", "longitude", "name"]], how="left"
        )
        merged = merged.dropna(subset=["value", "latitude", "longitude"])

        gdf = gpd.GeoDataFrame(
            merged.reset_index().rename(columns={"station": "station_id"}),
            geometry=[
                ShapelyPoint(row.longitude, row.latitude) for row in merged.itertuples()
            ],
            crs="EPSG:4326",
        )
        gdf.attrs["variable"] = self.variable
        gdf.attrs["source"] = "meteostat"
        return gdf
