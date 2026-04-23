"""ERA5 reanalysis data source via the Copernicus Climate Data Store (CDS) API.

Requires a free CDS account and cdsapi:
    pip install cdsapi
    # Set up ~/.cdsapirc with your API key — see https://cds.climate.copernicus.eu/api-how-to

ERA5 provides hourly/daily global reanalysis from 1940 onwards at 0.25° resolution.
It is the gold-standard reference dataset for climate and weather research.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import geopandas as gpd
from shapely.geometry import Point

from geointerpo.sources.base import BaseDataSource, BBox

# ERA5 variable → CDS short name mapping
ERA5_VARIABLES = {
    "temperature":        "2m_temperature",
    "t2m":               "2m_temperature",
    "2m_temperature":    "2m_temperature",
    "dewpoint":          "2m_dewpoint_temperature",
    "wind_u":            "10m_u_component_of_wind",
    "wind_v":            "10m_v_component_of_wind",
    "wind_speed":        "10m_wind_speed",
    "precipitation":     "total_precipitation",
    "total_precipitation": "total_precipitation",
    "surface_pressure":  "surface_pressure",
    "radiation":         "surface_solar_radiation_downwards",
    "snow_depth":        "snow_depth",
    "sea_ice":           "sea_ice_cover",
}

# Unit conversions applied after download
ERA5_UNIT_OFFSET = {
    "2m_temperature": -273.15,          # K → °C
    "2m_dewpoint_temperature": -273.15,  # K → °C
}


class ERA5Source(BaseDataSource):
    """Fetch ERA5 reanalysis data via the CDS API.

    The CDS API downloads a NetCDF/GRIB file for the requested area and time.
    We then sample it on a regular grid within the bbox and return a GeoDataFrame
    compatible with the geointerpo Pipeline.

    Parameters
    ----------
    variable:    ERA5 variable name (e.g. 'temperature', '2m_temperature').
    date:        ISO date string 'YYYY-MM-DD'.
    time:        Hour string 'HH:MM' (default '12:00' — noon).
    pressure_level: Pressure level in hPa for pressure-level variables (None for single-level).
    product_type:   'reanalysis' (default) or 'ensemble_members'.
    n_grid_points:  Number of grid points to sample within bbox (default 50×50).
    """

    def __init__(
        self,
        variable: str = "temperature",
        date: str = "2024-01-01",
        time: str = "12:00",
        pressure_level: int | None = None,
        product_type: str = "reanalysis",
        n_grid_points: int = 50,
    ):
        self.variable = ERA5_VARIABLES.get(variable, variable)
        self.date = date
        self.time = time
        self.pressure_level = pressure_level
        self.product_type = product_type
        self.n_grid_points = n_grid_points

    def fetch(self, bbox: BBox) -> gpd.GeoDataFrame:
        """Download ERA5 data and return as a GeoDataFrame of virtual stations."""
        try:
            import cdsapi
        except ImportError as e:
            raise ImportError(
                "ERA5 source requires cdsapi:\n"
                "  pip install cdsapi\n"
                "  # Then set up ~/.cdsapirc — see https://cds.climate.copernicus.eu/api-how-to"
            ) from e

        min_lon, min_lat, max_lon, max_lat = bbox

        # CDS area order: N/W/S/E
        area = [max_lat, min_lon, min_lat, max_lon]

        dataset = (
            "reanalysis-era5-pressure-levels"
            if self.pressure_level is not None
            else "reanalysis-era5-single-levels"
        )

        request: dict = {
            "product_type": self.product_type,
            "variable": self.variable,
            "year": self.date[:4],
            "month": self.date[5:7],
            "day": self.date[8:10],
            "time": self.time,
            "format": "netcdf",
            "area": area,
        }
        if self.pressure_level is not None:
            request["pressure_level"] = str(self.pressure_level)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "era5.nc"
            client = cdsapi.Client(quiet=True)
            client.retrieve(dataset, request, str(output_path))
            return self._nc_to_gdf(output_path, bbox)

    def _nc_to_gdf(self, nc_path: Path, bbox: BBox) -> gpd.GeoDataFrame:
        import xarray as xr

        ds = xr.open_dataset(nc_path)

        # Find the data variable (skip coordinate variables)
        data_vars = [v for v in ds.data_vars if v not in ("latitude", "longitude", "time")]
        if not data_vars:
            raise ValueError(f"No data variables found in ERA5 output. Variables: {list(ds.data_vars)}")
        var_name = data_vars[0]

        da = ds[var_name]

        # Select first time step if multiple
        if "time" in da.dims:
            da = da.isel(time=0)
        if "expver" in da.dims:
            da = da.isel(expver=0)

        # Rename coordinate aliases
        rename = {}
        for dim in da.dims:
            if dim in ("latitude", "lat"):
                rename[dim] = "lat"
            elif dim in ("longitude", "lon"):
                rename[dim] = "lon"
        if rename:
            da = da.rename(rename)

        vals = da.values.astype(float)

        # Apply unit conversion (K → °C for temperature)
        offset = ERA5_UNIT_OFFSET.get(self.variable, 0.0)
        if offset:
            vals = vals + offset

        lats = da.lat.values
        lons = da.lon.values

        # Build GeoDataFrame from grid points
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        flat_lons = lon_grid.ravel()
        flat_lats = lat_grid.ravel()
        flat_vals = vals.ravel()

        valid = ~np.isnan(flat_vals)
        gdf = gpd.GeoDataFrame(
            {"value": flat_vals[valid]},
            geometry=[Point(lo, la) for lo, la in zip(flat_lons[valid], flat_lats[valid])],
            crs="EPSG:4326",
        )
        gdf.attrs["variable"] = self.variable
        gdf.attrs["source"] = "era5"
        gdf.attrs["date"] = self.date
        return gdf
