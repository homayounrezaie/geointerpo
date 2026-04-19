# geointerpo

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/methods-15-teal?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/docs-online-orange?style=flat-square"/>
</p>

<p align="center">
  Spatial interpolation for Python — 15 algorithms, live data APIs, boundary clipping, and GEE validation.<br/>
  Drop in point data, get a smooth interpolated raster out.<br/><br/>
  Fetch live weather, air quality, or precipitation data from <b>Meteostat</b>, <b>OpenAQ</b>, and <b>Open-Meteo</b>.<br/>
  Define your study area by place name, polygon file, or bounding box — boundaries are resolved automatically.<br/>
  Validate results against <b>MODIS</b>, <b>CHIRPS</b>, and <b>Sentinel-5P</b> satellite products via Google Earth Engine.<br/>
  Export to <b>GeoTIFF</b> or <b>NetCDF</b>, run spatial cross-validation, and compare methods side by side.
</p>

<p align="center">
  <a href="https://homayounrezaie.github.io/geonterpo"><b>📖 Documentation</b></a> ·
  <a href="https://homayounrezaie.github.io/geonterpo/install/">Install</a> ·
  <a href="https://homayounrezaie.github.io/geonterpo/quickstart/">Quickstart</a> ·
  <a href="https://homayounrezaie.github.io/geonterpo/interpolators/">Methods</a> ·
  <a href="https://homayounrezaie.github.io/geonterpo/examples/">Examples</a>
</p>

---

<p align="center">
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/kriging.png" width="270"/>
  &nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/natural_neighbor.png" width="270"/>
  &nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/gp.png" width="270"/>
</p>
<p align="center"><i>Ordinary Kriging · Natural Neighbor · Gaussian Process — same 60 stations, Alberta, Canada</i></p>

---

## Install

```bash
pip install "geointerpo[full]"
```

## Quickstart

```python
from geointerpo import Pipeline

result = Pipeline(
    data="stations.csv",               # CSV, GeoDataFrame, or live API
    boundary="Calgary, Alberta",       # place name, bbox, or polygon file
    method=["idw", "kriging", "spline"],
).run()

result.plot()            # side-by-side comparison
result.metrics_table()   # cross-validation RMSE / r
result.save("outputs/")  # GeoTIFF + PNG + CSV
```

---

## Methods

geointerpo covers the full ArcGIS Spatial Analyst interpolation toolkit plus modern ML methods. All share the same interface — swap `method=` to compare.

### Distance-based

The fastest methods — no statistical assumptions, exact at data points. Ideal as a quick baseline or when data is dense and evenly distributed.

<p align="center">
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/idw.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/nearest.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/linear.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/cubic.png" width="220"/>
</p>

`idw` · `nearest` · `linear` · `cubic`

### Spline & Trend

Fit smooth continuous surfaces. Splines minimise curvature; RBF offers eight kernel choices; Trend fits a global polynomial for large-scale patterns.

<p align="center">
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/spline.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/spline_tension.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/rbf.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/trend.png" width="220"/>
</p>

`spline` · `spline_tension` · `rbf` · `trend`

### Geostatistical

Account for spatial autocorrelation via a variogram model. Produce statistically optimal, unbiased estimates. Natural Neighbor uses Voronoi area-stealing weights — smooth and exact at data locations.

<p align="center">
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/kriging.png" width="290"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/uk.png" width="290"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/natural_neighbor.png" width="290"/>
</p>

`kriging` (Ordinary) · `uk` (Universal) · `natural_neighbor`

### Machine Learning

Capture non-linear spatial patterns. GP returns a full uncertainty surface alongside the mean prediction. Regression Kriging combines an ML trend with Kriging of the residuals.

<p align="center">
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/gp.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/rf.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/gbm.png" width="220"/>
  &nbsp;
  <img src="https://raw.githubusercontent.com/homayounrezaie/geointerpo/main/outputs/methods/rk.png" width="220"/>
</p>

`gp` (Gaussian Process) · `rf` (Random Forest) · `gbm` (Gradient Boosting) · `rk` (Regression Kriging)

---

## References

- [ArcGIS Pro — Interpolation Tools Overview](https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/an-overview-of-the-interpolation-tools.htm)
- [3 Best Methods for Spatial Interpolation — Towards Data Science](https://towardsdatascience.com/3-best-methods-for-spatial-interpolation-912cab7aee47/)
- [GeoStat-Framework/PyKrige](https://github.com/GeoStat-Framework/PyKrige) — Ordinary, Universal, and Regression Kriging
- [GeoStat-Framework/GSTools](https://github.com/GeoStat-Framework/GSTools) — Covariance models, variograms, random fields
- [mmaelicke/scikit-gstat](https://github.com/mmaelicke/scikit-gstat) — Variogram estimation and ordinary kriging
- [DataverseLabs/pyinterpolate](https://github.com/DataverseLabs/pyinterpolate) — IDW, kriging, Poisson kriging
- [fatiando/verde](https://github.com/fatiando/verde) — Machine-learning-style spatial gridding
- [GeostatsGuy/GeostatsPy](https://github.com/GeostatsGuy/GeostatsPy) — GSLIB-based geostatistics
