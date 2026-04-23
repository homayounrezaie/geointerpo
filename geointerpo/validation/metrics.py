from __future__ import annotations

import copy
import warnings
import numpy as np
import xarray as xr
import geopandas as gpd


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
    """Compute metrics between two spatially aligned DataArrays."""
    pred_aligned = predicted.interp(lat=reference.lat, lon=reference.lon, method="linear")
    obs_vals = reference.values.ravel()
    pred_vals = pred_aligned.values.ravel()
    metrics = compute_metrics(obs_vals, pred_vals)
    diff = pred_aligned - reference
    metrics["diff_map"] = diff
    return metrics


def spatial_cv(
    interpolator,
    gdf: gpd.GeoDataFrame,
    strategy: str = "block",
    k: int = 5,
    buffer_km: float | None = None,
) -> dict:
    """Spatial cross-validation with configurable strategy.

    Parameters
    ----------
    interpolator:  any fitted or unfitted BaseInterpolator instance.
    gdf:           GeoDataFrame with Point geometry and a value column.
    strategy:      'block'  — blocked k-fold (spatially sorted, avoids autocorrelation).
                   'loo'    — leave-one-out with optional buffer exclusion.
                              Pairs well with buffer_km to remove autocorrelated
                              neighbours around each test point.
    k:             Number of folds for strategy='block' (ignored for 'loo').
    buffer_km:     For strategy='loo': exclude neighbours within this many km
                   of the test point from the training set.  Addresses spatial
                   autocorrelation leakage.  None = standard LOO (no buffer).

    Returns
    -------
    dict with 'rmse', 'mae', 'bias', 'r', 'n' and 'per_fold' list.
    """
    gdf = gdf.to_crs("EPSG:4326").reset_index(drop=True)
    lons = gdf.geometry.x.to_numpy()
    lats = gdf.geometry.y.to_numpy()
    values = gdf[interpolator.value_col].to_numpy(dtype=float)
    n = len(gdf)

    preds = np.full(n, np.nan, dtype=float)
    per_fold = []

    if strategy == "block":
        order = np.lexsort((lons, lats))
        folds = np.array_split(order, k)

        for fold_test in folds:
            train_idx = np.setdiff1d(np.arange(n), fold_test)
            if len(train_idx) < 2:
                continue
            clone = copy.deepcopy(interpolator)
            clone.fit(gdf.iloc[train_idx].copy())
            fold_gdf = gdf.iloc[fold_test].copy()
            _predict_fold(clone, fold_gdf, preds, fold_test)
            fold_m = compute_metrics(values[fold_test], preds[fold_test])
            per_fold.append(fold_m)

    elif strategy == "loo":
        from pyproj import Transformer

        # Project to a metre-based CRS for distance filtering
        from geointerpo.interpolators.base import _utm_crs_for_bbox
        proj_crs = _utm_crs_for_bbox(lons.min(), lats.min(), lons.max(), lats.max())
        t = Transformer.from_crs("EPSG:4326", proj_crs, always_xy=True)
        xs, ys = t.transform(lons, lats)
        buffer_m = (buffer_km or 0.0) * 1_000

        for i in range(n):
            if buffer_m > 0:
                dists = np.sqrt((xs - xs[i]) ** 2 + (ys - ys[i]) ** 2)
                train_idx = np.where((np.arange(n) != i) & (dists >= buffer_m))[0]
            else:
                train_idx = np.delete(np.arange(n), i)

            if len(train_idx) < 2:
                continue
            clone = copy.deepcopy(interpolator)
            clone.fit(gdf.iloc[train_idx].copy())
            _predict_fold(clone, gdf.iloc[[i]].copy(), preds, np.array([i]))
            fold_m = compute_metrics(values[[i]], preds[[i]])
            per_fold.append(fold_m)

    else:
        raise ValueError(f"Unknown strategy '{strategy}'. Choose 'block' or 'loo'.")

    mask = ~np.isnan(preds)
    result = compute_metrics(values[mask], preds[mask])
    result["per_fold"] = per_fold
    return result


def _predict_fold(clone, fold_gdf, preds, fold_test_idx):
    """Run prediction for one CV fold and write results into preds array."""
    fold_lons = fold_gdf.geometry.x.to_numpy()
    fold_lats = fold_gdf.geometry.y.to_numpy()

    if clone._needs_metric and clone._proj_crs is not None:
        xs, ys = clone._project(fold_lons, fold_lats)
    else:
        xs, ys = fold_lons, fold_lats

    fold_preds = clone._predict_points(xs, ys, fold_lons, fold_lats)
    preds[fold_test_idx] = fold_preds
