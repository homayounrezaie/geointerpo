"""Quick-start: the 3-step Pipeline workflow.

Three inputs → one call → results.

    Step 1  data=      Point data: CSV file, geo file, GeoDataFrame, or API source
    Step 2  boundary=  Study area: place name, file, 4-corner tuple, or polygon
    Step 3  method=    Interpolation method(s) with optional per-method params

Run (offline, no network needed):
    python examples/quickstart.py

For interactive maps:
    pip install 'geointerpo[interactive]'
"""

from geointerpo import Pipeline

# =============================================================================
# Example A — Offline demo with auto-ranking (no network)
# =============================================================================
result = Pipeline(
    data="sample",                            # Step 1: built-in synthetic data
    variable="temperature",
    boundary=(-114.5, 50.8, -113.8, 51.3),   # Step 2: four corners
    method=["idw", "kriging", "spline"],      # Step 3: compare three methods
    method_params={
        "idw":     {"power": 2},
        "kriging": {"variogram_model": "spherical"},
    },
    resolution="2km",                         # resolution as a string — 2 km grid
    cv_folds=5,
).run()

print(result.metrics_table())
print(f"\nBest method: {result.best_method()}")
print("\nFull ranking:")
print(result.rank_methods())
result.save("outputs/quickstart")

# Interactive map (requires: pip install geointerpo[interactive])
try:
    fig = result.plot_interactive()
    fig.show()
except ImportError:
    pass


# =============================================================================
# Example B — CSV file + place-name boundary (needs network for Nominatim)
# =============================================================================
# result = Pipeline(
#     data="my_stations.csv",               # Step 1: CSV (lon, lat, value columns)
#     boundary="Tehran, Iran",              # Step 2: place name → polygon
#     method="kriging",                     # Step 3: single method
# ).run()


# =============================================================================
# Example C — Shapefile + polygon file
# =============================================================================
# result = Pipeline(
#     data="data/stations.shp",            # Step 1: shapefile
#     boundary="data/study_area.geojson",   # Step 2: polygon file
#     method=["idw", "rbf"],               # Step 3: two methods
# ).run()


# =============================================================================
# Example D — Live API + city boundary (needs network)
# =============================================================================
# result = Pipeline(
#     data="meteostat",                    # Step 1: live weather API
#     variable="temperature",
#     date="2024-07-15",
#     boundary="Calgary, Alberta, Canada", # Step 2: Nominatim polygon
#     method="kriging",                    # Step 3: method
#     resolution=0.05,
# ).run()
