"""Interactive visualization for geointerpo.

Requires either plotly or leafmap (optional extras):
    pip install plotly                   # lightweight, works in any Jupyter kernel
    pip install "geointerpo[notebooks]"  # includes leafmap + full notebook stack
"""

from __future__ import annotations

from typing import Optional, Sequence
import numpy as np
import xarray as xr
import geopandas as gpd


def plot_interactive(
    da: xr.DataArray,
    stations: Optional[gpd.GeoDataFrame] = None,
    boundary: Optional[gpd.GeoDataFrame] = None,
    backend: str = "auto",
    title: str = "",
    cmap: str = "RdYlBu_r",
    opacity: float = 0.85,
    **kwargs,
):
    """Interactive map of an interpolated DataArray.

    Parameters
    ----------
    da:       xr.DataArray (lat/lon coords, WGS-84)
    stations: optional GeoDataFrame of station points
    boundary: optional GeoDataFrame of study-area boundary
    backend:  'plotly' | 'leafmap' | 'auto' (tries plotly then leafmap)
    title:    map title
    cmap:     matplotlib colormap name
    opacity:  raster layer opacity (0–1)

    Returns
    -------
    A plotly Figure or leafmap Map, ready for display in a notebook.
    Call `.show()` outside notebooks.
    """
    if backend == "auto":
        backend = _detect_backend()

    if backend == "plotly":
        return _plotly_map(da, stations, boundary, title, cmap, opacity, **kwargs)
    if backend == "leafmap":
        return _leafmap_map(da, stations, boundary, title, cmap, opacity, **kwargs)
    raise ValueError(f"Unknown backend '{backend}'. Choose 'plotly' or 'leafmap'.")


def plot_interactive_comparison(
    arrays: Sequence[xr.DataArray],
    labels: Sequence[str],
    stations: Optional[gpd.GeoDataFrame] = None,
    backend: str = "auto",
    cmap: str = "RdYlBu_r",
    **kwargs,
):
    """Side-by-side interactive comparison of multiple interpolated grids.

    Returns a list of interactive figures (one per method).
    Use in a notebook — they render inline automatically.
    """
    return [
        plot_interactive(da, stations=stations, backend=backend,
                         title=label, cmap=cmap, **kwargs)
        for da, label in zip(arrays, labels)
    ]


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

def _detect_backend() -> str:
    try:
        import plotly  # noqa: F401
        return "plotly"
    except ImportError:
        pass
    try:
        import leafmap  # noqa: F401
        return "leafmap"
    except ImportError:
        pass
    raise ImportError(
        "No interactive backend found. Install one:\n"
        "  pip install plotly          # recommended\n"
        "  pip install 'geointerpo[notebooks]'  # includes leafmap"
    )


def _plotly_map(da, stations, boundary, title, cmap, opacity, **kwargs):
    import plotly.graph_objects as go
    import plotly.express as px

    vals = da.values.astype(float)
    lats = da.lat.values
    lons = da.lon.values

    vmin = float(np.nanpercentile(vals, 2))
    vmax = float(np.nanpercentile(vals, 98))

    # Map matplotlib cmap name → plotly colorscale
    colorscale = _mpl_to_plotly_colorscale(cmap, n=20)

    fig = go.Figure()

    # Heatmap layer (raster approximation via density_mapbox or heatmap)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    valid_mask = ~np.isnan(vals)

    fig.add_trace(go.Densitymap(
        lat=lat_grid[valid_mask].ravel(),
        lon=lon_grid[valid_mask].ravel(),
        z=vals[valid_mask].ravel(),
        radius=20,
        colorscale=colorscale,
        zmin=vmin,
        zmax=vmax,
        opacity=opacity,
        colorbar={"title": da.name or "value"},
        hovertemplate="lon: %{lon:.3f}<br>lat: %{lat:.3f}<br>value: %{z:.2f}<extra></extra>",
        name=title or da.name or "interpolated",
    ))

    # Station scatter
    if stations is not None and len(stations) > 0:
        sv = stations["value"].values if "value" in stations.columns else None
        fig.add_trace(go.Scattermap(
            lat=stations.geometry.y.values,
            lon=stations.geometry.x.values,
            mode="markers",
            marker=dict(
                size=8,
                color=sv,
                colorscale=colorscale,
                cmin=vmin,
                cmax=vmax,
            ),
            hovertemplate=(
                "lon: %{lon:.3f}<br>lat: %{lat:.3f}<br>"
                + ("value: %{marker.color:.2f}" if sv is not None else "")
                + "<extra>stations</extra>"
            ),
            name="stations",
        ))

    center_lat = float(lats.mean())
    center_lon = float(lons.mean())

    fig.update_layout(
        title=title or (da.name or "Interpolated surface"),
        map=dict(
            style="carto-positron",
            center={"lat": center_lat, "lon": center_lon},
            zoom=_auto_zoom(lats, lons),
        ),
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=600,
    )
    return fig


def _leafmap_map(da, stations, boundary, title, cmap, opacity, **kwargs):
    """Render using leafmap (writes a temporary GeoTIFF for the raster layer)."""
    import tempfile
    import os

    try:
        import leafmap
    except ImportError as e:
        raise ImportError(
            "leafmap is required for backend='leafmap': "
            "pip install 'geointerpo[notebooks]'"
        ) from e

    m = leafmap.Map(center=[float(da.lat.mean()), float(da.lon.mean())],
                    zoom=_auto_zoom(da.lat.values, da.lon.values))

    # Write raster to temp GeoTIFF so leafmap can display it
    try:
        from geointerpo.io import export_geotiff
        tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
        tmp.close()
        export_geotiff(da, tmp.name)
        m.add_raster(tmp.name, layer_name=title or da.name or "interpolated",
                     colormap=cmap, opacity=opacity)
    except Exception:
        pass  # If rasterio not installed, skip raster layer

    if stations is not None and len(stations) > 0:
        try:
            m.add_gdf(stations, layer_name="stations", zoom_to_layer=False)
        except Exception:
            pass

    if boundary is not None:
        try:
            m.add_gdf(boundary, layer_name="boundary", style={"color": "white", "fillOpacity": 0},
                      zoom_to_layer=False)
        except Exception:
            pass

    if title:
        m.add_text(title, position="topright")

    return m


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _mpl_to_plotly_colorscale(cmap_name: str, n: int = 20) -> list:
    """Convert a matplotlib colormap to a plotly colorscale list."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        cmap = plt.get_cmap(cmap_name)
        return [
            [i / (n - 1), mcolors.to_hex(cmap(i / (n - 1)))]
            for i in range(n)
        ]
    except Exception:
        return "RdYlBu_r"  # plotly built-in fallback


def _auto_zoom(lats: np.ndarray, lons: np.ndarray) -> int:
    """Estimate a reasonable zoom level from the spatial extent."""
    lat_span = float(np.nanmax(lats) - np.nanmin(lats))
    lon_span = float(np.nanmax(lons) - np.nanmin(lons))
    span = max(lat_span, lon_span)
    for zoom, threshold in [(11, 0.2), (10, 0.5), (9, 1), (8, 2),
                             (7, 4), (6, 8), (5, 16), (4, 32), (3, 64)]:
        if span < threshold:
            return zoom
    return 2
