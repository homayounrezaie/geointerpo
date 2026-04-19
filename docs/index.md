# geointerpo

**Python spatial interpolation toolkit** — point data, 15 methods, boundaries, raster export, and GEE validation.

Lightweight core. Optional extras. PyPI-friendly.

---

## Start here

<div class="grid cards" markdown>

- :material-download: **[Install](install.md)**

    Get up and running in one command.  
    Core, extras, and source installs.

- :material-rocket-launch: **[Quickstart](quickstart.md)**

    Run your first interpolation in under 5 minutes.  
    No data, no API keys required.

- :material-map-marker-radius: **[Boundaries](boundaries.md)**

    Load study areas from place names, files, or polygons.

- :material-function-variant: **[Methods](interpolators.md)**

    15 algorithms with visual output gallery.

</div>

---

## Three-step workflow

```
data=          →   boundary=           →   method=
point input        study-area polygon      interpolation algorithm(s)
```

```python
from geointerpo import Pipeline

result = Pipeline(
    data="stations.csv",                    # (1) point data
    boundary="Calgary, Alberta, Canada",    # (2) study area
    method=["idw", "kriging", "spline"],    # (3) methods to compare
).run()

result.plot()            # side-by-side matplotlib figure
result.metrics_table()   # cross-validation RMSE / MAE / r
result.save("outputs/")  # GeoTIFF + PNG + metrics CSV
```

---

## Feature highlights

| Layer | What's included |
|---|---|
| **Pipeline** | 3-step workflow — data → boundary → method |
| **Interpolation** | 15 algorithms, 24 method keys (ArcGIS-equivalent + GP, RF, GBM, RK) |
| **Point data** | CSV · geo file · GeoDataFrame · live APIs (Meteostat, OpenAQ, Open-Meteo) |
| **Boundary** | Place name · file · bbox tuple · polygon / GeoDataFrame |
| **Elevation** | SRTM DEM covariate (optional) |
| **Export** | GeoTIFF, NetCDF, metrics CSV |
| **Validation** | Compare against MODIS, CHIRPS, Sentinel-5P via Google Earth Engine (optional) |
| **Visualization** | Static matplotlib via `[viz]` extra |

---

## Method output gallery

All 15 methods on the same dataset — 60 weather stations over Alberta, Canada, 0.25° grid:

<table>
<tr>
  <td align="center"><img src="assets/methods/idw.png" width="220"/><br/><b>IDW</b></td>
  <td align="center"><img src="assets/methods/kriging.png" width="220"/><br/><b>Ordinary Kriging</b></td>
  <td align="center"><img src="assets/methods/uk.png" width="220"/><br/><b>Universal Kriging</b></td>
</tr>
<tr>
  <td align="center"><img src="assets/methods/natural_neighbor.png" width="220"/><br/><b>Natural Neighbor</b></td>
  <td align="center"><img src="assets/methods/spline.png" width="220"/><br/><b>Spline (Regularized)</b></td>
  <td align="center"><img src="assets/methods/spline_tension.png" width="220"/><br/><b>Spline Tension</b></td>
</tr>
<tr>
  <td align="center"><img src="assets/methods/trend.png" width="220"/><br/><b>Trend Surface</b></td>
  <td align="center"><img src="assets/methods/rbf.png" width="220"/><br/><b>RBF</b></td>
  <td align="center"><img src="assets/methods/nearest.png" width="220"/><br/><b>Nearest Neighbor</b></td>
</tr>
<tr>
  <td align="center"><img src="assets/methods/linear.png" width="220"/><br/><b>Linear (Delaunay)</b></td>
  <td align="center"><img src="assets/methods/cubic.png" width="220"/><br/><b>Cubic (Clough-Tocher)</b></td>
  <td align="center"><img src="assets/methods/gp.png" width="220"/><br/><b>Gaussian Process</b></td>
</tr>
<tr>
  <td align="center"><img src="assets/methods/rf.png" width="220"/><br/><b>Random Forest</b></td>
  <td align="center"><img src="assets/methods/gbm.png" width="220"/><br/><b>Gradient Boosting</b></td>
  <td align="center"><img src="assets/methods/rk.png" width="220"/><br/><b>Regression Kriging</b></td>
</tr>
</table>

→ See [Methods](interpolators.md) for a full description of each algorithm.

---

## Stack

**Core:** `scipy` · `geopandas` · `shapely` · `pyproj` · `xarray` · `numpy` · `pandas` · `requests`

**Optional:** `pykrige` · `scikit-learn` · `rasterio` · `rioxarray` · `meteostat` · `openaq` · `matplotlib` · `geopy` · `earthengine-api`
