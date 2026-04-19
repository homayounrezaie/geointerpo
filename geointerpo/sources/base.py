from abc import ABC, abstractmethod
from typing import Tuple
import geopandas as gpd

BBox = Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)


class BaseDataSource(ABC):
    """All data sources return a GeoDataFrame with Point geometry and a 'value' column."""

    @abstractmethod
    def fetch(self, bbox: BBox, **kwargs) -> gpd.GeoDataFrame:
        """Fetch data within bbox. Returns GeoDataFrame(geometry=Point, value=float, ...)."""
        ...
