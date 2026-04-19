# Examples

Three canonical workflows — from simplest to most complete.

---

## 1. Offline quickstart (no data, no network)

The fastest way to try geointerpo. Uses built-in synthetic stations.

```bash
pip install "geointerpo[kriging,viz]"
```

```python
from geointerpo import Pipeline

result = Pipeline(
    data="sample",
    variable="temperature",
    boundary=(-114.5, 50.8, -113.8, 51.3),   # Calgary bbox
    method=["idw", "kriging", "spline"],
    resolution=0.05,
).run()

result.plot()
print(result.metrics_table())
result.save("outputs/")
```

---

## 2. CSV file + named boundary

Your own point data, geocoded study area, two methods compared.

```bash
pip install "geointerpo[kriging,raster,viz,geo]"
```

```python
from geointerpo import Pipeline

result = Pipeline(
    data="my_stations.csv",            # lon, lat, value columns
    boundary="Tehran, Iran",           # geocoded via Nominatim (free, no key)
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

Expected CSV format:

```
lon,lat,value
51.41,35.69,28.3
51.33,35.74,27.1
...
```

Column name aliases (`longitude`, `x`, `latitude`, `y`) are auto-detected.

---

## 3. Live API data + GEE validation

Full pipeline with live weather station data, DEM covariate, and MODIS LST validation.

```bash
pip install "geointerpo[full,gee]"
earthengine authenticate
```

```python
from geointerpo import Pipeline

result = Pipeline(
    data="meteostat",
    variable="temperature",
    date="2024-07-15",
    boundary="Bavaria, Germany",
    method=["kriging", "rk", "gp"],
    include_dem=True,          # SRTM elevation as covariate
    validate_with_gee=True,    # compare against MODIS LST
    resolution=0.1,
).run()

print(result.metrics_table())
print("GEE validation:", result.gee_metrics)
result.save("outputs/")
```

---

## Interactive notebook map

After running the pipeline, display the result in an interactive leafmap inside Jupyter:

```bash
pip install "geointerpo[notebooks]"
```

```python
import leafmap, tempfile

da = result.grid
with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
    tmp = f.name
da.rio.set_spatial_dims(x_dim="lon", y_dim="lat").rio.write_crs("EPSG:4326").rio.to_raster(tmp)

m = leafmap.Map(center=[float(da.lat.mean()), float(da.lon.mean())], zoom=6)
m.add_raster(tmp, colormap="RdYlBu_r", layer_name="interpolated")
m   # displays inline in Jupyter
```

---

## Run all 15 methods and save one PNG each

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from geointerpo import Pipeline
from geointerpo import viz
from geointerpo.data.samples import load_temperature

bbox = (-120.0, 48.5, -109.5, 60.5)
gdf  = load_temperature(bbox=bbox)

all_methods = [
    "idw", "kriging", "uk", "natural_neighbor",
    "spline", "spline_tension", "trend", "rbf",
    "nearest", "linear", "cubic",
    "gp", "rf", "gbm", "rk",
]

for method in all_methods:
    try:
        result = Pipeline(
            data=gdf,
            boundary=bbox,
            method=method,
            resolution=0.25,
            clip_to_boundary=False,
        ).run()
        fig = viz.plot_interpolated(result.grid, stations=gdf, title=method)
        fig.savefig(f"outputs/methods/{method}.png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"  {method} — saved")
    except Exception as e:
        print(f"  {method} — SKIPPED ({e})")
```

---

## Via CLI

```bash
geointerpo demo temperature         # offline temperature demo
geointerpo benchmark                # run all methods and print RMSE table
geointerpo run configs/calgary.yml  # run a YAML config
```

YAML config example (`configs/calgary.yml`):

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
