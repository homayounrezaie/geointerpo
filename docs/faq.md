# FAQ & Troubleshooting

## Installation

??? failure "ModuleNotFoundError: No module named 'pykrige'"
    Kriging and ML methods require the `kriging` extra:
    ```bash
    pip install "geointerpo[kriging]"
    ```

??? failure "ModuleNotFoundError: No module named 'rioxarray'"
    GeoTIFF export and boundary clipping require the `raster` extra:
    ```bash
    pip install "geointerpo[raster]"
    ```

??? failure "ModuleNotFoundError: No module named 'matplotlib'"
    Plotting requires the `viz` extra:
    ```bash
    pip install "geointerpo[viz]"
    ```

??? failure "ModuleNotFoundError: No module named 'plotly'"
    Interactive maps require the `interactive` extra:
    ```bash
    pip install "geointerpo[interactive]"
    # or just: pip install plotly
    ```

??? failure "ModuleNotFoundError: No module named 'gstools'"
    Cokriging and Sequential Gaussian Simulation require the `geostat` extra:
    ```bash
    pip install "geointerpo[geostat]"
    ```

??? failure "ModuleNotFoundError: No module named 'mapie'"
    Conformal prediction intervals for GBM require the `uncertainty` extra:
    ```bash
    pip install "geointerpo[uncertainty]"
    ```
    RF bootstrap intervals are built-in and need no extra install.

??? failure "ModuleNotFoundError: No module named 'cdsapi'"
    ERA5 reanalysis requires the `era5` extra plus a free CDS API account:
    ```bash
    pip install "geointerpo[era5]"
    ```
    Then create `~/.cdsapirc` following the [CDS API setup guide](https://cds.climate.copernicus.eu/api-how-to).

---

## Boundaries

??? warning "ValueError: Could not geocode location 'X'"
    Nominatim couldn't find the place name. Try:

    - A more specific name: `"Calgary, Alberta, Canada"` instead of `"Calgary"`
    - A bbox tuple: `boundary=(-114.5, 50.8, -113.8, 51.3)`
    - A file: `boundary="my_region.geojson"`

??? warning "Boundary clips everything to NaN"
    The boundary polygon may not overlap your station data. Check:

    1. `boundary_bbox(boundary)` returns a bbox that covers your data
    2. `rioxarray` is installed: `pip install "geointerpo[raster]"`
    3. Try `clip_to_boundary=False` to isolate the issue

---

## Data sources

??? failure "No stations returned from Meteostat"
    Meteostat may have no stations for that bbox/date. Try:

    - A wider bbox (increase `padding_deg`)
    - A different date (some stations have gaps)
    - `data="sample"` to confirm the pipeline works offline

??? failure "ImportError: No module named 'meteostat'"
    ```bash
    pip install "geointerpo[data]"
    ```

---

## Interpolation

??? warning "ValueError: Not enough points for spline"
    Spline requires at least 16 points. Either add more stations or use `method="rbf"` or `method="idw"`.

??? warning "kriging returns all NaN"
    Check that `pykrige` is installed and try `variogram_model="linear"` as a safe fallback.

??? info "natural_neighbor output looks like IDW"
    With very sparse data most grid points fall outside the station convex hull, so the IDW fallback activates. This is correct behaviour — the Voronoi weights are only applied to interior points.

---

## Plotting

??? failure "RuntimeError: Colorbar layout not compatible with tight_layout"
    Use `layout="constrained"` in your figure:
    ```python
    fig, ax = plt.subplots(layout="constrained")
    ```

??? failure "Interactive map doesn't display in Jupyter"
    ```bash
    pip install "geointerpo[notebooks]"
    ```

---

## Performance

!!! tip "Speed up large grids"
    - Increase `resolution` (0.5° instead of 0.1°) for a quick first pass
    - `natural_neighbor` is O(n_stations × n_grid) — use `idw` or `rbf` for large grids
    - GP scales as O(n³) — prefer `rf` or `gbm` for more than ~500 stations
