---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

# geointerpo

Point data in. Smooth interpolated raster out.  
15 algorithms · live weather & air-quality APIs · boundary clipping · GEE satellite validation.

<div class="hero-buttons" markdown>
<a class="hero-btn hero-btn-primary" href="install/">Get Started</a>
<a class="hero-btn hero-btn-secondary" href="interpolators/">Browse Methods</a>
<a class="hero-btn hero-btn-secondary" href="https://github.com/homayounrezaie/geointerpo">GitHub</a>
</div>

</div>

## Why geointerpo?

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **One API, 15 methods**

    ---

    Every algorithm shares `.fit()` → `.predict()`. Swap `method=` to compare IDW, Kriging, GP, and 12 more without changing any other code.

    [:octicons-arrow-right-24: Browse methods](interpolators.md)

-   :material-map-marker-radius:{ .lg .middle } **Smart boundaries**

    ---

    Pass a place name, a file, or a bbox. The pipeline geocodes it, derives the grid, and clips the output automatically.

    [:octicons-arrow-right-24: Boundary guide](boundaries.md)

-   :material-database-import:{ .lg .middle } **Live data, zero setup**

    ---

    Pull real weather, air quality, and precipitation data from **Meteostat**, **OpenAQ**, and **Open-Meteo** — no API keys needed.

    [:octicons-arrow-right-24: Data sources](api/sources.md)

-   :material-satellite-variant:{ .lg .middle } **Satellite validation**

    ---

    Compare your interpolated surface against **MODIS**, **CHIRPS**, and **Sentinel-5P** reference products via Google Earth Engine.

    [:octicons-arrow-right-24: GEE validation](api/validation.md)

-   :material-chart-line:{ .lg .middle } **Built-in cross-validation**

    ---

    Blocked spatial k-fold CV runs automatically. RMSE, MAE, bias, and r printed for every method after every run.

    [:octicons-arrow-right-24: Pipeline reference](pipeline.md)

-   :material-export:{ .lg .middle } **Export anywhere**

    ---

    Save to **GeoTIFF**, **NetCDF**, or **PNG**. Every output carries CRS metadata and is ready for QGIS, ArcGIS, or further analysis.

    [:octicons-arrow-right-24: Examples](examples.md)

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
    ).run()

    result.plot()           # side-by-side comparison
    result.metrics_table()  # RMSE / MAE / r for each method
    result.save("outputs/") # GeoTIFF + PNG + metrics CSV
    ```

=== "Live API"

    ```python
    result = Pipeline(
        data="meteostat",
        variable="temperature",
        date="2024-07-15",
        boundary="Bavaria, Germany",
        method=["kriging", "gp"],
        validate_with_gee=True,
    ).run()
    ```

=== "Offline demo"

    ```python
    result = Pipeline(
        data="sample",
        variable="temperature",
        boundary=(-114.5, 50.8, -113.8, 51.3),
        method=["idw", "kriging"],
        resolution=0.05,
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
  <figure><img src="assets/methods/kriging.png" width="230" alt="Kriging"/><figcaption>Ordinary Kriging</figcaption></figure>
  <figure><img src="assets/methods/uk.png" width="230" alt="Universal Kriging"/><figcaption>Universal Kriging</figcaption></figure>
  <figure><img src="assets/methods/natural_neighbor.png" width="230" alt="Natural Neighbor"/><figcaption>Natural Neighbor</figcaption></figure>
</div>

### Machine Learning

<div class="method-row" markdown>
  <figure><img src="assets/methods/gp.png" width="230" alt="GP"/><figcaption>Gaussian Process</figcaption></figure>
  <figure><img src="assets/methods/rf.png" width="230" alt="RF"/><figcaption>Random Forest</figcaption></figure>
  <figure><img src="assets/methods/rk.png" width="230" alt="RK"/><figcaption>Regression Kriging</figcaption></figure>
</div>

[:octicons-arrow-right-24: Full method reference with all 15 algorithms](interpolators.md)

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

=== "From source"
    ```bash
    git clone https://github.com/homayounrezaie/geointerpo
    cd geointerpo && pip install -e ".[full]"
    ```

[:octicons-arrow-right-24: Full install guide with all extras](install.md)
