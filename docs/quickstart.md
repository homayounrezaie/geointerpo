# Quickstart

No data files, no API keys, no internet connection required.

## Step 0 — Install

```bash
pip install "geointerpo[kriging,viz]"
```

## Step 1 — Run the offline demo

```python
from geointerpo import Pipeline

result = Pipeline(
    data="sample",                           # built-in synthetic stations
    variable="temperature",
    boundary=(-114.5, 50.8, -113.8, 51.3),  # Calgary bbox (lon_min, lat_min, lon_max, lat_max)
    method=["idw", "kriging", "spline"],
    resolution=0.05,
).run()
```

Output:

```
[1/5] Resolving boundary…
[2/5] Loading point data…
      60 points loaded
      bbox = (-115.0, 50.3, -113.3, 51.8)
[3/5] Skipping DEM
[4/5] Interpolating with: idw, kriging, spline
      idw                        RMSE=0.842  r=0.9831
      kriging                    RMSE=0.623  r=0.9913
      spline                     RMSE=0.711  r=0.9887
[5/5] Skipping GEE validation
```

## Step 2 — View results

```python
result.plot()            # side-by-side matplotlib figure (requires [viz])
result.metrics_table()   # pandas DataFrame with RMSE, MAE, bias, r
```

## Step 3 — Save outputs

```python
result.save("outputs/")
# outputs/idw.tif       ← GeoTIFF (requires [raster])
# outputs/kriging.tif
# outputs/spline.tif
# outputs/cv_metrics.csv
# outputs/interpolation_comparison.png
```

## Next steps

- Use your own CSV: `data="my_stations.csv"`
- Use a place name boundary: `boundary="Tehran, Iran"`
- Try all 15 methods: `method=list(Pipeline.ALL_METHODS)`
- Add DEM covariate: `include_dem=True`
- Validate against satellite: `validate_with_gee=True`

→ Full examples in [Examples](examples.md)  
→ All method keys in [Methods](interpolators.md)  
→ Boundary options in [Boundaries](boundaries.md)
