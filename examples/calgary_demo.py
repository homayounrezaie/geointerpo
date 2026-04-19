"""Calgary temperature interpolation — 3-step Pipeline demo.

    Step 1  data=      synthetic offline data (swap for CSV / API)
    Step 2  boundary=  Calgary city limits resolved via Nominatim
    Step 3  method=    three methods compared side-by-side

Nominatim is called once for the boundary polygon (needs network).
Everything else is offline.

Run:
    python examples/calgary_demo.py
"""

from __future__ import annotations

from geointerpo import Pipeline

# ------------------------------------------------------------------
# A: place-name boundary — bbox derived automatically
# ------------------------------------------------------------------
result = Pipeline(
    data="sample",                          # Step 1: synthetic data (offline)
    variable="temperature",
    date="2024-07-15",
    boundary="Calgary, Alberta, Canada",    # Step 2: Nominatim polygon (needs network)
    method=["idw", "kriging", "spline"],    # Step 3: compare three methods
    method_params={
        "kriging": {"variogram_model": "spherical"},
    },
    resolution=0.05,
    padding_deg=0.2,
).run()

print("\nCross-validation metrics:")
print(result.metrics_table())
result.save("outputs/calgary")


# ------------------------------------------------------------------
# B: CSV file + polygon file (fully offline after file download)
# ------------------------------------------------------------------
# result = Pipeline(
#     data="data/calgary_stations.csv",     # Step 1: your CSV
#     value_col="temperature",
#     boundary="data/calgary_boundary.geojson",  # Step 2: polygon file
#     method="kriging",                     # Step 3: method
#     resolution=0.05,
# ).run()


# ------------------------------------------------------------------
# C: 4-corner bbox instead of a polygon
# ------------------------------------------------------------------
# result = Pipeline(
#     data="meteostat",                    # Step 1: live API (needs network)
#     variable="temperature",
#     date="2024-07-15",
#     boundary=(-114.5, 50.8, -113.8, 51.3),  # Step 2: four corners
#     method="kriging",                    # Step 3: method
# ).run()
