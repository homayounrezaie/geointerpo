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

## Live API data with a DEM covariate

Pull real weather station data, add an elevation covariate, and compare several methods on the same boundary.

**1. Install**

```bash
pip install "geointerpo[full]"
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
    resolution=0.1,
).run()

print(result.metrics_table())
print(result.best_method())
result.save("outputs/")
```

!!! note
    `include_dem=True` downloads SRTM elevation and uses it as an extra feature for the `rk` and `gp` methods.

---

## Interactive map in Jupyter

Display the interpolated surface on a zoomable map with one call.

**1. Install**

```bash
pip install "geointerpo[interactive]"   # plotly (lightweight)
# or:
pip install "geointerpo[notebooks]"     # plotly + leafmap + full Jupyter stack
```

**2. Display**

```python
result = Pipeline(data="sample", method="kriging", resolution="5km").run()

# One call — auto-detects plotly or leafmap
fig = result.plot_interactive()
fig.show()   # in a script; omit in Jupyter (renders inline)
```

You can also call the underlying function directly for more control:

```python
from geointerpo.viz_interactive import plot_interactive

fig = plot_interactive(
    result.grid,
    stations=result.stations,
    backend="plotly",        # 'plotly' | 'leafmap' | 'auto'
    title="Temperature (°C)",
    cmap="RdYlBu_r",
    opacity=0.85,
)
```

---

## Auto-rank methods

Compare methods head-to-head and let geointerpo tell you which one won.

```python
from geointerpo import Pipeline

result = Pipeline(
    data="sample",
    variable="temperature",
    method=["idw", "kriging", "spline", "rbf", "gp"],
    resolution="10km",
    cv_folds=5,
).run()

print(result.best_method())       # 'kriging'
print(result.rank_methods())      # ranked DataFrame with rmse / mae / r / rank columns
result.plot_interactive()         # interactive map of the best method's grid
```

---

## Kriging variance surface

Visualise where your interpolation is most uncertain.

```python
from geointerpo import Pipeline
from geointerpo import viz
from geointerpo.data.samples import load_temperature

gdf  = load_temperature(n_stations=40, seed=0)
bbox = (5.0, 44.0, 25.0, 56.0)

result = Pipeline(data=gdf, method="kriging", resolution="5km", cv_folds=0).run()

var_da = result.variance_grids["kriging"]
fig = viz.plot_interpolated(var_da, title="Kriging variance (highest = uncertain)")
fig.savefig("kriging_variance.png", dpi=120, bbox_inches="tight")
```

---

## ML uncertainty intervals

Bootstrap prediction intervals from a Random Forest.

```python
from geointerpo.interpolators.ml import MLInterpolator
from geointerpo.data.samples import load_temperature

gdf  = load_temperature(n_stations=50, seed=1)
bbox = (5.0, 44.0, 25.0, 56.0)

model = MLInterpolator(method="rf", n_estimators=200).fit(gdf)
mean, lower, upper = model.predict_with_uncertainty(bbox, resolution="10km", alpha=0.1)
# mean, lower, upper are xr.DataArrays — 90% bootstrap interval
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
