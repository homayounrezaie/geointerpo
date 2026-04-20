"""Google Earth Engine validation layer.

Requires:
  pip install 'geointerpo[gee]'
  earthengine authenticate   # one-time browser login

GEE_PRODUCTS maps each variable type to a GEE dataset, band name, and
optional scale factor to convert raw values to the same units used by
the station data sources.
"""

from typing import Tuple, Optional
import numpy as np
import xarray as xr

BBox = Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)

GEE_PRODUCTS = {
    "temperature": {
        "collection": "MODIS/061/MOD11A1",
        "band": "LST_Day_1km",
        "scale": 0.02,        # Kelvin; subtract 273.15 after scaling for Celsius
        "kelvin_to_celsius": True,
        "resolution_m": 1000,
    },
    "precipitation": {
        "collection": "UCSB-CHG/CHIRPS/DAILY",
        "band": "precipitation",
        "scale": 1.0,
        "kelvin_to_celsius": False,
        "resolution_m": 5566,  # ~0.05 degrees
    },
    "pm25": {
        "collection": "COPERNICUS/S5P/NRTI/L3_AER_AI",
        "band": "absorbing_aerosol_index",
        "scale": 1.0,
        "kelvin_to_celsius": False,
        "resolution_m": 3500,
    },
    "o3": {
        "collection": "COPERNICUS/S5P/NRTI/L3_O3",
        "band": "O3_column_number_density",
        "scale": 1.0,
        "kelvin_to_celsius": False,
        "resolution_m": 3500,
    },
    "no2": {
        "collection": "COPERNICUS/S5P/NRTI/L3_NO2",
        "band": "tropospheric_NO2_column_number_density",
        "scale": 1.0,
        "kelvin_to_celsius": False,
        "resolution_m": 3500,
    },
}


class GEEValidator:
    """Fetch a GEE reference raster and compare against an interpolated surface.

    Usage
    -----
    validator = GEEValidator(variable="temperature", date="2024-06-15")
    reference = validator.fetch_reference(bbox=(-10, 35, 30, 60), resolution=0.1)
    metrics = validator.compare(interpolated_da, reference)
    """

    def __init__(self, variable: str, date: str, project: Optional[str] = None):
        if variable not in GEE_PRODUCTS:
            raise ValueError(f"Unknown variable '{variable}'. Options: {list(GEE_PRODUCTS)}")
        self.variable = variable
        self.date = date
        self.project = project
        self._ee = None

    def _init_ee(self):
        if self._ee is not None:
            return
        try:
            import ee
        except ImportError as exc:
            raise ImportError("Install earthengine-api: pip install earthengine-api") from exc
        try:
            import geemap
            geemap.ee_initialize(project=self.project)
        except ImportError:
            # geemap not available — fall back to plain ee auth
            try:
                if self.project:
                    ee.Initialize(project=self.project)
                else:
                    ee.Initialize()
            except Exception:
                ee.Authenticate()
                if self.project:
                    ee.Initialize(project=self.project)
                else:
                    ee.Initialize()
        self._ee = ee

    def fetch_reference(self, bbox: BBox, resolution: float = 0.1) -> xr.DataArray:
        """Download GEE raster for the configured variable/date and return as DataArray.

        resolution: output grid resolution in degrees.
        """
        self._init_ee()
        ee = self._ee
        product = GEE_PRODUCTS[self.variable]

        region = ee.Geometry.BBox(*bbox)
        date_end = (
            __import__("pandas").Timestamp(self.date) + __import__("pandas").Timedelta(days=1)
        ).strftime("%Y-%m-%d")

        image = (
            ee.ImageCollection(product["collection"])
            .filterDate(self.date, date_end)
            .filterBounds(region)
            .select(product["band"])
            .mean()
        )

        scale_m = max(int(resolution * 111_320), product["resolution_m"])
        url = image.getDownloadURL(
            {
                "region": region,
                "scale": scale_m,
                "format": "GEO_TIFF",
                "bands": [product["band"]],
            }
        )

        import requests, io
        import rioxarray  # noqa: F401 — registers .rio accessor

        response = requests.get(url, timeout=120)
        response.raise_for_status()
        with io.BytesIO(response.content) as buf:
            da = xr.open_dataarray(buf, engine="rasterio").squeeze(drop=True)

        da = da * product["scale"]
        if product.get("kelvin_to_celsius"):
            da = da - 273.15

        da = da.rename({"x": "lon", "y": "lat"})
        da.name = self.variable
        da.attrs["source"] = "GEE"
        da.attrs["collection"] = product["collection"]
        da.attrs["date"] = self.date
        return da

    def compare(self, predicted: xr.DataArray, reference: xr.DataArray) -> dict:
        """Compare interpolated surface against GEE reference. Returns metrics dict."""
        from geointerpo.validation.metrics import grid_metrics
        return grid_metrics(reference, predicted)
