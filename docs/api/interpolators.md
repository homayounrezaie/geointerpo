# Interpolators API

All interpolators share the same interface via `BaseInterpolator`.

## Common Interface

```python
model.fit(gdf)                        # GeoDataFrame with geometry + 'value' column
grid = model.predict(bbox, resolution) # returns xarray.DataArray
metrics = model.cross_validate(gdf, k) # returns dict: rmse, mae, bias, r, n
```

## IDWInterpolator

```python
from geointerpo.interpolators import IDWInterpolator

model = IDWInterpolator(power=2.0)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `power` | float | 2.0 | Distance decay exponent |
| `value_col` | str | `"value"` | Column name in GeoDataFrame |

## RBFInterpolator

```python
from geointerpo.interpolators import RBFInterpolator

model = RBFInterpolator(kernel="thin_plate_spline", smoothing=0.0)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `kernel` | str | `"thin_plate_spline"` | RBF kernel type |
| `smoothing` | float | 0.0 | Regularisation (0 = exact) |

Available kernels: `linear`, `thin_plate_spline`, `cubic`, `quintic`, `multiquadric`, `inverse_multiquadric`, `inverse_quadratic`, `gaussian`

## KrigingInterpolator

```python
from geointerpo.interpolators import KrigingInterpolator

model = KrigingInterpolator(mode="ordinary", variogram_model="spherical")
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `mode` | str | `"ordinary"` | `"ordinary"` or `"universal"` |
| `variogram_model` | str | `"spherical"` | Variogram model type |
| `nlags` | int | 6 | Number of variogram lags |
| `weight` | bool | False | Weight variogram by pair count |

Available variogram models: `linear`, `power`, `gaussian`, `spherical`, `exponential`, `hole-effect`

Extra property: `model.variogram_parameters` — fitted nugget, sill, range.

## MLInterpolator

```python
from geointerpo.interpolators import MLInterpolator

model = MLInterpolator(method="gp")
mean_da, std_da = model.predict_with_std(bbox)  # GP only
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | str | `"gp"` | `"gp"`, `"rf"`, or `"gbm"` |
| `covariates_fn` | callable | None | `fn(lons, lats) -> np.ndarray` of extra features |
