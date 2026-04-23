# Install

## Recommended

```bash
pip install "geointerpo[full]"
```

Adds kriging, ML methods, GeoTIFF export, all data APIs, matplotlib, plotly, and uncertainty tools. Covers 95% of use cases.

## Core only

```bash
pip install geointerpo
```

Includes IDW (KD-tree fast), RBF, spline, griddata, boundary loading, and the Pipeline. No kriging, no ML, no APIs.

## Pick your extras

=== "Kriging & ML"
    ```bash
    pip install "geointerpo[kriging]"
    ```
    Unlocks `kriging`, `uk`, `gp`, `rf`, `gbm`, `rk` methods via **pykrige** + **scikit-learn**.

=== "Advanced Geostatistics"
    ```bash
    pip install "geointerpo[geostat]"
    ```
    Unlocks **cokriging** (`ked`) and **Sequential Gaussian Simulation** (`sgs`) via **gstools**.

=== "Uncertainty (ML)"
    ```bash
    pip install "geointerpo[uncertainty]"
    ```
    Conformal prediction intervals for GBM via **MAPIE**. RF bootstrap intervals need no extra install.

=== "Raster I/O"
    ```bash
    pip install "geointerpo[raster]"
    ```
    GeoTIFF export and boundary polygon clipping via **rasterio** + **rioxarray**.

=== "Live Data APIs"
    ```bash
    pip install "geointerpo[data]"
    ```
    `data="meteostat"`, `data="openaq"`, `data="openmeteo"` — no API keys needed.  
    `data="nasapower"` — NASA POWER REST API, no account required.

=== "ERA5 Reanalysis"
    ```bash
    pip install "geointerpo[era5]"
    # Then set up your CDS API key:
    # https://cds.climate.copernicus.eu/api-how-to
    ```
    80+ years of hourly global reanalysis at 0.25°. Free CDS account required.

=== "Interactive Visualization"
    ```bash
    pip install "geointerpo[interactive]"
    # or:
    pip install plotly
    ```
    `result.plot_interactive()` — zoomable Plotly map in notebook or browser.

=== "Visualization"
    ```bash
    pip install "geointerpo[viz]"
    ```
    `result.plot()` and all `viz.*` helpers via **matplotlib**.

=== "Notebooks"
    ```bash
    pip install "geointerpo[notebooks]"
    ```
    Interactive maps in Jupyter via **plotly** + **leafmap** + **geemap**.

---

## Extras at a glance

| Extra | Packages | Unlocks |
|---|---|---|
| `kriging` | pykrige, scikit-learn | Kriging, GP, RF, GBM, RK methods |
| `geostat` | gstools | Cokriging (KED), Sequential Gaussian Simulation |
| `uncertainty` | mapie | Conformal prediction intervals for GBM |
| `raster` | rasterio, rioxarray | GeoTIFF export, boundary clipping |
| `data` | meteostat, openaq, openmeteo-requests | Live weather & air quality APIs |
| `era5` | cdsapi | ERA5 reanalysis (needs free CDS account) |
| `interactive` | plotly | Interactive zoomable maps |
| `viz` | matplotlib | Static plots |
| `dem` | srtm.py | SRTM elevation covariate |
| `geo` | geopy | Named-location geocoding |
| `notebooks` | plotly, leafmap, geemap, jupyter | Interactive maps in Jupyter |
| `full` | all core extras | Recommended for data science |
| `dev` | full + notebooks + pytest | Contributors |

---

## From source

```bash
git clone https://github.com/homayounrezaie/geointerpo
cd geointerpo
pip install -e ".[full,geostat]"
```

!!! note
    Editable install — changes to the source take effect immediately without reinstalling.

## Verify

```bash
python -c "import geointerpo; print(geointerpo.__version__)"
# → 0.2.0
```
