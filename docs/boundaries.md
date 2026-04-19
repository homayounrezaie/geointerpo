# Boundaries

Use the `boundary=` parameter to define your study area. geointerpo accepts five input formats and normalizes all of them to a single WGS-84 GeoDataFrame.

## Input formats

### Place name

Pass any city, region, or country name. geointerpo resolves it for free using OpenStreetMap's Nominatim geocoder — no API key required.

```python
Pipeline(boundary="Calgary, Alberta, Canada", ...)
Pipeline(boundary="Tehran, Iran", ...)
Pipeline(boundary="Bavaria, Germany", ...)
```

For higher-quality polygon boundaries, install `osmnx` and set `boundary_provider="osmnx"`:

```python
pip install osmnx
```

```python
Pipeline(boundary="Calgary, AB", boundary_provider="osmnx", ...)
```

### Bounding box

Pass a four-value tuple `(min_lon, min_lat, max_lon, max_lat)`:

```python
Pipeline(boundary=(-114.5, 50.8, -113.8, 51.3), ...)
```

### File path

Pass a path to any vector file. Supported formats: `.geojson`, `.gpkg`, `.shp`, `.zip`.

```python
Pipeline(boundary="data/study_area.geojson", ...)
```

### GeoDataFrame or Shapely geometry

Pass an object you already have in memory:

```python
import geopandas as gpd

my_gdf = gpd.read_file("region.geojson")
Pipeline(boundary=my_gdf, ...)
```

```python
from shapely.geometry import box

Pipeline(boundary=box(-114.5, 50.8, -113.8, 51.3), ...)
```

### No boundary

Omit `boundary=` entirely. The grid covers the extent of your point data plus `padding_deg` on each side.

```python
Pipeline(data="stations.csv", ...)
```

---

## What the boundary does

When you provide a boundary, geointerpo uses it for three things:

1. **Grid bbox** — builds the interpolation grid from the boundary's bounding box, extended by `padding_deg` (default `0.5°`) on each side.
2. **Output clipping** — after interpolation, sets grid cells outside the polygon to `NaN`. Requires the `[raster]` extra. Disable with `clip_to_boundary=False`.
3. **API scoping** — when you use a live data source (`data="meteostat"` etc.), the boundary bbox limits the station search area.

```python
Pipeline(
    boundary="Calgary, AB",
    padding_deg=0.2,       # tighter grid padding
    clip_to_boundary=True, # mask outside cells (default)
)
```

---

## Use boundaries directly

To work with boundaries outside the Pipeline:

```python
from geointerpo.boundaries import load_boundary, boundary_bbox

boundary = load_boundary("Calgary, Alberta, Canada")
# Returns a single-row, dissolved, make_valid'd GeoDataFrame in EPSG:4326

bbox = boundary_bbox(boundary)
# Returns (min_lon, min_lat, max_lon, max_lat)
```

`load_boundary` always returns a normalised GeoDataFrame regardless of input format.

---

## Troubleshooting

!!! failure "ValueError: Could not geocode location"
    Nominatim could not find the place name. Try one of the following:

    - Use a more specific name: `"Calgary, Alberta, Canada"` instead of `"Calgary"`
    - Pass a bbox tuple: `boundary=(-114.5, 50.8, -113.8, 51.3)`
    - Pass a file path: `boundary="my_region.geojson"`

!!! failure "Boundary clips everything to NaN"
    The boundary polygon does not overlap your station data. To diagnose:

    1. Run `boundary_bbox(boundary)` and confirm the bbox covers your stations.
    2. Check that `rioxarray` is installed: `pip install "geointerpo[raster]"`
    3. Set `clip_to_boundary=False` to rule out the clipping step.

!!! failure "ImportError: osmnx"
    `boundary_provider="osmnx"` requires a separate install:
    ```bash
    pip install osmnx
    ```
