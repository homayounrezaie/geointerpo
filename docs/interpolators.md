# Interpolation Methods

**15 algorithms · 24 method keys.**  
Every method shares the same interface: `.fit(gdf)` → `.predict(bbox, resolution)` → `xr.DataArray`.

---

## Output gallery

All 15 methods on the same dataset — 60 weather stations, Alberta, Canada, 0.25° grid:

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

---

## ArcGIS Spatial Analyst equivalents

| # | `method=` key | Aliases | Description | Key params |
|---|---|---|---|---|
| 1 | `"idw"` | — | Inverse Distance Weighting | `power` |
| 2 | `"kriging"` | `"ok"`, `"ordinary_kriging"` | Ordinary Kriging | `variogram_model`, `nlags` |
| 3 | `"uk"` | `"universal_kriging"` | Universal Kriging — detrended residuals | `variogram_model` |
| 4 | `"natural_neighbor"` | `"nn"` | Voronoi/Sibson area-stealing weights | — |
| 5 | `"spline"` | `"spline_regularized"` | Minimum curvature spline | `smoothing` |
| 6 | `"spline_tension"` | — | Tension spline — pulls toward flat | `smoothing` |
| 7 | `"trend"` | — | Global polynomial trend surface | `order` (1–12) |
| 8 | `"nearest"` | — | Nearest-neighbour (scipy griddata) | — |

## Additional methods

| # | `method=` key | Aliases | Description | Key params |
|---|---|---|---|---|
| 9 | `"rbf"` | — | Radial Basis Functions — 8 kernels | `kernel`, `smoothing` |
| 10 | `"linear"` | — | Delaunay triangulation, linear barycentric | — |
| 11 | `"cubic"` | — | Clough-Tocher C1 cubic | — |
| 12 | `"gp"` | `"gaussian_process"` | Gaussian Process — outputs mean + σ | `length_scale`, `alpha` |
| 13 | `"rf"` | `"random_forest"` | Random Forest regressor | `n_estimators`, `max_depth` |
| 14 | `"gbm"` | `"gradient_boosting"` | Gradient Boosting regressor | `n_estimators`, `learning_rate` |
| 15 | `"rk"` | `"regression_kriging"` | ML trend + Kriging of residuals | `ml_method` |

---

## Method notes

### IDW

Simple, fast, and exact at data points. Higher `power` (default 2) makes the surface more local — distant stations contribute less.

```python
method_params={"idw": {"power": 3}}
```

### Kriging (Ordinary and Universal)

Geostatistical — accounts for spatial autocorrelation via a variogram model. Returns optimal unbiased linear estimates. Universal Kriging (`"uk"`) first removes a polynomial trend and kriges the residuals.

```python
method_params={"kriging": {"variogram_model": "spherical", "nlags": 8}}
```

Available variogram models: `"linear"` · `"power"` · `"gaussian"` · `"spherical"` · `"exponential"` · `"hole-effect"`

### Natural Neighbor

Uses Voronoi tessellation. The weight for station *i* equals the area that Voronoi cell *i* loses when the query point is inserted. Smooth, local, and exact at data locations. Falls back to IDW for points outside the station convex hull.

### Spline

Fits a minimum-curvature surface (regularized) or a tension spline. Exact at data points when `smoothing=0`. Good for smooth fields like temperature or elevation.

```python
method_params={"spline": {"smoothing": 0.1}}
method_params={"spline_tension": {"smoothing": 0.5}}
```

### Trend

Fits a global polynomial of degree `order` (default 1 = linear). Captures large-scale spatial patterns but not local variation.

```python
method_params={"trend": {"order": 2}}
```

### RBF

Radial Basis Functions with 8 kernel choices. Exact at data points when `smoothing=0`.

```python
method_params={"rbf": {"kernel": "thin_plate_spline"}}
```

Available kernels: `"thin_plate_spline"` · `"multiquadric"` · `"inverse_multiquadric"` · `"inverse_quadratic"` · `"gaussian"` · `"linear"` · `"cubic"` · `"quintic"`

### Gaussian Process

Probabilistic model — returns both a mean surface and a per-pixel uncertainty (standard deviation). Automatically reprojects to UTM so the length-scale is in metres.

```python
from geointerpo.interpolators import MLInterpolator

gp = MLInterpolator(method="gp").fit(gdf)
mean_da, std_da = gp.predict_with_std(bbox)
```

### Random Forest / Gradient Boosting

Ensemble ML methods that use (x, y) coordinates as features. No smoothness assumptions — useful for discontinuous or patchy fields.

```python
method_params={"rf":  {"n_estimators": 200, "max_depth": 8}}
method_params={"gbm": {"n_estimators": 200, "learning_rate": 0.05}}
```

### Regression Kriging

Combines ML trend estimation with Kriging of the residuals. Best of both worlds for fields with both large-scale trends and local spatial structure. Requires `[kriging]` extra.

---

## Direct interpolator usage

```python
from geointerpo.interpolators import (
    IDWInterpolator,
    KrigingInterpolator,
    NaturalNeighborInterpolator,
    SplineInterpolator,
    TrendInterpolator,
    RBFInterpolator,
    GridDataInterpolator,
    MLInterpolator,
    RegressionKrigingInterpolator,
)

model = KrigingInterpolator(variogram_model="spherical")
model.fit(gdf)                                    # GeoDataFrame with Point geometry + 'value' column
grid  = model.predict(bbox, resolution=0.25)      # xr.DataArray (WGS-84)
cv    = model.cross_validate(gdf, k=5)            # blocked spatial k-fold CV
```

→ Full parameter reference in [API: Interpolators](api/interpolators.md)
