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
from geointerpo.validation.metrics import grid_metrics

metrics = grid_metrics(reference_da, predicted_da)
# includes 'diff_map': xr.DataArray of pixel-wise differences
```

Reprojects `predicted_da` onto `reference_da` grid via bilinear interpolation before comparison.

## GEEValidator

```python
from geointerpo.validation import GEEValidator

validator = GEEValidator(variable="temperature", date="2024-07-15")
reference = validator.fetch_reference(bbox=(5, 44, 25, 56), resolution=0.25)
metrics = validator.compare(interpolated_da, reference)
```

| `variable` | GEE Dataset | Band |
|---|---|---|
| `temperature` | `MODIS/061/MOD11A1` | `LST_Day_1km` (→ °C) |
| `precipitation` | `UCSB-CHG/CHIRPS/DAILY` | `precipitation` |
| `pm25` | `COPERNICUS/S5P/NRTI/L3_AER_AI` | `absorbing_aerosol_index` |
| `o3` | `COPERNICUS/S5P/NRTI/L3_O3` | `O3_column_number_density` |
| `no2` | `COPERNICUS/S5P/NRTI/L3_NO2` | `tropospheric_NO2_column_number_density` |

**Setup:** run `earthengine authenticate` once in your terminal.
