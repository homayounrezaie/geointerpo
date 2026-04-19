"""Static visualization helpers for geointerpo.

All functions here require only matplotlib (pip install 'geointerpo[viz]').
Interactive mapping (leafmap, geemap) is intentionally kept out of this
module — see notebooks/examples for interactive workflows.
"""

from typing import Optional, Sequence
import math
import numpy as np
import numpy.ma as ma
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.figure import Figure


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _geo_aspect(lat_min: float, lat_max: float) -> float:
    """Correct lon:lat display ratio so distances look proportional."""
    mid = math.radians((lat_min + lat_max) / 2)
    return 1.0 / max(math.cos(mid), 0.1)


def _grid_extent(da: xr.DataArray, pad: float = 0.04):
    """Return (lon_min, lon_max, lat_min, lat_max) with small fractional padding."""
    lon_min, lon_max = float(da.lon.min()), float(da.lon.max())
    lat_min, lat_max = float(da.lat.min()), float(da.lat.max())
    dlon = max((lon_max - lon_min) * pad, 0.01)
    dlat = max((lat_max - lat_min) * pad, 0.01)
    return lon_min - dlon, lon_max + dlon, lat_min - dlat, lat_max + dlat


def _add_gridlines(ax, x0, x1, y0, y1):
    """Add light geographic grid lines with degree labels."""
    # Pick sensible tick spacing based on extent
    dlon = x1 - x0
    dlat = y1 - y0
    for span, steps in [(0.5, 0.1), (1, 0.2), (2, 0.5), (5, 1), (10, 2),
                        (20, 5), (40, 10), (80, 20), (160, 30)]:
        if dlon <= span:
            lon_step = steps
            break
    else:
        lon_step = 45
    for span, steps in [(0.5, 0.1), (1, 0.2), (2, 0.5), (5, 1), (10, 2),
                        (20, 5), (40, 10), (80, 20)]:
        if dlat <= span:
            lat_step = steps
            break
    else:
        lat_step = 30

    ax.set_xticks(np.arange(math.ceil(x0 / lon_step) * lon_step,
                             math.floor(x1 / lon_step) * lon_step + lon_step, lon_step))
    ax.set_yticks(np.arange(math.ceil(y0 / lat_step) * lat_step,
                             math.floor(y1 / lat_step) * lat_step + lat_step, lat_step))

    def _fmt_lon(v, _):
        if v == 0:
            return "0°"
        return f"{abs(v):.4g}°{'E' if v > 0 else 'W'}"

    def _fmt_lat(v, _):
        if v == 0:
            return "0°"
        return f"{abs(v):.4g}°{'N' if v > 0 else 'S'}"

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_lon))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_lat))
    ax.grid(color="white", linewidth=0.5, linestyle="--", alpha=0.7, zorder=1)
    ax.tick_params(labelsize=8, length=3)


# ---------------------------------------------------------------------------
# Public plotting functions
# ---------------------------------------------------------------------------

def plot_interpolated(
    da: xr.DataArray,
    stations: Optional[gpd.GeoDataFrame] = None,
    boundary: Optional[gpd.GeoDataFrame] = None,
    title: str = "",
    cmap: str = "RdYlBu_r",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    figsize: tuple = (7, 5),
    ax: Optional[plt.Axes] = None,
    n_contours: int = 128,
) -> Figure:
    """Plot an interpolated DataArray as a smooth filled-contour map."""
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    else:
        fig = ax.get_figure()

    vals = ma.masked_invalid(da.values)
    valid = vals.compressed()
    if valid.size == 0:
        ax.set_title(title or "No data")
        return fig

    vmin = vmin if vmin is not None else float(np.nanpercentile(valid, 2))
    vmax = vmax if vmax is not None else float(np.nanpercentile(valid, 98))

    # Light background so masked (NaN) areas show as a neutral colour
    ax.set_facecolor("#d8d8d8")

    levels = np.linspace(vmin, vmax, n_contours + 1)
    cf = ax.contourf(
        da.lon.values, da.lat.values, vals,
        levels=levels, cmap=cmap, extend="both", zorder=2,
    )
    # Thin contour lines for definition (every 8th level)
    ax.contour(
        da.lon.values, da.lat.values, vals,
        levels=levels[::8], colors="k", linewidths=0.15, alpha=0.25, zorder=3,
    )

    fig.colorbar(cf, ax=ax, label=da.name or "value",
                 fraction=0.035, pad=0.02, shrink=0.85)

    # Boundary outline
    if boundary is not None:
        try:
            boundary.boundary.plot(ax=ax, color="white", linewidth=1.2, zorder=5)
        except Exception:
            pass

    # Station dots (small, subtle)
    if stations is not None:
        ax.scatter(
            stations.geometry.x, stations.geometry.y,
            c=stations["value"], cmap=cmap, vmin=vmin, vmax=vmax,
            edgecolors="white", linewidths=0.6, s=30, zorder=6,
        )

    x0, x1, y0, y1 = _grid_extent(da)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(_geo_aspect(y0, y1))

    _add_gridlines(ax, x0, x1, y0, y1)
    ax.set_xlabel("Longitude", fontsize=9)
    ax.set_ylabel("Latitude", fontsize=9)
    ax.set_title(title or (da.name or "Interpolated surface"), fontsize=10, pad=6)
    return fig


def plot_comparison(
    arrays: Sequence[xr.DataArray],
    labels: Sequence[str],
    stations: Optional[gpd.GeoDataFrame] = None,
    boundary: Optional[gpd.GeoDataFrame] = None,
    cmap: str = "RdYlBu_r",
    figsize: tuple = None,
    n_contours: int = 128,
) -> Figure:
    """Side-by-side smooth comparison of multiple interpolated grids."""
    n = len(arrays)
    figsize = figsize or (5.5 * n, 4.5)
    fig, axes = plt.subplots(1, n, figsize=figsize, constrained_layout=True)
    if n == 1:
        axes = [axes]

    valid_all = np.concatenate([
        ma.masked_invalid(a.values).compressed() for a in arrays
    ])
    vmin = float(np.nanpercentile(valid_all, 2))
    vmax = float(np.nanpercentile(valid_all, 98))

    for ax, da, label in zip(axes, arrays, labels):
        plot_interpolated(da, stations=stations, boundary=boundary,
                          title=label, cmap=cmap,
                          vmin=vmin, vmax=vmax, ax=ax, n_contours=n_contours)
    return fig


def plot_diff(
    reference: xr.DataArray,
    predicted: xr.DataArray,
    title: str = "Predicted − Reference",
    figsize: tuple = (7, 5),
    n_contours: int = 64,
) -> Figure:
    """Smooth diverging plot of pixel-wise difference between predicted and reference."""
    pred_r = predicted.interp(lat=reference.lat, lon=reference.lon, method="linear")
    diff = pred_r - reference

    valid = ma.masked_invalid(diff.values).compressed()
    vabs = float(np.nanpercentile(np.abs(valid), 98))
    levels = np.linspace(-vabs, vabs, n_contours + 1)

    fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    ax.set_facecolor("#d8d8d8")
    cf = ax.contourf(
        diff.lon.values, diff.lat.values, ma.masked_invalid(diff.values),
        levels=levels, cmap="RdBu_r", extend="both", zorder=2,
    )
    fig.colorbar(cf, ax=ax, label="Δ value", fraction=0.035, pad=0.02, shrink=0.85)

    x0, x1, y0, y1 = _grid_extent(diff)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(_geo_aspect(y0, y1))
    _add_gridlines(ax, x0, x1, y0, y1)

    ax.set_xlabel("Longitude", fontsize=9)
    ax.set_ylabel("Latitude", fontsize=9)
    ax.set_title(title, fontsize=10, pad=6)
    return fig


def plot_variogram(kriging_interpolator, title: str = "Experimental Variogram") -> Figure:
    """Plot experimental variogram from a fitted KrigingInterpolator."""
    model = kriging_interpolator._model
    if model is None:
        raise RuntimeError("KrigingInterpolator must be fitted first")

    lags = model.lags
    semivariance = model.semivariance
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    ax.scatter(lags, semivariance, color="steelblue", zorder=3, label="Experimental")

    lag_fine = np.linspace(0, lags.max(), 300)
    fitted = model.variogram_function(model.variogram_model_parameters, lag_fine)
    ax.plot(lag_fine, fitted, "r-", label=f"Fitted ({model.variogram_model})")
    ax.set_xlabel("Lag distance")
    ax.set_ylabel("Semivariance")
    ax.set_title(title)
    ax.legend()
    return fig


def plot_cv_scatter(observed: np.ndarray, predicted: np.ndarray, label: str = "") -> Figure:
    """1:1 scatter plot for cross-validation results."""
    obs = np.asarray(observed)
    pred = np.asarray(predicted)
    fig, ax = plt.subplots(figsize=(5, 5), layout="constrained")
    ax.scatter(obs, pred, alpha=0.6, edgecolors="k", linewidths=0.3, label=label)
    lims = [min(obs.min(), pred.min()), max(obs.max(), pred.max())]
    ax.plot(lims, lims, "r--", lw=1.5, label="1:1")
    ax.set_xlabel("Observed")
    ax.set_ylabel("Predicted")
    ax.set_title("Cross-validation: Observed vs Predicted")
    ax.legend()
    ax.set_aspect("equal")
    return fig
