# Methods

**15 algorithms · 24 method keys.**  
Every method shares `.fit(gdf)` → `.predict(bbox, resolution)` → `xr.DataArray`.  
Swap `method=` to compare — everything else stays the same.

---

## Distance-based

Fast and assumption-free. Good as a baseline or when data is dense and evenly distributed.

<div class="method-row" markdown>
  <figure><img src="assets/methods/idw.png" width="220"/><figcaption>IDW</figcaption></figure>
  <figure><img src="assets/methods/nearest.png" width="220"/><figcaption>Nearest Neighbor</figcaption></figure>
  <figure><img src="assets/methods/linear.png" width="220"/><figcaption>Linear (Delaunay)</figcaption></figure>
  <figure><img src="assets/methods/cubic.png" width="220"/><figcaption>Cubic (Clough-Tocher)</figcaption></figure>
</div>

| Key | Description | Key params |
|---|---|---|
| `idw` | Inverse Distance Weighting | `power` (default 2) |
| `nearest` | Nearest-neighbour via scipy griddata | — |
| `linear` | Delaunay triangulation, linear barycentric | — |
| `cubic` | Clough-Tocher C¹ cubic | — |

!!! tip
    Higher `power` in IDW makes the surface more local — distant stations contribute less.

---

## Spline & Trend

Fit smooth continuous surfaces. Splines minimise curvature; RBF offers 8 kernel choices; Trend fits a global polynomial for large-scale patterns.

<div class="method-row" markdown>
  <figure><img src="assets/methods/spline.png" width="220"/><figcaption>Spline (Regularized)</figcaption></figure>
  <figure><img src="assets/methods/spline_tension.png" width="220"/><figcaption>Spline Tension</figcaption></figure>
  <figure><img src="assets/methods/rbf.png" width="220"/><figcaption>RBF</figcaption></figure>
  <figure><img src="assets/methods/trend.png" width="220"/><figcaption>Trend Surface</figcaption></figure>
</div>

| Key | Description | Key params |
|---|---|---|
| `spline` | Minimum curvature regularized spline | `smoothing` |
| `spline_tension` | Tension spline — flatter between points | `smoothing` |
| `rbf` | Radial Basis Functions | `kernel`, `smoothing` |
| `trend` | Global polynomial trend surface | `order` (1–12) |

**RBF kernels:** `thin_plate_spline` · `multiquadric` · `inverse_multiquadric` · `inverse_quadratic` · `gaussian` · `linear` · `cubic` · `quintic`

---

## Geostatistical

Account for spatial autocorrelation via a variogram model. Produce statistically optimal, unbiased estimates. Natural Neighbor uses Voronoi area-stealing weights — smooth and exact at data locations.

<div class="method-row" markdown>
  <figure><img src="assets/methods/kriging.png" width="290"/><figcaption>Ordinary Kriging</figcaption></figure>
  <figure><img src="assets/methods/uk.png" width="290"/><figcaption>Universal Kriging</figcaption></figure>
  <figure><img src="assets/methods/natural_neighbor.png" width="290"/><figcaption>Natural Neighbor</figcaption></figure>
</div>

| Key | Aliases | Description | Key params |
|---|---|---|---|
| `kriging` | `ok`, `ordinary_kriging` | Ordinary Kriging | `variogram_model`, `nlags` |
| `uk` | `universal_kriging` | Universal Kriging — detrended residuals | `variogram_model` |
| `natural_neighbor` | `nn` | Voronoi/Sibson area-stealing weights | — |

**Variogram models:** `linear` · `power` · `gaussian` · `spherical` · `exponential` · `hole-effect`

!!! note "Requires kriging extra"
    ```bash
    pip install "geointerpo[kriging]"
    ```

---

## Machine Learning

Capture non-linear spatial patterns without variogram assumptions. GP also returns a per-pixel uncertainty surface alongside the mean prediction. Regression Kriging combines an ML trend with Kriging of the residuals.

<div class="method-row" markdown>
  <figure><img src="assets/methods/gp.png" width="220"/><figcaption>Gaussian Process</figcaption></figure>
  <figure><img src="assets/methods/rf.png" width="220"/><figcaption>Random Forest</figcaption></figure>
  <figure><img src="assets/methods/gbm.png" width="220"/><figcaption>Gradient Boosting</figcaption></figure>
  <figure><img src="assets/methods/rk.png" width="220"/><figcaption>Regression Kriging</figcaption></figure>
</div>

| Key | Aliases | Description | Key params |
|---|---|---|---|
| `gp` | `gaussian_process` | Gaussian Process — mean + σ output | `length_scale`, `alpha` |
| `rf` | `random_forest` | Random Forest regressor | `n_estimators`, `max_depth` |
| `gbm` | `gradient_boosting` | Gradient Boosting regressor | `n_estimators`, `learning_rate` |
| `rk` | `regression_kriging` | ML trend + Kriging of residuals | `ml_method` |

```python
# GP — also returns uncertainty grid
from geointerpo.interpolators import MLInterpolator
mean_da, std_da = MLInterpolator(method="gp").fit(gdf).predict_with_std(bbox)
```

---

## Direct usage

```python
from geointerpo.interpolators import KrigingInterpolator

model = KrigingInterpolator(variogram_model="spherical")
model.fit(gdf)                              # GeoDataFrame with Point geometry + 'value'
grid  = model.predict(bbox, resolution=0.25)  # xr.DataArray (WGS-84)
cv    = model.cross_validate(gdf, k=5)        # blocked spatial k-fold CV
```

→ Full parameter reference in [API: Interpolators](api/interpolators.md)
