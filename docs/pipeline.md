# Pipeline

`Pipeline` is the three-step entry point that mirrors the ArcGIS Spatial Analyst workflow.

```python
from geointerpo import Pipeline

result = Pipeline(
    data=...,        # Step 1 — point data
    boundary=...,    # Step 2 — study area
    method=...,      # Step 3 — interpolation method(s)
    **options,
).run()
```

---

## Step 1 — `data=`

| Value | What it does |
|---|---|
| `"stations.csv"` | CSV with lon/lat/value columns |
| `"stations.shp"` | Any geo file (.shp / .geojson / .gpkg / .zip) |
| `my_gdf` | GeoDataFrame already in memory |
| `"meteostat"` | Live weather station data via Meteostat |
| `"openaq"` | Live air quality data via OpenAQ |
| `"openmeteo"` | Live forecast/reanalysis data via Open-Meteo |
| `"sample"` | Built-in synthetic data — no network needed |

CSV column auto-detection understands `lon`, `longitude`, `x`, `X` for longitude, and `lat`, `latitude`, `y`, `Y` for latitude. Override with `lon_col=`, `lat_col=`, `value_col=`.

```python
Pipeline(data="my_data.csv", lon_col="x", lat_col="y", value_col="temp", ...)
```

For API sources, pair with `variable=` and `date=`:

```python
Pipeline(data="meteostat",  variable="temperature",  date="2024-07-15", ...)
Pipeline(data="openaq",     variable="pm25",          date="2024-07-15", ...)
Pipeline(data="openmeteo",  variable="precipitation", date="2024-07-15", ...)
```

---

## Step 2 — `boundary=`

See [Boundaries](boundaries.md) for the full reference.

Quick options:

```python
boundary="Calgary, Alberta, Canada"      # place name via Nominatim
boundary=(-114.5, 50.8, -113.8, 51.3)   # (min_lon, min_lat, max_lon, max_lat)
boundary="data/region.geojson"           # file path
boundary=my_gdf                          # GeoDataFrame
```

---

## Step 3 — `method=`

```python
method="kriging"                              # single method
method=["idw", "kriging", "spline", "rbf"]    # compare multiple
```

All 24 method keys: see [Methods](interpolators.md).

### Per-method parameters

```python
Pipeline(
    method=["idw", "kriging", "rbf"],
    method_params={
        "idw":     {"power": 3},
        "kriging": {"variogram_model": "spherical", "nlags": 12},
        "rbf":     {"kernel": "thin_plate_spline"},
    },
)
```

---

## All options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | str / Path / GeoDataFrame | required | Point data source |
| `boundary` | str / tuple / GeoDataFrame | `None` | Study area |
| `method` | str / list[str] | `"kriging"` | Method key(s) |
| `variable` | str | `"value"` | Variable name / API variable |
| `date` | str | yesterday | ISO date for API sources |
| `lon_col` | str | `"lon"` | CSV longitude column |
| `lat_col` | str | `"lat"` | CSV latitude column |
| `value_col` | str | `"value"` | CSV / GDF value column |
| `resolution` | float | `0.25` | Grid cell size in degrees |
| `padding_deg` | float | `0.5` | Padding around boundary bbox |
| `method_params` | dict | `{}` | Per-method parameter overrides |
| `clip_to_boundary` | bool | `True` | Mask output to boundary polygon |
| `include_dem` | bool | `False` | Add SRTM elevation covariate (ML/RK methods) |
| `validate_with_gee` | bool | `False` | Compare against GEE reference raster |
| `cv_folds` | int | `5` | Spatial cross-validation folds |
| `boundary_provider` | str | `"nominatim"` | `"nominatim"` or `"osmnx"` |
| `search_radius` | SearchRadius | `None` | Limit stations used per prediction |

---

## InterpolationResult

`Pipeline.run()` returns an `InterpolationResult` with:

```python
result.grid          # xr.DataArray — primary method's output
result.grids         # dict[method_key → xr.DataArray] — all methods
result.stations      # gpd.GeoDataFrame — input points
result.cv_metrics    # dict[method_key → {rmse, mae, bias, r, n}]
result.boundary      # gpd.GeoDataFrame or None
result.gee_metrics   # dict or None (if validate_with_gee=True)
result.gee_reference # xr.DataArray or None

result.plot()            # matplotlib side-by-side figure
result.metrics_table()   # pandas DataFrame of CV metrics
result.save("outputs/")  # GeoTIFF + PNG + metrics CSV
```

---

## SearchRadius

Mirror of the ArcGIS `SearchRadius` parameter:

```python
from geointerpo import Pipeline, SearchRadius

# Variable: use n nearest stations (default in ArcGIS: n=12)
Pipeline(..., search_radius=SearchRadius.variable(n=15))

# Fixed: use all stations within distance_m metres
Pipeline(..., search_radius=SearchRadius.fixed(distance_m=100_000))
```
