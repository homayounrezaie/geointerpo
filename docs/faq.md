# FAQ & Troubleshooting

## Installation errors

**`ModuleNotFoundError: No module named 'pykrige'`**

Kriging and ML methods require the `kriging` extra:

```bash
pip install "geointerpo[kriging]"
```

**`ModuleNotFoundError: No module named 'rioxarray'`**

GeoTIFF export and boundary clipping require the `raster` extra:

```bash
pip install "geointerpo[raster]"
```

**`ModuleNotFoundError: No module named 'matplotlib'`**

Plotting requires the `viz` extra:

```bash
pip install "geointerpo[viz]"
```

---

## Boundary errors

**`ValueError: Could not geocode location 'X'`**

Nominatim couldn't find the place name. Try:

- A more specific name: `"Calgary, Alberta, Canada"` instead of `"Calgary"`
- A bbox tuple: `boundary=(-114.5, 50.8, -113.8, 51.3)`
- A file: `boundary="my_region.geojson"`

**`boundary clips everything to NaN`**

The boundary polygon doesn't overlap your station data. Check:

1. `boundary_bbox(boundary)` returns a bbox that covers your data
2. `rioxarray` is installed: `pip install "geointerpo[raster]"`
3. Try `clip_to_boundary=False` to rule out the clipping step

---

## Data source errors

**`No stations returned from Meteostat`**

Meteostat may have no stations for the bbox/date combination. Try:

- A wider bbox (increase `padding_deg`)
- A different date (some stations have gaps)
- `data="sample"` to confirm the pipeline works offline

**`openaq API error`**

OpenAQ is rate-limited without an API key. Try adding a delay or reducing the bbox.

**`ImportError: No module named 'meteostat'`**

```bash
pip install "geointerpo[data]"
```

---

## GEE errors

**`EEException: Please authorise access to your Earth Engine account`**

```bash
earthengine authenticate
```

**`ImportError: No module named 'earthengine'`**

```bash
pip install "geointerpo[gee]"
```

---

## Interpolation errors

**`ValueError: Not enough points for spline interpolation`**

Spline requires at least 16 points (or 4× the polynomial degree). Either:

- Add more stations
- Use a lower-degree method: `method="rbf"` or `method="idw"`

**`kriging` returns all NaN**

Check that `pykrige` is installed and the variogram model fits the data range. Try `variogram_model="linear"` as a safe fallback.

**`natural_neighbor` output looks wrong / empty**

This method requires more than ~10 stations spread over the area. With very sparse data, the IDW fallback activates for most grid points. The output will look similar to IDW in that case — which is correct behaviour.

---

## Plotting

**`RuntimeError: Colorbar layout not compatible with tight_layout`**

This is a matplotlib issue with tight_layout + colorbar. The library uses `layout="constrained"` internally and avoids this. If you're building your own figure, use:

```python
fig, ax = plt.subplots(layout="constrained")
```

**Interactive map doesn't display in Jupyter**

Make sure `leafmap` and `ipykernel` are installed:

```bash
pip install "geointerpo[notebooks]"
```

---

## Performance

**Pipeline is slow for large grids**

- Increase `resolution` (0.5 instead of 0.1) for a first pass
- `natural_neighbor` runs O(n_stations × n_grid) Voronoi computations — use IDW or RBF for large grids
- `gp` (Gaussian Process) scales as O(n³) — prefer `rf` or `gbm` for more than ~500 stations

**Memory error**

Reduce the bbox, increase the resolution, or use a method with lower memory usage (IDW, linear).
