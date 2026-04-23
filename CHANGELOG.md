# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.2.0] — 2026-04-22

### Added

**Performance**
- `IDWInterpolator`: replaced per-point loop with vectorized `scipy.spatial.cKDTree` query — 50–200× faster on large grids, identical results. New `n_neighbors` parameter to restrict each prediction to the k nearest stations.

**Uncertainty quantification**
- `KrigingInterpolator.predict_with_variance(bbox, resolution)`: returns `(mean_da, variance_da)` — both as `xr.DataArray`. The variance surface is highest far from stations. Backward compatible: `attrs["variance"]` still set.
- `KrigingInterpolator`: `anisotropy_scaling` and `anisotropy_angle` parameters to model directional spatial correlation.
- `MLInterpolator.predict_with_uncertainty(bbox, resolution, alpha)`: returns `(mean, lower, upper)` DataArrays.
  - GP: native posterior standard deviation.
  - RF: bootstrap percentile intervals from individual trees (no extra install).
  - GBM: MAPIE conformal prediction (`pip install mapie`).
- `Pipeline.variance_grids`: dict of variance DataArrays collected from methods that support it (Kriging, Cokriging, SGS).

**Interactive visualization**
- New `geointerpo/viz_interactive.py` module with `plot_interactive(da, backend="auto")`.
- `InterpolationResult.plot_interactive()` — one call renders a zoomable Plotly or leafmap map.
- Auto-detects available backend (plotly first, then leafmap).

**New data sources**
- `ERA5Source` (`geointerpo/sources/era5.py`): fetches ERA5 reanalysis via CDS API (`pip install cdsapi`). Supports temperature, precipitation, wind, radiation, and 20+ more variables from 1940 to present.
- `NASAPowerSource` (`geointerpo/sources/nasapower.py`): fetches meteorological/solar data from NASA POWER REST API — free, no account required, samples a grid of virtual stations within the bbox.
- Pipeline: `data="era5"` and `data="nasapower"` now recognized API source strings.

**Advanced geostatistics** (requires `pip install gstools`)
- `CokrigingInterpolator` (`geointerpo/interpolators/cokriging.py`): Kriging with External Drift — uses a secondary correlated variable (e.g. elevation) to guide interpolation. Method keys: `"cokriging"`, `"ked"`.
- `SGSInterpolator` (`geointerpo/interpolators/sgs.py`): Sequential Gaussian Simulation — produces `n_realizations` equally probable stochastic realizations. `predict_with_std()` returns ensemble mean + std. `realize()` returns 3-D `(realization, lat, lon)` DataArray. Method keys: `"sgs"`, `"simulation"`.

**Improved cross-validation**
- `spatial_cv(interpolator, gdf, strategy, k, buffer_km)` in `geointerpo/validation/metrics.py`.
  - `strategy="block"`: existing blocked k-fold (spatially sorted).
  - `strategy="loo"`: leave-one-out with optional `buffer_km` exclusion zone — removes autocorrelation leakage around each test point.
  - Returns `per_fold` list of per-fold metrics alongside aggregate statistics.

**Auto-ranking**
- `InterpolationResult.best_method(by="rmse")` → returns the name of the winning method.
- `InterpolationResult.rank_methods(by="rmse")` → ranked DataFrame with `rank` column.
- Pipeline prints a ranked table automatically after `[5/5]`.

**Resolution in km**
- `Pipeline(resolution="5km")` and `resolution="500m"` now accepted — converted to degrees internally (1° ≈ 111 km). Float degrees still work as before.
- `_parse_resolution()` helper exposed for direct use.

### Changed
- `__version__` bumped to `0.2.0`.
- `pyproject.toml`: added `geostat`, `uncertainty`, `interactive`, `era5` extras.
- `full` extra now includes `plotly`, `gstools`, and `mapie`.
- Method registry extended with `cokriging`, `ked`, `sgs`, `simulation` keys.

### Fixed
- `Pipeline._interpolate`: now uses `predict_with_variance()` when available instead of `predict()`, so variance grids are collected without a separate call.

---

## [Unreleased]

### Added
- MkDocs documentation site with GitHub Pages deployment
- Method output gallery (15 PNGs) in docs and README
- `CONTRIBUTING.md` and `CHANGELOG.md`

### Fixed
- `SearchRadius`: now selects neighbours per prediction location instead of trimming the dataset once near the centroid; fixed-radius search can leave `NaN` gaps when no local stations are available
- `NaturalNeighborInterpolator`: vectorized IDW fallback now fills all NaN results, including Voronoi failures inside the convex hull (previously only out-of-hull points were filled)
- Smooth visualization: switched from `pcolormesh` to `contourf` (128 levels) for MODIS-style output
- Geographic aspect ratio in plots: `1/cos(mid_lat)` so lon/lat maps appear undistorted
- `MLInterpolator`: GP kernel `length_scale` default changed from `1.0` to `50_000` m (UTM-correct)
- `MeteostatSource`: rewritten for meteostat v2.1.4 API (`stations.nearby` + `daily`)
- `SplineInterpolator`: degree reduction loop prevents crash with fewer than 16 points

### Changed
- `viz.py`: removed `interactive_map()` — leafmap/geemap kept out of core library
- `pyproject.toml`: removed `verde` from all extras; `leafmap`/`geemap` moved to `notebooks` extra only

---

## [0.1.0] — 2025-04

### Added
- Initial release
- 15 interpolation algorithms: IDW, Ordinary Kriging, Universal Kriging, Natural Neighbor, Spline (Regularized + Tension), Trend, RBF, Nearest, Linear, Cubic, Gaussian Process, Random Forest, Gradient Boosting, Regression Kriging
- `Pipeline` — three-step workflow matching ArcGIS Spatial Analyst
- Boundary loading from place names, files, bbox tuples, GeoDataFrames
- Data sources: Meteostat, OpenAQ, Open-Meteo, sample data
- GEE validation against MODIS LST, CHIRPS, Sentinel-5P
- GeoTIFF and NetCDF export via rioxarray
- Blocked spatial k-fold cross-validation
- `SearchRadius` (variable/fixed) parameter
- CLI: `geointerpo run`, `geointerpo demo`, `geointerpo benchmark`
- YAML config support
