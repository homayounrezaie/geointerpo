# Boundaries

The `boundary=` parameter accepts five input types. All are normalised to a WGS-84 GeoDataFrame before use.

## Place name (Nominatim)

No API key required. Uses OpenStreetMap's Nominatim geocoder.

```python
Pipeline(boundary="Calgary, Alberta, Canada", ...)
Pipeline(boundary="Tehran, Iran", ...)
Pipeline(boundary="Bavaria, Germany", ...)
```

For more precise polygons (richer OSM data) install osmnx:

```python
Pipeline(boundary="Calgary, AB", boundary_provider="osmnx", ...)
```

## Four-corner bbox

```python
# (min_lon, min_lat, max_lon, max_lat)
Pipeline(boundary=(-114.5, 50.8, -113.8, 51.3), ...)
```

## File path

```python
Pipeline(boundary="data/study_area.geojson", ...)   # .geojson / .gpkg / .shp / .zip
```

## GeoDataFrame or Shapely geometry

```python
import geopandas as gpd
my_gdf = gpd.read_file("region.geojson")
Pipeline(boundary=my_gdf, ...)

from shapely.geometry import box
Pipeline(boundary=box(-114.5, 50.8, -113.8, 51.3), ...)
```

## No boundary

```python
Pipeline(data="stations.csv", ...)   # grid covers the extent of the point data
```

---

## What the boundary does

1. **Derives the grid bbox** — the interpolation grid is built from the boundary's bounding box, with `padding_deg=0.5` added on each side (configurable).
2. **Clips the output** — after interpolation, grid cells outside the boundary polygon are set to NaN (requires `[raster]` extra). Disable with `clip_to_boundary=False`.
3. **Scopes API fetches** — when `data="meteostat"` etc., the boundary bbox is used to limit the station search radius.

```python
Pipeline(
    boundary="Calgary, AB",
    padding_deg=0.2,         # tighter grid around the boundary
    clip_to_boundary=True,   # mask cells outside the polygon (default)
)
```

---

## Direct use

```python
from geointerpo.boundaries import load_boundary, boundary_bbox

boundary = load_boundary("Calgary, Alberta, Canada")  # → GeoDataFrame (EPSG:4326)
bbox = boundary_bbox(boundary)                        # → (min_lon, min_lat, max_lon, max_lat)
```

`load_boundary` always returns a single-row, dissolved, `make_valid`'d GeoDataFrame in WGS-84.

---

## Common errors

**`ValueError: Could not geocode location 'X'`**  
Nominatim couldn't find the place name. Try a more specific name, or pass a bbox tuple or file instead.

**Boundary clips everything to NaN**  
The boundary polygon may not overlap the station data. Check that `boundary_bbox(boundary)` covers the same region as your stations. Also confirm `rioxarray` is installed (`pip install "geointerpo[raster]"`).

**`ImportError: osmnx`**  
`boundary_provider="osmnx"` requires `pip install osmnx`.
