# Validation API

## compute_metrics

```python
from geointerpo.validation import compute_metrics

metrics = compute_metrics(observed, predicted)
# {'rmse': 1.23, 'mae': 0.98, 'bias': 0.12, 'r': 0.94, 'n': 47}
```

Works on 1-D arrays; NaN values are automatically masked.

## grid_metrics

```python
from geointerpo.validation import grid_metrics

metrics = grid_metrics(reference_da, predicted_da)
# includes 'diff_map': xr.DataArray of pixel-wise differences
```

Reprojects `predicted_da` onto `reference_da` grid via bilinear interpolation before comparison.

## spatial_cv

```python
from geointerpo.validation import spatial_cv
from geointerpo.interpolators import IDWInterpolator

model = IDWInterpolator(power=2)
metrics = spatial_cv(model, gdf, strategy="block", k=5)
# or:
metrics = spatial_cv(model, gdf, strategy="loo", buffer_km=50)
```

| Parameter | Meaning |
|---|---|
| `strategy="block"` | Blocked spatial k-fold CV |
| `strategy="loo"` | Leave-one-out CV |
| `buffer_km` | Exclude nearby training points in LOO to reduce leakage |

Returns the standard metric keys plus a `per_fold` list.
