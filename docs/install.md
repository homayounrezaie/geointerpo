# Install

## Core install

```bash
pip install geointerpo
```

The core package includes IDW, RBF, spline, griddata, boundary loading, and the Pipeline. No API keys needed.

## Recommended install

```bash
pip install "geointerpo[full]"
```

Adds kriging, ML methods, GeoTIFF export, all three data APIs, and matplotlib. Everything except GEE and interactive notebooks.

## Extras

Install only what you need:

```bash
pip install "geointerpo[kriging]"     # Ordinary/Universal Kriging + GP/RF/GBM via pykrige + sklearn
pip install "geointerpo[raster]"      # GeoTIFF export + boundary clipping via rasterio + rioxarray
pip install "geointerpo[data]"        # Live weather/air-quality APIs (Meteostat, OpenAQ, Open-Meteo)
pip install "geointerpo[gee]"         # Google Earth Engine validation (also needs earthengine authenticate)
pip install "geointerpo[viz]"         # Static matplotlib plots
pip install "geointerpo[dem]"         # SRTM elevation covariate via srtm.py
pip install "geointerpo[geo]"         # Named-location geocoding via geopy
pip install "geointerpo[notebooks]"   # leafmap + geemap + Jupyter (interactive maps in notebooks)
```

### What each extra unlocks

| Extra | Packages added | Unlocks |
|---|---|---|
| `kriging` | `pykrige`, `scikit-learn` | `"kriging"`, `"uk"`, `"gp"`, `"rf"`, `"gbm"`, `"rk"` methods |
| `raster` | `rasterio`, `rioxarray` | `result.save()` GeoTIFF, `clip_to_boundary=True` |
| `data` | `meteostat`, `openaq`, `openmeteo-requests` | `data="meteostat"`, `data="openaq"`, `data="openmeteo"` |
| `gee` | `earthengine-api` | `validate_with_gee=True`, MODIS/CHIRPS/Sentinel comparison |
| `viz` | `matplotlib` | `result.plot()`, `viz.plot_interpolated()` |
| `dem` | `srtm.py` | `include_dem=True` SRTM elevation covariate |
| `geo` | `geopy` | `boundary="Tehran, Iran"` named-location geocoding |
| `notebooks` | `leafmap`, `geemap`, `jupyter` | Interactive maps in Jupyter notebooks |
| `full` | all of the above except GEE + notebooks | Recommended for local data science work |
| `dev` | `full` + GEE + notebooks + pytest + ruff | Contributors and CI |

## Install from source

```bash
git clone https://github.com/homayounrezaie/geonterpo
cd geointerpo
pip install -e ".[full]"
```

Editable install — changes to the source take effect immediately without reinstalling.

## GEE authentication

Required only if you use `validate_with_gee=True`:

```bash
pip install "geointerpo[gee]"
earthengine authenticate
```

This opens a browser for a one-time OAuth flow. Credentials are cached locally.

## Verify

```bash
python -c "import geointerpo; print(geointerpo.__version__)"
```

Or run the offline demo:

```bash
python examples/quickstart.py
```
