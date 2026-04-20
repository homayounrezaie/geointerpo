"""Boundary loading and normalisation helpers.

Provides a single entry point ``load_boundary()`` that accepts:

* A file path  (.geojson / .gpkg / .shp / .zip)
* A GeoDataFrame or Shapely geometry (passthrough)
* A place-name string  ("Calgary, AB")  resolved via pluggable providers

All outputs are normalised to:
  - CRS EPSG:4326
  - Single dissolved geometry (union of all features)
  - Valid geometry  (shapely.make_valid repair applied)
  - Returned as a one-row GeoDataFrame

Example
-------
    from geointerpo.boundaries import load_boundary, boundary_bbox

    boundary = load_boundary("Calgary, AB")
    bbox     = boundary_bbox(boundary)

    # Or from a file:
    boundary = load_boundary("data/calgary_boundary.geojson")

    # Or pass geometry/GeoDataFrame directly:
    boundary = load_boundary(my_geodataframe)
"""

from __future__ import annotations

import pathlib
from typing import Union

import geopandas as gpd
import shapely.geometry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

BoundaryInput = Union[
    str,                                   # place name or file path
    pathlib.Path,                          # file path
    tuple,                                 # (min_lon, min_lat, max_lon, max_lat)
    gpd.GeoDataFrame,                      # passthrough
    shapely.geometry.base.BaseGeometry,    # passthrough
]


def load_boundary(
    source: BoundaryInput,
    provider: str = "nominatim",
    padding_deg: float = 0.0,
) -> gpd.GeoDataFrame:
    """Load, resolve, and normalise a study-area boundary.

    Parameters
    ----------
    source:
        * str / Path  →  file path (.geojson, .gpkg, .shp, .zip) **or** place name
        * GeoDataFrame  →  passed through, reprojected if needed
        * Shapely geometry  →  wrapped into a one-row GeoDataFrame
    provider:
        Place-name backend. Ignored when ``source`` is a file/geometry.
        'nominatim'  — free OpenStreetMap geocoder (default, no key).
        'osmnx'      — richer boundaries via osmnx (``pip install osmnx``).
    padding_deg:
        Optional uniform buffer added around the resolved boundary (degrees).
        Useful when you want a small margin outside the admin boundary.

    Returns
    -------
    GeoDataFrame with a single row, CRS=EPSG:4326, dissolved, make_valid'd.
    """

    gdf = _resolve_source(source, provider)
    gdf = _normalise(gdf)

    if padding_deg and padding_deg > 0:
        gdf = gpd.GeoDataFrame(
            geometry=[gdf.geometry.iloc[0].buffer(padding_deg)],
            crs="EPSG:4326",
        )

    return gdf


def boundary_bbox(boundary: gpd.GeoDataFrame) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) bounding box of the boundary."""
    geom = boundary.geometry.union_all() if hasattr(boundary.geometry, "union_all") \
           else boundary.geometry.unary_union
    min_lon, min_lat, max_lon, max_lat = geom.bounds
    return (min_lon, min_lat, max_lon, max_lat)


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

def _providers() -> dict:
    return {
        "nominatim": _nominatim_boundary,
        "osmnx":     _osmnx_boundary,
    }


def resolve_place(name: str, provider: str = "nominatim") -> gpd.GeoDataFrame:
    """Resolve a place name to a boundary GeoDataFrame using the given provider."""
    registry = _providers()
    if provider not in registry:
        raise ValueError(
            f"Unknown boundary provider '{provider}'. Available: {list(registry)}"
        )
    return registry[provider](name)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_source(source: BoundaryInput, provider: str) -> gpd.GeoDataFrame:
    if isinstance(source, gpd.GeoDataFrame):
        return source.copy()

    if isinstance(source, shapely.geometry.base.BaseGeometry):
        return gpd.GeoDataFrame(geometry=[source], crs="EPSG:4326")

    # (min_lon, min_lat, max_lon, max_lat) bbox tuple
    if isinstance(source, (tuple, list)) and len(source) == 4:
        from shapely.geometry import box as _box
        min_lon, min_lat, max_lon, max_lat = [float(v) for v in source]
        return gpd.GeoDataFrame(
            geometry=[_box(min_lon, min_lat, max_lon, max_lat)], crs="EPSG:4326"
        )

    if isinstance(source, pathlib.Path) or (
        isinstance(source, str) and _looks_like_path(source)
    ):
        return _load_file(pathlib.Path(source))

    # Treat as a place name
    if not isinstance(source, str):
        raise TypeError(
            f"source must be a file path, place name, 4-tuple bbox, GeoDataFrame, "
            f"or Shapely geometry; got {type(source).__name__}"
        )
    return resolve_place(source, provider=provider)


def _looks_like_path(s: str) -> bool:
    """Return True if the string looks like a file path (has a known geo extension)."""
    p = pathlib.Path(s)
    return p.suffix.lower() in {".geojson", ".gpkg", ".shp", ".zip", ".json"} or p.exists()


def _load_file(path: pathlib.Path) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Boundary file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".zip":
        gdf = gpd.read_file(f"zip://{path}")
    else:
        gdf = gpd.read_file(path)
    return gdf


def _normalise(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject → dissolve → make_valid → return one-row GDF."""
    # Reproject to WGS-84
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    # Dissolve to single geometry
    union = (
        gdf.geometry.union_all()
        if hasattr(gdf.geometry, "union_all")
        else gdf.geometry.unary_union
    )

    # Repair invalid geometry
    try:
        from shapely.validation import make_valid
        union = make_valid(union)
    except Exception:
        union = union.buffer(0)

    return gpd.GeoDataFrame(geometry=[union], crs="EPSG:4326")


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _nominatim_boundary(name: str) -> gpd.GeoDataFrame:
    """Resolve place name → polygon via Nominatim polygon_geojson."""
    try:
        import requests
    except ImportError as e:
        raise ImportError("Install requests: pip install requests") from e

    from shapely.geometry import shape

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": name,
        "format": "json",
        "limit": 1,
        "polygon_geojson": 1,
    }
    headers = {"User-Agent": "geointerpo/0.1 (https://github.com/homayounrezaie/geointerpo)"}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    results = resp.json()

    if not results:
        raise ValueError(f"Nominatim found no results for '{name}'")

    hit = results[0]
    geojson = hit.get("geojson")

    if geojson is None or geojson.get("type") not in (
        "Polygon", "MultiPolygon", "GeometryCollection"
    ):
        # Fall back to bounding box polygon
        bb = hit.get("boundingbox")  # [south, north, west, east]
        if bb is None:
            raise ValueError(
                f"Nominatim returned no polygon or bounding box for '{name}'. "
                "Try a more specific place name or provide a file."
            )
        s, n, w, e = [float(x) for x in bb]
        from shapely.geometry import box
        geom = box(w, s, e, n)
    else:
        geom = shape(geojson)

    return gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")


def _osmnx_boundary(name: str) -> gpd.GeoDataFrame:
    """Resolve place name → polygon via osmnx.geocode_to_gdf."""
    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError(
            "Install osmnx for richer boundary resolution: pip install osmnx"
        ) from e

    gdf = ox.geocode_to_gdf(name)
    return gdf[["geometry"]].copy()
