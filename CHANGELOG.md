# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- MkDocs documentation site with GitHub Pages deployment
- Method output gallery (15 PNGs) in docs and README
- `CONTRIBUTING.md` and `CHANGELOG.md`

### Fixed
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
