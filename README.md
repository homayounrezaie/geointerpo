# geointerpo

Python spatial interpolation toolkit — 15 methods, boundaries, point data, raster export.

**[Documentation](https://homayounrezaie.github.io/geonterpo)** · [Install](https://homayounrezaie.github.io/geonterpo/install/) · [Quickstart](https://homayounrezaie.github.io/geonterpo/quickstart/) · [Methods](https://homayounrezaie.github.io/geonterpo/interpolators/) · [Examples](https://homayounrezaie.github.io/geonterpo/examples/)

---

## Install

```bash
pip install "geointerpo[full]"
```

## Quickstart

```python
from geointerpo import Pipeline

result = Pipeline(
    data="stations.csv",
    boundary="Calgary, Alberta, Canada",
    method=["idw", "kriging", "spline"],
).run()

result.plot()
result.save("outputs/")
```

---

## Method Gallery

15 algorithms on the same dataset — 60 weather stations, Alberta, Canada:

<table>
<tr>
  <td align="center"><img src="outputs/methods/idw.png" width="220"/><br/><b>IDW</b></td>
  <td align="center"><img src="outputs/methods/kriging.png" width="220"/><br/><b>Ordinary Kriging</b></td>
  <td align="center"><img src="outputs/methods/uk.png" width="220"/><br/><b>Universal Kriging</b></td>
</tr>
<tr>
  <td align="center"><img src="outputs/methods/natural_neighbor.png" width="220"/><br/><b>Natural Neighbor</b></td>
  <td align="center"><img src="outputs/methods/spline.png" width="220"/><br/><b>Spline (Regularized)</b></td>
  <td align="center"><img src="outputs/methods/spline_tension.png" width="220"/><br/><b>Spline Tension</b></td>
</tr>
<tr>
  <td align="center"><img src="outputs/methods/trend.png" width="220"/><br/><b>Trend Surface</b></td>
  <td align="center"><img src="outputs/methods/rbf.png" width="220"/><br/><b>RBF</b></td>
  <td align="center"><img src="outputs/methods/nearest.png" width="220"/><br/><b>Nearest Neighbor</b></td>
</tr>
<tr>
  <td align="center"><img src="outputs/methods/linear.png" width="220"/><br/><b>Linear (Delaunay)</b></td>
  <td align="center"><img src="outputs/methods/cubic.png" width="220"/><br/><b>Cubic (Clough-Tocher)</b></td>
  <td align="center"><img src="outputs/methods/gp.png" width="220"/><br/><b>Gaussian Process</b></td>
</tr>
<tr>
  <td align="center"><img src="outputs/methods/rf.png" width="220"/><br/><b>Random Forest</b></td>
  <td align="center"><img src="outputs/methods/gbm.png" width="220"/><br/><b>Gradient Boosting</b></td>
  <td align="center"><img src="outputs/methods/rk.png" width="220"/><br/><b>Regression Kriging</b></td>
</tr>
</table>

---

## Stack

`scipy` · `geopandas` · `shapely` · `pyproj` · `xarray` · `pykrige` · `scikit-learn` · `rasterio` · `matplotlib`

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
