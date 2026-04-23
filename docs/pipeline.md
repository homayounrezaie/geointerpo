# Pipeline

`Pipeline` is the main entry point. It takes your data, study area, and method choice, runs the interpolation, and returns a result object with grids, metrics, and export helpers.

```python
from geointerpo import Pipeline

result = Pipeline(
    data=...,      # step 1 — point data
    boundary=...,  # step 2 — study area
    method=...,    # step 3 — interpolation method(s)
).run()
```

---

## Step 1 — Provide point data (`data=`)

| Value | What it loads |
|---|---|
| `"stations.csv"` | CSV with longitude, latitude, and value columns |
| `"stations.shp"` | Any vector file: `.shp`, `.geojson`, `.gpkg`, `.zip` |
| `my_gdf` | A GeoDataFrame already in memory |
| `"meteostat"` | Live weather data from Meteostat |
| `"openaq"` | Live air quality data from OpenAQ |
| `"openmeteo"` | Live reanalysis data from Open-Meteo |
| `"sample"` | Built-in synthetic dataset — no network needed |

**CSV files:** geointerpo detects column names automatically. It recognises `lon`, `longitude`, `x` for longitude and `lat`, `latitude`, `y` for latitude. Override with `lon_col=`, `lat_col=`, and `value_col=`:

```python
Pipeline(data="my_data.csv", lon_col="x", lat_col="y", value_col="temp", ...)
```

**Live API sources:** pair with `variable=` and `date=`:

```python
Pipeline(data="meteostat",  variable="temperature",  date="2024-07-15", ...)
Pipeline(data="openaq",     variable="pm25",          date="2024-07-15", ...)
Pipeline(data="openmeteo",  variable="precipitation", date="2024-07-15", ...)
```

---

## Step 2 — Define the study area (`boundary=`)

See [Boundaries](boundaries.md) for all input formats. Quick options:

```python
boundary="Calgary, Alberta, Canada"      # place name (Nominatim)
boundary=(-114.5, 50.8, -113.8, 51.3)   # (min_lon, min_lat, max_lon, max_lat)
boundary="data/region.geojson"           # file path
boundary=my_gdf                          # GeoDataFrame
```

---

## Step 3 — Choose a method (`method=`)

```python
method="kriging"                              # single method
method=["idw", "kriging", "spline", "rbf"]   # run multiple and compare
```

See [Methods](interpolators.md) for all 24 method keys.

**Override parameters per method:**

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

## All parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | str / Path / GeoDataFrame | required | Point data source |
| `boundary` | str / tuple / GeoDataFrame | `None` | Study area |
| `method` | str or list[str] | `"kriging"` | Method key(s) to run |
| `variable` | str | `"value"` | Column name or API variable |
| `date` | str | yesterday | ISO date `"YYYY-MM-DD"` for API sources |
| `lon_col` | str | `"lon"` | CSV longitude column |
| `lat_col` | str | `"lat"` | CSV latitude column |
| `value_col` | str | `"value"` | CSV or GeoDataFrame value column |
| `resolution` | float | `0.25` | Grid cell size in degrees |
| `padding_deg` | float | `0.5` | Degrees of padding around boundary bbox |
| `method_params` | dict | `{}` | Per-method parameter overrides |
| `clip_to_boundary` | bool | `True` | Mask grid cells outside the boundary polygon |
| `include_dem` | bool | `False` | Add SRTM elevation as a covariate for ML and RK methods |
| `validate_with_gee` | bool | `False` | Compare output against a GEE reference raster |
| `cv_folds` | int | `5` | Number of spatial cross-validation folds |
| `boundary_provider` | str | `"nominatim"` | `"nominatim"` (default) or `"osmnx"` |
| `search_radius` | SearchRadius | `None` | Restrict the local station neighbourhood used per prediction |

---

## Work with results

`Pipeline.run()` returns an `InterpolationResult`:

```python
result.grid          # xr.DataArray — primary method surface (WGS-84)
result.grids         # dict[str, xr.DataArray] — one grid per method
result.stations      # gpd.GeoDataFrame — your input points
result.cv_metrics    # dict[str, dict] — RMSE, MAE, bias, r, n per method
result.boundary      # gpd.GeoDataFrame or None
result.gee_metrics   # dict or None — only when validate_with_gee=True
result.gee_reference # xr.DataArray or None
```

**Visualize:**

```python
result.plot()           # side-by-side matplotlib figure (requires [viz])
result.metrics_table()  # pandas DataFrame with RMSE, MAE, bias, r
```

**Export:**

```python
result.save("outputs/")
# writes: <method>.tif, cv_metrics.csv, interpolation_comparison.png
```

---

## Limit the search radius

Use `SearchRadius` to control how many stations each prediction point uses — matching the ArcGIS Spatial Analyst `SearchRadius` parameter:

```python
from geointerpo import Pipeline, SearchRadius

# Use the 15 nearest stations
Pipeline(..., search_radius=SearchRadius.variable(n=15))

# Use all stations within 100 km
Pipeline(..., search_radius=SearchRadius.fixed(distance_m=100_000))
```

!!! note
    `SearchRadius.variable(n=12)` is the ArcGIS default.

!!! info
    `variable` selects the nearest `n` stations separately for each grid cell.
    `fixed` uses all stations within `distance_m` metres of each grid cell.

!!! warning
    Fixed-radius search can leave `NaN` gaps if no stations fall inside the radius,
    or if too few local stations are available for the chosen interpolator.

!!! note
    Search-radius neighbourhoods are applied by the deterministic interpolators
    (`idw`, `kriging`, `natural_neighbor`, `nearest`, `linear`, `cubic`,
    `rbf`, `spline`, `spline_tension`, `trend`).
    ML-based methods (`gp`, `rf`, `gbm`, `rk`) remain global and ignore
    `search_radius`.

!!! tip
    Local search can be noticeably slower for methods that need to refit a
    local model per grid cell, especially kriging and spline-style methods.
