"""I/O helpers: export xarray.DataArray to GeoTIFF/NetCDF, clip by polygon."""

from __future__ import annotations

import pathlib
import numpy as np
import xarray as xr


def export_geotiff(da: xr.DataArray, path: str | pathlib.Path) -> None:
    """Write a lon/lat DataArray to a GeoTIFF with CRS metadata.

    Requires rioxarray (pip install 'geointerpo[raster]').
    """
    try:
        import rioxarray  # noqa: F401
    except ImportError as e:
        raise ImportError("Install rioxarray: pip install 'geointerpo[raster]'") from e

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    da = da.copy()
    if "spatial_ref" not in da.coords:
        da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat")
        da = da.rio.write_crs("EPSG:4326")

    da.rio.to_raster(str(path))


def export_netcdf(da: xr.DataArray, path: str | pathlib.Path) -> None:
    """Write a DataArray to NetCDF with CF-compliant metadata."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    da = da.copy()
    da.attrs = _netcdf_safe_attrs(da.attrs)
    ds = da.to_dataset(name=da.name or "value")
    ds["lon"].attrs.update({"units": "degrees_east", "long_name": "longitude"})
    ds["lat"].attrs.update({"units": "degrees_north", "long_name": "latitude"})
    ds.attrs.setdefault("Conventions", "CF-1.8")
    ds.to_netcdf(str(path))


def _netcdf_safe_attrs(attrs: dict) -> dict:
    """Drop attrs that NetCDF backends cannot encode, such as 2-D arrays."""
    safe = {}
    for key, value in attrs.items():
        arr = np.asarray(value) if isinstance(value, (list, tuple, np.ndarray)) else None
        if arr is not None and arr.ndim > 1:
            continue
        safe[key] = value
    return safe


def clip_to_polygon(
    da: xr.DataArray,
    geometry,
    all_touched: bool = False,
) -> xr.DataArray:
    """Mask a DataArray to the interior of a Shapely geometry or GeoDataFrame.

    Pixels whose centres fall outside the polygon are set to NaN.

    geometry: a Shapely geometry or a GeoDataFrame (union of all geometries used).
    all_touched: if True, include pixels that touch the boundary.

    Requires rioxarray.
    """
    try:
        import rioxarray  # noqa: F401
    except ImportError as e:
        raise ImportError("Install rioxarray: pip install 'geointerpo[raster]'") from e

    da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat").rio.write_crs("EPSG:4326")

    if hasattr(geometry, "geometry"):  # GeoDataFrame
        geom = [geometry.geometry.union_all()]
    elif hasattr(geometry, "__geo_interface__"):
        geom = [geometry]
    else:
        geom = list(geometry)

    return da.rio.clip(geom, crs="EPSG:4326", all_touched=all_touched, drop=True)
