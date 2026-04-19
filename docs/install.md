# Install

## Recommended

```bash
pip install "geointerpo[full]"
```

Adds kriging, ML methods, GeoTIFF export, all three data APIs, and matplotlib. Covers 95% of use cases.

## Core only

```bash
pip install geointerpo
```

Includes IDW, RBF, spline, griddata, boundary loading, and the Pipeline. No kriging, no ML, no APIs.

## Pick your extras

=== "Kriging & ML"
    ```bash
    pip install "geointerpo[kriging]"
    ```
    Unlocks `kriging`, `uk`, `gp`, `rf`, `gbm`, `rk` methods via **pykrige** + **scikit-learn**.

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

=== "GEE Validation"
    ```bash
    pip install "geointerpo[gee]"
    earthengine authenticate
    ```
    Compare against MODIS, CHIRPS, Sentinel-5P via **earthengine-api**.

=== "Visualization"
    ```bash
    pip install "geointerpo[viz]"
    ```
    `result.plot()` and all `viz.*` helpers via **matplotlib**.

=== "Notebooks"
    ```bash
    pip install "geointerpo[notebooks]"
    ```
    Interactive maps in Jupyter via **leafmap** + **geemap**.

---

## Extras at a glance

| Extra | Packages | Unlocks |
|---|---|---|
| `kriging` | pykrige, scikit-learn | Kriging, GP, RF, GBM, RK methods |
| `raster` | rasterio, rioxarray | GeoTIFF export, boundary clipping |
| `data` | meteostat, openaq, openmeteo-requests | Live weather & air quality APIs |
| `gee` | earthengine-api | MODIS / CHIRPS / Sentinel validation |
| `viz` | matplotlib | Static plots |
| `dem` | srtm.py | SRTM elevation covariate |
| `geo` | geopy | Named-location geocoding |
| `notebooks` | leafmap, geemap, jupyter | Interactive maps |
| `full` | all above except GEE & notebooks | Recommended for data science |
| `dev` | full + GEE + notebooks + pytest | Contributors |

---

## From source

```bash
git clone https://github.com/homayounrezaie/geonterpo
cd geonterpo
pip install -e ".[full]"
```

!!! note
    Editable install — changes to the source take effect immediately without reinstalling.

## GEE authentication

!!! warning "One-time setup required"
    GEE validation (`validate_with_gee=True`) requires a one-time browser auth:

    ```bash
    pip install "geointerpo[gee]"
    earthengine authenticate
    ```

## Verify

```bash
python -c "import geointerpo; print(geointerpo.__version__)"
python examples/quickstart.py
```
