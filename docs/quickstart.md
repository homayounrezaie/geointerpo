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
    resolution="2km",   # ← accepts km strings (new in v0.2)
).run()
```

Expected output:

```
[1/5] Resolving boundary…
[2/5] Loading point data…
      60 points loaded
[3/5] Skipping DEM
[4/5] Interpolating with: idw, kriging, spline
      idw                        RMSE=0.842  r=0.9831
      kriging                    RMSE=0.623  r=0.9913
      spline                     RMSE=0.711  r=0.9887

[5/5] Best method by RMSE: kriging
      rank  rmse    mae    bias       r
      kriging   1  0.623  0.491  0.012  0.9913
      spline    2  0.711  0.564  0.008  0.9887
      idw       3  0.842  0.661  0.031  0.9831
```

## Step 2 — View results

```python
result.plot()               # side-by-side matplotlib figure
result.plot_interactive()   # zoomable plotly map (needs: pip install plotly)
result.metrics_table()      # pandas DataFrame: RMSE, MAE, bias, r
result.best_method()        # → "kriging"
result.rank_methods()       # full ranked DataFrame
```

## Step 3 — Uncertainty

```python
# Kriging variance surface
from geointerpo.interpolators import KrigingInterpolator
model = KrigingInterpolator().fit(result.stations)
mean_da, var_da = model.predict_with_variance(result.bbox)

# Random Forest bootstrap intervals
from geointerpo.interpolators import MLInterpolator
rf = MLInterpolator(method="rf").fit(result.stations)
mean, lower, upper = rf.predict_with_uncertainty(result.bbox, alpha=0.1)
```

## Step 4 — Save

```python
result.save("outputs/")
# outputs/idw.tif                    ← GeoTIFF  (needs [raster])
# outputs/kriging.tif
# outputs/spline.tif
# outputs/kriging_variance.tif       ← new: variance surface
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

-   :material-satellite:{ .lg .middle } **ERA5 / NASA POWER**

    ---

    Fetch reanalysis data — no station networks needed.

    ```python
    Pipeline(data="nasapower", variable="temperature", date="2024-07-15", ...)
    Pipeline(data="era5", variable="temperature", date="2024-07-15", ...)
    ```

-   :material-chart-scatter-plot:{ .lg .middle } **Try all 17 methods**

    ---

    Compare every algorithm on the same data.

    [:octicons-arrow-right-24: Method reference](interpolators.md)

</div>
