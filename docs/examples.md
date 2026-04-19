# Examples

## Offline quickstart

The fastest way to try geointerpo. Uses built-in synthetic data — no files, no API keys, no network.

**1. Install**

```bash
pip install "geointerpo[kriging,viz]"
```

**2. Run**

```python
from geointerpo import Pipeline

result = Pipeline(
    data="sample",
    variable="temperature",
    boundary=(-114.5, 50.8, -113.8, 51.3),
    method=["idw", "kriging", "spline"],
    resolution=0.05,
).run()
```

**3. View and save**

```python
result.plot()
print(result.metrics_table())
result.save("outputs/")
```

---

## CSV file with a named boundary

Use your own point data with a place name as the study area.

**1. Install**

```bash
pip install "geointerpo[kriging,raster,viz,geo]"
```

**2. Prepare your CSV**

Your file needs longitude, latitude, and value columns. Column name aliases like `longitude`, `x`, `latitude`, `y` are detected automatically.

```
lon,lat,value
51.41,35.69,28.3
51.33,35.74,27.1
...
```

**3. Run**

```python
from geointerpo import Pipeline

result = Pipeline(
    data="my_stations.csv",
    boundary="Tehran, Iran",
    method=["kriging", "idw"],
    method_params={
        "kriging": {"variogram_model": "spherical"},
        "idw":     {"power": 2},
    },
    resolution=0.1,
    clip_to_boundary=True,
).run()

result.plot()
result.save("outputs/")
```

---

## Live API data with GEE validation

Pull real weather station data, add an elevation covariate, and compare the output against a MODIS satellite reference.

**1. Install and authenticate**

```bash
pip install "geointerpo[full,gee]"
earthengine authenticate
```

**2. Run**

```python
from geointerpo import Pipeline

result = Pipeline(
    data="meteostat",
    variable="temperature",
    date="2024-07-15",
    boundary="Bavaria, Germany",
    method=["kriging", "rk", "gp"],
    include_dem=True,
    validate_with_gee=True,
    resolution=0.1,
).run()

print(result.metrics_table())
print(result.gee_metrics)
result.save("outputs/")
```

!!! note
    `include_dem=True` downloads SRTM elevation and uses it as an extra feature for the `rk` and `gp` methods.

---

## Interactive map in Jupyter

Display the interpolated surface on an interactive map after running the pipeline.

**1. Install**

```bash
pip install "geointerpo[notebooks,raster]"
```

**2. Display**

```python
import leafmap
import tempfile

da = result.grid
with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
    tmp = f.name

da.rio.set_spatial_dims(x_dim="lon", y_dim="lat") \
  .rio.write_crs("EPSG:4326") \
  .rio.to_raster(tmp)

m = leafmap.Map(center=[float(da.lat.mean()), float(da.lon.mean())], zoom=6)
m.add_raster(tmp, colormap="RdYlBu_r", layer_name="Interpolated")
m  # displays inline in Jupyter
```

---

## Run all 15 methods and save one image each

Generate one output PNG per method for visual comparison.

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from geointerpo import Pipeline
from geointerpo import viz
from geointerpo.data.samples import load_temperature

bbox = (-120.0, 48.5, -109.5, 60.5)
gdf  = load_temperature(bbox=bbox)

methods = [
    "idw", "kriging", "uk", "natural_neighbor",
    "spline", "spline_tension", "trend", "rbf",
    "nearest", "linear", "cubic",
    "gp", "rf", "gbm", "rk",
]

for method in methods:
    try:
        result = Pipeline(
            data=gdf,
            boundary="Alberta, Canada",
            method=method,
            resolution=0.25,
        ).run()
        fig = viz.plot_interpolated(
            result.grid,
            stations=gdf,
            boundary=result.boundary,
            title=method.replace("_", " ").title(),
        )
        fig.savefig(f"outputs/methods/{method}.png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"{method} — saved")
    except Exception as e:
        print(f"{method} — skipped ({e})")
```

---

## CLI and YAML config

Run pipelines from the terminal without writing Python:

```bash
geointerpo demo temperature         # offline temperature demo
geointerpo benchmark                # run all methods and print RMSE table
geointerpo run configs/calgary.yml  # run from a YAML config file
```

**Example YAML config:**

```yaml
data: sample
variable: temperature
boundary: "Calgary, Alberta, Canada"
method:
  - idw
  - kriging
  - spline
resolution: 0.1
output_dir: outputs/calgary/
```
