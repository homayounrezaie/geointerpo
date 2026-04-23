---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

# geointerpo

Point data in. Smooth interpolated raster out.  
17 algorithms · live weather & air-quality APIs · uncertainty quantification · interactive maps.

<div class="hero-buttons" markdown>
<a class="hero-btn hero-btn-primary" href="install/">Get Started</a>
<a class="hero-btn hero-btn-secondary" href="interpolators/">Browse Methods</a>
<a class="hero-btn hero-btn-secondary" href="https://github.com/homayounrezaie/geointerpo">GitHub</a>
</div>

</div>

## Why geointerpo?

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **One API, 17 methods**

    ---

    Every algorithm shares `.fit()` → `.predict()`. Swap `method=` to compare IDW, Kriging, Cokriging, SGS, GP, and 12 more without changing any other code.

    [:octicons-arrow-right-24: Browse methods](interpolators.md)

-   :material-map-marker-radius:{ .lg .middle } **Smart boundaries**

    ---

    Pass a place name, a file, or a bbox. The pipeline geocodes it, derives the grid, and clips the output automatically.

    [:octicons-arrow-right-24: Boundary guide](boundaries.md)

-   :material-database-import:{ .lg .middle } **Live data, zero setup**

    ---

    Pull real weather and air quality data from **Meteostat**, **OpenAQ**, **Open-Meteo**, and **NASA POWER** — no API keys needed. **ERA5** reanalysis via CDS API.

    [:octicons-arrow-right-24: Data sources](api/sources.md)

-   :material-chart-bell-curve:{ .lg .middle } **Uncertainty quantification**

    ---

    Kriging variance surfaces, GP posterior std, RF bootstrap intervals, and conformal prediction (MAPIE) — every method can now express *how sure* it is.

    [:octicons-arrow-right-24: Uncertainty guide](interpolators.md#uncertainty)

-   :material-map:{ .lg .middle } **Interactive maps**

    ---

    `result.plot_interactive()` renders a zoomable map with plotly or leafmap — no static PNG, no extra code.

    [:octicons-arrow-right-24: Visualization guide](examples.md)

-   :material-chart-line:{ .lg .middle } **Auto-ranked cross-validation**

    ---

    Spatial k-fold or leave-one-out CV runs automatically. `result.best_method()` and `result.rank_methods()` tell you which algorithm won.

    [:octicons-arrow-right-24: Pipeline reference](pipeline.md)

-   :material-export:{ .lg .middle } **Export anywhere**

    ---

    Save to **GeoTIFF**, **NetCDF**, or **PNG**. Every output carries CRS metadata and is ready for QGIS, ArcGIS, or further analysis.

    [:octicons-arrow-right-24: Examples](examples.md)

-   :material-speedometer:{ .lg .middle } **50–200× faster IDW**

    ---

    KD-tree vectorized IDW replaces the old per-point loop — identical results, dramatically less waiting on large grids.

    [:octicons-arrow-right-24: What's new in v0.2](interpolators.md)

</div>

---

## Quickstart

=== "Three lines"

    ```python
    from geointerpo import Pipeline

    result = Pipeline(
        data="stations.csv",
        boundary="Calgary, Alberta, Canada",
        method=["idw", "kriging", "spline"],
        resolution="5km",   # ← km strings now supported
    ).run()

    result.plot()               # side-by-side matplotlib comparison
    result.plot_interactive()   # zoomable plotly map
    result.best_method()        # → "kriging"
    result.rank_methods()       # ranked DataFrame
    result.save("outputs/")     # GeoTIFF + PNG + metrics CSV
    ```

=== "Uncertainty"

    ```python
    from geointerpo.interpolators import KrigingInterpolator, MLInterpolator

    # Kriging: mean + variance surface
    model = KrigingInterpolator().fit(gdf)
    mean_da, var_da = model.predict_with_variance(bbox, resolution=0.1)

    # RF: bootstrap prediction interval
    model = MLInterpolator(method="rf").fit(gdf)
    mean, lower, upper = model.predict_with_uncertainty(bbox, alpha=0.1)
    ```

=== "Cokriging / SGS"

    ```python
    # Cokriging with elevation as secondary variable
    from geointerpo.interpolators import CokrigingInterpolator

    model = CokrigingInterpolator(
        secondary_col="elevation",
        secondary_fn=dem_lookup_fn,   # callable(xs_utm, ys_utm) → elevations
    ).fit(gdf_with_elevation)
    grid = model.predict(bbox, resolution=0.1)

    # Sequential Gaussian Simulation — stochastic realizations
    from geointerpo.interpolators import SGSInterpolator

    model = SGSInterpolator(n_realizations=100).fit(gdf)
    mean_da, std_da = model.predict_with_std(bbox)
    all_realizations = model.realize(bbox)  # (100, n_lat, n_lon) DataArray
    ```

=== "Spatial CV"

    ```python
    from geointerpo.validation.metrics import spatial_cv
    from geointerpo.interpolators import IDWInterpolator

    model = IDWInterpolator(power=2)
    # LOO with 50 km buffer — removes autocorrelation leakage
    result = spatial_cv(model, gdf, strategy="loo", buffer_km=50)
    print(result["rmse"], result["r"])
    ```

=== "Offline demo"

    ```python
    result = Pipeline(
        data="sample",
        variable="temperature",
        boundary=(-114.5, 50.8, -113.8, 51.3),
        method=["idw", "kriging"],
        resolution="2km",
    ).run()
    ```

!!! tip "No data? No problem."
    Use `data="sample"` for a built-in synthetic dataset — no network, no API keys, runs in seconds.

---

## Methods at a glance

All outputs below use the same 60 weather stations over Alberta, Canada.

### Distance-based

<div class="method-row" markdown>
  <figure><img src="assets/methods/idw.png" width="230" alt="IDW"/><figcaption>IDW</figcaption></figure>
  <figure><img src="assets/methods/nearest.png" width="230" alt="Nearest"/><figcaption>Nearest Neighbor</figcaption></figure>
  <figure><img src="assets/methods/linear.png" width="230" alt="Linear"/><figcaption>Linear (Delaunay)</figcaption></figure>
</div>

### Spline & Trend

<div class="method-row" markdown>
  <figure><img src="assets/methods/spline.png" width="230" alt="Spline"/><figcaption>Spline</figcaption></figure>
  <figure><img src="assets/methods/rbf.png" width="230" alt="RBF"/><figcaption>RBF</figcaption></figure>
  <figure><img src="assets/methods/trend.png" width="230" alt="Trend"/><figcaption>Trend Surface</figcaption></figure>
</div>

### Geostatistical

<div class="method-row" markdown>
  <figure><img src="assets/methods/kriging.png" width="230" alt="Kriging"/><figcaption>Ordinary Kriging + variance</figcaption></figure>
  <figure><img src="assets/methods/uk.png" width="230" alt="Universal Kriging"/><figcaption>Universal Kriging</figcaption></figure>
  <figure><img src="assets/methods/natural_neighbor.png" width="230" alt="Natural Neighbor"/><figcaption>Natural Neighbor</figcaption></figure>
</div>

### Machine Learning

<div class="method-row" markdown>
  <figure><img src="assets/methods/gp.png" width="230" alt="GP"/><figcaption>Gaussian Process + σ</figcaption></figure>
  <figure><img src="assets/methods/rf.png" width="230" alt="RF"/><figcaption>Random Forest + intervals</figcaption></figure>
  <figure><img src="assets/methods/rk.png" width="230" alt="RK"/><figcaption>Regression Kriging</figcaption></figure>
</div>

[:octicons-arrow-right-24: Full method reference with all 17 algorithms](interpolators.md)

---

## Install

=== "Recommended"
    ```bash
    pip install "geointerpo[full]"
    ```

=== "Core only"
    ```bash
    pip install geointerpo
    ```

=== "Advanced geostatistics (cokriging + SGS)"
    ```bash
    pip install "geointerpo[full,geostat]"
    ```

=== "From source"
    ```bash
    git clone https://github.com/homayounrezaie/geointerpo
    cd geointerpo && pip install -e ".[full,geostat]"
    ```

[:octicons-arrow-right-24: Full install guide with all extras](install.md)
