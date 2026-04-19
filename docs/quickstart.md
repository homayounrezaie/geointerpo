# Quickstart

!!! tip "No data or API keys needed"
    This guide uses `data="sample"` — a built-in synthetic dataset. Everything runs offline.

## Step 0 — Install

```bash
pip install "geointerpo[kriging,viz]"
```

## Step 1 — Run

```python
from geointerpo import Pipeline

result = Pipeline(
    data="sample",
    variable="temperature",
    boundary=(-114.5, 50.8, -113.8, 51.3),  # Calgary bbox
    method=["idw", "kriging", "spline"],
    resolution=0.05,
).run()
```

Expected output:

```
[1/5] Resolving boundary…
[2/5] Loading point data…
      60 points loaded
[3/5] Skipping DEM
[4/5] Interpolating with: idw, kriging, spline
      idw        RMSE=0.842  r=0.9831
      kriging    RMSE=0.623  r=0.9913
      spline     RMSE=0.711  r=0.9887
[5/5] Skipping GEE validation
```

## Step 2 — View results

```python
result.plot()           # side-by-side matplotlib figure
result.metrics_table()  # pandas DataFrame: RMSE, MAE, bias, r
```

## Step 3 — Save

```python
result.save("outputs/")
# outputs/idw.tif        ← GeoTIFF  (needs [raster])
# outputs/kriging.tif
# outputs/spline.tif
# outputs/cv_metrics.csv
# outputs/interpolation_comparison.png
```

!!! note "GeoTIFF export needs rioxarray"
    ```bash
    pip install "geointerpo[raster]"
    ```

---

## Next steps

<div class="grid cards" markdown>

-   :material-database:{ .lg .middle } **Use your own data**

    ---

    Pass a CSV file, GeoDataFrame, or live API source.

    ```python
    Pipeline(data="my_stations.csv", ...)
    ```

-   :material-map:{ .lg .middle } **Use a place name boundary**

    ---

    Any city or region, geocoded automatically.

    ```python
    Pipeline(boundary="Tehran, Iran", ...)
    ```

-   :material-chart-scatter-plot:{ .lg .middle } **Try all 15 methods**

    ---

    Compare every algorithm on the same data.

    [:octicons-arrow-right-24: Method reference](interpolators.md)

-   :material-satellite:{ .lg .middle } **Validate with satellite data**

    ---

    Compare against MODIS, CHIRPS, or Sentinel-5P.

    ```python
    Pipeline(..., validate_with_gee=True)
    ```

</div>
