"""Covariate helpers — elevation (DEM) and land cover.

DEM sources (in priority order):
  1. GEE SRTM   — if earthengine-api is authenticated.
  2. srtm.py    — lightweight pure-Python SRTM downloader (pip install srtm.py).
  3. Synthetic  — smooth procedural surface, so offline demos always work.

The returned DataArray matches the same lon/lat grid used by the interpolators.
"""

from __future__ import annotations

from typing import Tuple
import numpy as np
import xarray as xr

BBox = Tuple[float, float, float, float]


def fetch_dem(
    bbox: BBox,
    resolution: float = 0.1,
    source: str = "auto",
) -> xr.DataArray:
    """Fetch a DEM (elevation in metres) as an xr.DataArray on a regular grid.

    Parameters
    ----------
    bbox:       (min_lon, min_lat, max_lon, max_lat)
    resolution: grid spacing in degrees
    source:     'gee' | 'srtm' | 'synthetic' | 'auto'
                'auto' tries gee → srtm → synthetic in order.
    """
    if source == "auto":
        for attempt in ("gee", "srtm", "synthetic"):
            try:
                return fetch_dem(bbox, resolution, source=attempt)
            except Exception:
                continue
        raise RuntimeError("All DEM sources failed")

    if source == "gee":
        return _fetch_dem_gee(bbox, resolution)
    if source == "srtm":
        return _fetch_dem_srtm(bbox, resolution)
    if source == "synthetic":
        return _fetch_dem_synthetic(bbox, resolution)
    raise ValueError(f"Unknown DEM source '{source}'. Choose 'gee', 'srtm', 'synthetic', or 'auto'.")


# ---------------------------------------------------------------------------
# Source implementations
# ---------------------------------------------------------------------------

def _fetch_dem_gee(bbox: BBox, resolution: float) -> xr.DataArray:
    try:
        import ee
    except ImportError as e:
        raise ImportError("Install earthengine-api: pip install 'geointerpo[gee]'") from e

    try:
        ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize()

    import requests, io
    import rioxarray  # noqa: F401

    min_lon, min_lat, max_lon, max_lat = bbox
    region = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
    scale_m = max(30, int(resolution * 111_320))

    srtm = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(region)
    url = srtm.getDownloadURL({
        "region": region,
        "scale": scale_m,
        "format": "GEO_TIFF",
    })
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with io.BytesIO(resp.content) as buf:
        da = xr.open_dataarray(buf, engine="rasterio").squeeze(drop=True)
    da = da.rename({"x": "lon", "y": "lat"})
    da.name = "elevation"
    da.attrs["source"] = "GEE SRTM"
    return da


def _fetch_dem_srtm(bbox: BBox, resolution: float) -> xr.DataArray:
    try:
        import srtm
    except ImportError as e:
        raise ImportError("Install srtm.py: pip install srtm.py") from e

    min_lon, min_lat, max_lon, max_lat = bbox
    lons = np.arange(min_lon, max_lon + resolution, resolution)
    lats = np.arange(min_lat, max_lat + resolution, resolution)
    lon_g, lat_g = np.meshgrid(lons, lats)

    data = srtm.get_data()
    elev = np.vectorize(lambda la, lo: data.get_elevation(la, lo) or 0)(lat_g, lon_g)

    da = xr.DataArray(
        elev.astype(float),
        dims=["lat", "lon"],
        coords={"lat": lats, "lon": lons},
        name="elevation",
        attrs={"source": "SRTM (srtm.py)", "units": "m"},
    )
    return da


def _fetch_dem_synthetic(bbox: BBox, resolution: float) -> xr.DataArray:
    """Smooth procedural elevation — useful for offline demos."""
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = np.arange(min_lon, max_lon + resolution, resolution)
    lats = np.arange(min_lat, max_lat + resolution, resolution)
    lon_g, lat_g = np.meshgrid(lons, lats)

    # mountainous wave pattern
    elev = (
        500
        + 400 * np.sin(np.radians(lon_g) * 4)
        + 300 * np.cos(np.radians(lat_g) * 5)
        + 200 * np.sin(np.radians(lon_g + lat_g) * 3)
    )
    elev = np.clip(elev, 0, None)

    da = xr.DataArray(
        elev,
        dims=["lat", "lon"],
        coords={"lat": lats, "lon": lons},
        name="elevation",
        attrs={"source": "synthetic", "units": "m"},
    )
    return da


def make_covariate_fn(dem: xr.DataArray):
    """Return a covariates_fn(xs, ys) that samples elevation at projected coords.

    xs, ys are in the interpolator's projected CRS (metres).  The function
    reprojects them back to WGS-84, then bilinearly samples the DEM.

    Usage:
        dem = fetch_dem(bbox)
        model = MLInterpolator(method='rf', covariates_fn=make_covariate_fn(dem))
    """
    from scipy.interpolate import RegularGridInterpolator

    lons = dem.lon.values
    lats = dem.lat.values
    values = dem.values  # shape (nlat, nlon)

    # Regular grid interpolator in lon/lat space
    _rgi = RegularGridInterpolator(
        (lats, lons), values, method="linear", bounds_error=False, fill_value=0.0
    )

    def covariates_fn(xs, ys, proj_crs=None):
        if proj_crs is not None:
            from pyproj import Transformer
            t = Transformer.from_crs(proj_crs, "EPSG:4326", always_xy=True)
            lons_q, lats_q = t.transform(xs, ys)
        else:
            lons_q, lats_q = xs, ys
        pts = np.column_stack([lats_q, lons_q])
        return _rgi(pts).reshape(-1, 1)

    return covariates_fn
