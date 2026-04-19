# Interpolators API

All interpolators share the same interface through `BaseInterpolator`. You can use them directly or through `Pipeline`.

## Common interface

```python
model.fit(gdf)                         # GeoDataFrame with geometry + 'value' column
grid = model.predict(bbox, resolution) # returns xarray.DataArray (WGS-84)
metrics = model.cross_validate(gdf, k) # returns dict: rmse, mae, bias, r, n
```

---

## IDWInterpolator

Inverse Distance Weighting — fast, assumption-free, good as a baseline.

```python
from geointerpo.interpolators import IDWInterpolator

model = IDWInterpolator(power=2.0)
model.fit(gdf)
grid = model.predict(bbox=(-114.5, 50.8, -113.8, 51.3), resolution=0.25)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `power` | float | `2.0` | Distance decay exponent — higher values make the surface more local |
| `value_col` | str | `"value"` | Column name to read from the GeoDataFrame |

---

## RBFInterpolator

Radial Basis Functions — smooth surfaces with eight kernel choices.

```python
from geointerpo.interpolators import RBFInterpolator

model = RBFInterpolator(kernel="thin_plate_spline", smoothing=0.0)
model.fit(gdf)
grid = model.predict(bbox, resolution=0.25)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `kernel` | str | `"thin_plate_spline"` | RBF kernel — see list below |
| `smoothing` | float | `0.0` | Regularisation — `0` fits exactly through every point |
| `value_col` | str | `"value"` | Column name in GeoDataFrame |

**Available kernels:** `linear` · `thin_plate_spline` · `cubic` · `quintic` · `multiquadric` · `inverse_multiquadric` · `inverse_quadratic` · `gaussian`

---

## KrigingInterpolator

Ordinary and Universal Kriging — statistically optimal, unbiased estimates via variogram modelling.

!!! note "Requires kriging extra"
    ```bash
    pip install "geointerpo[kriging]"
    ```

```python
from geointerpo.interpolators import KrigingInterpolator

model = KrigingInterpolator(mode="ordinary", variogram_model="spherical")
model.fit(gdf)
grid = model.predict(bbox, resolution=0.25)
print(model.variogram_parameters)   # fitted nugget, sill, range
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `mode` | str | `"ordinary"` | `"ordinary"` or `"universal"` |
| `variogram_model` | str | `"spherical"` | Variogram model type — see list below |
| `nlags` | int | `6` | Number of variogram lags |
| `weight` | bool | `False` | Weight the variogram by pair count |

**Available variogram models:** `linear` · `power` · `gaussian` · `spherical` · `exponential` · `hole-effect`

**Extra property:** `model.variogram_parameters` — fitted nugget, sill, and range after calling `.fit()`.

---

## MLInterpolator

Gaussian Process, Random Forest, and Gradient Boosting — capture non-linear spatial patterns without variogram assumptions.

!!! note "Requires kriging extra"
    ```bash
    pip install "geointerpo[kriging]"
    ```

```python
from geointerpo.interpolators import MLInterpolator

# Mean prediction
model = MLInterpolator(method="rf")
model.fit(gdf)
grid = model.predict(bbox, resolution=0.25)

# GP also returns a per-pixel uncertainty surface
model = MLInterpolator(method="gp")
model.fit(gdf)
mean_da, std_da = model.predict_with_std(bbox)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | str | `"gp"` | `"gp"`, `"rf"`, `"gbm"`, or `"rk"` |
| `covariates_fn` | callable | `None` | `fn(lons, lats) -> np.ndarray` — add extra features (e.g. elevation) |

!!! tip
    `predict_with_std()` is only available for `method="gp"`. For all other methods, use `predict()`.
