import numpy as np
import xarray as xr
from typing import Union


def compute_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict:
    """Compute RMSE, MAE, bias, and Pearson r between two 1-D arrays."""
    obs = np.asarray(observed, dtype=float)
    pred = np.asarray(predicted, dtype=float)
    mask = ~(np.isnan(obs) | np.isnan(pred))
    obs, pred = obs[mask], pred[mask]
    if len(obs) == 0:
        return {"rmse": np.nan, "mae": np.nan, "bias": np.nan, "r": np.nan, "n": 0}
    diff = pred - obs
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))
    bias = float(np.mean(diff))
    r = float(np.corrcoef(obs, pred)[0, 1]) if len(obs) > 1 else np.nan
    return {"rmse": rmse, "mae": mae, "bias": bias, "r": r, "n": int(len(obs))}


def grid_metrics(reference: xr.DataArray, predicted: xr.DataArray) -> dict:
    """Compute metrics between two spatially aligned DataArrays.

    reference and predicted are aligned/resampled before comparison.
    """
    pred_aligned = predicted.interp(lat=reference.lat, lon=reference.lon, method="linear")
    obs_vals = reference.values.ravel()
    pred_vals = pred_aligned.values.ravel()
    metrics = compute_metrics(obs_vals, pred_vals)

    diff = pred_aligned - reference
    metrics["diff_map"] = diff
    return metrics
