"""Offline demo — no network or API keys required.

Usage
-----
    python -m geointerpo.demo temperature
    python -m geointerpo.demo precipitation
    python -m geointerpo.demo air_quality
    python -m geointerpo.demo benchmark    # compare all methods on temperature
"""

from __future__ import annotations

import sys
import pathlib

OUTPUTS = pathlib.Path("outputs")


def _run_temperature():
    from geointerpo.data import load_temperature
    from geointerpo.interpolators import (
        IDWInterpolator, RBFInterpolator, KrigingInterpolator,
        GridDataInterpolator, MLInterpolator,
    )
    from geointerpo import viz

    print("Loading synthetic temperature stations…")
    gdf = load_temperature()
    bbox = (5.0, 44.0, 25.0, 56.0)
    resolution = 0.25

    models = {
        "IDW":     IDWInterpolator(power=2).fit(gdf),
        "RBF":     RBFInterpolator(kernel="thin_plate_spline").fit(gdf),
        "Nearest": GridDataInterpolator(method="nearest").fit(gdf),
        "Linear":  GridDataInterpolator(method="linear").fit(gdf),
        "Kriging": KrigingInterpolator(variogram_model="spherical").fit(gdf),
    }
    grids = {name: m.predict(bbox, resolution) for name, m in models.items()}

    print("Cross-validating…")
    for name, m in models.items():
        cv = m.cross_validate(gdf, k=5)
        print(f"  {name:10s}  RMSE={cv['rmse']:.2f}  MAE={cv['mae']:.2f}  r={cv['r']:.3f}")

    import matplotlib.pyplot as plt
    fig = viz.plot_comparison(list(grids.values()), list(grids.keys()), stations=gdf)
    fig.suptitle("Synthetic temperature interpolation", y=1.02)
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "demo_temperature.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def _run_precipitation():
    from geointerpo.data import load_precipitation
    from geointerpo.interpolators import IDWInterpolator, KrigingInterpolator, RBFInterpolator
    from geointerpo import viz

    print("Loading synthetic precipitation stations…")
    gdf = load_precipitation()
    bbox = (-10.0, 35.0, 30.0, 55.0)

    models = {
        "IDW":     IDWInterpolator(power=2).fit(gdf),
        "RBF":     RBFInterpolator(smoothing=0.5).fit(gdf),
        "Kriging": KrigingInterpolator(variogram_model="exponential").fit(gdf),
    }
    grids = {name: m.predict(bbox, resolution=0.5) for name, m in models.items()}

    import matplotlib.pyplot as plt
    fig = viz.plot_comparison(list(grids.values()), list(grids.keys()),
                              stations=gdf, cmap="Blues")
    fig.suptitle("Synthetic precipitation interpolation", y=1.02)
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "demo_precipitation.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def _run_air_quality():
    from geointerpo.data import load_air_quality
    from geointerpo.interpolators import IDWInterpolator, KrigingInterpolator, MLInterpolator
    from geointerpo import viz

    print("Loading synthetic air quality stations…")
    gdf = load_air_quality()
    bbox = (68.0, 20.0, 90.0, 35.0)

    models = {
        "IDW":     IDWInterpolator(power=2).fit(gdf),
        "Kriging": KrigingInterpolator(variogram_model="spherical").fit(gdf),
        "RF":      MLInterpolator(method="rf").fit(gdf),
    }
    grids = {name: m.predict(bbox, resolution=0.5) for name, m in models.items()}

    import matplotlib.pyplot as plt
    fig = viz.plot_comparison(list(grids.values()), list(grids.keys()),
                              stations=gdf, cmap="YlOrRd")
    fig.suptitle("Synthetic PM2.5 interpolation", y=1.02)
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "demo_air_quality.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def _run_benchmark():
    from geointerpo.data import load_temperature
    from geointerpo.interpolators import (
        IDWInterpolator, RBFInterpolator, KrigingInterpolator,
        GridDataInterpolator, MLInterpolator, RegressionKrigingInterpolator,
    )
    import pandas as pd

    print("Benchmark: all methods on synthetic temperature (k=5 spatial CV)\n")
    gdf = load_temperature()
    models = {
        "IDW (p=2)":    IDWInterpolator(power=2),
        "IDW (p=3)":    IDWInterpolator(power=3),
        "RBF-TPS":      RBFInterpolator(kernel="thin_plate_spline"),
        "Nearest":      GridDataInterpolator(method="nearest"),
        "Linear":       GridDataInterpolator(method="linear"),
        "OK-Spherical": KrigingInterpolator(variogram_model="spherical"),
        "OK-Gaussian":  KrigingInterpolator(variogram_model="gaussian"),
        "RK":           RegressionKrigingInterpolator(trend_model="linear"),
        "GP":           MLInterpolator(method="gp"),
        "RF":           MLInterpolator(method="rf"),
        "GBM":          MLInterpolator(method="gbm"),
    }
    rows = []
    for name, m in models.items():
        m.fit(gdf)
        cv = m.cross_validate(gdf, k=5)
        rows.append({"Method": name, **cv})
        print(f"  {name:20s}  RMSE={cv['rmse']:.3f}  MAE={cv['mae']:.3f}  r={cv['r']:.4f}")

    df = pd.DataFrame(rows).set_index("Method").drop(columns=["n"])
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "benchmark_results.csv"
    df.to_csv(out)
    print(f"\nResults saved: {out}")


_DEMOS = {
    "temperature": _run_temperature,
    "precipitation": _run_precipitation,
    "air_quality": _run_air_quality,
    "benchmark": _run_benchmark,
}


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "temperature"
    fn = _DEMOS.get(topic)
    if fn is None:
        print(f"Unknown demo '{topic}'. Options: {', '.join(_DEMOS)}")
        sys.exit(1)
    fn()


if __name__ == "__main__":
    main()
