"""CLI entry point.

Usage
-----
    geointerpo run configs/temperature.yml
    geointerpo demo temperature
    geointerpo benchmark
"""

from __future__ import annotations

import argparse
import sys


def _cmd_run(args):
    import yaml
    import pathlib

    cfg_path = pathlib.Path(args.config)
    if not cfg_path.exists():
        print(f"Config file not found: {cfg_path}")
        sys.exit(1)

    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    _run_from_config(cfg)


def _run_from_config(cfg: dict):
    import geopandas as gpd
    import pathlib

    # --- boundary (optional) ---
    boundary_gdf = None
    boundary_cfg = cfg.get("boundary")
    if boundary_cfg:
        from geointerpo.boundaries import load_boundary, boundary_bbox
        bsrc = boundary_cfg.get("source", "place")
        provider = boundary_cfg.get("provider", "nominatim")
        padding = boundary_cfg.get("padding_deg", 0.0)
        if bsrc == "place":
            boundary_gdf = load_boundary(
                boundary_cfg["name"], provider=provider, padding_deg=padding
            )
        elif bsrc == "file":
            boundary_gdf = load_boundary(
                pathlib.Path(boundary_cfg["path"]), padding_deg=padding
            )
        elif bsrc == "bbox":
            from shapely.geometry import box
            bbox_vals = boundary_cfg["bbox"]
            geom = box(*bbox_vals)
            import geopandas as _gpd
            boundary_gdf = _gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
        else:
            print(f"Unknown boundary.source '{bsrc}'. Use 'file', 'place', or 'bbox'.")
            sys.exit(1)

    # --- bbox: from config or derived from boundary ---
    if "bbox" in cfg:
        bbox = tuple(cfg["bbox"])
    elif boundary_gdf is not None:
        from geointerpo.boundaries import boundary_bbox
        min_lon, min_lat, max_lon, max_lat = boundary_bbox(boundary_gdf)
        p = cfg.get("padding_deg", 0.5)
        bbox = (min_lon - p, min_lat - p, max_lon + p, max_lat + p)
    else:
        print("Config must include either 'bbox' or a 'boundary' section.")
        sys.exit(1)

    # --- data source ---
    source_cfg = cfg.get("source", {})
    source_type = source_cfg.get("type", "sample")

    if source_type == "sample":
        variable = source_cfg.get("variable", "temperature")
        from geointerpo import data as _data
        fn = {"temperature": _data.load_temperature,
              "precipitation": _data.load_precipitation,
              "air_quality": _data.load_air_quality}.get(variable)
        if fn is None:
            print(f"Unknown sample variable '{variable}'.")
            sys.exit(1)
        gdf = fn(bbox=bbox)
    elif source_type == "csv":
        import pandas as pd
        from shapely.geometry import Point
        df = pd.read_csv(source_cfg["path"])
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(r[source_cfg.get("lon_col", "lon")],
                            r[source_cfg.get("lat_col", "lat")])
                      for _, r in df.iterrows()],
            crs="EPSG:4326",
        )
        gdf = gdf.rename(columns={source_cfg.get("value_col", "value"): "value"})
    elif source_type == "meteostat":
        from geointerpo.sources import MeteostatSource
        gdf = MeteostatSource(**{k: v for k, v in source_cfg.items() if k != "type"}).fetch(bbox)
    elif source_type == "openaq":
        from geointerpo.sources import OpenAQSource
        gdf = OpenAQSource(**{k: v for k, v in source_cfg.items() if k != "type"}).fetch(bbox)
    elif source_type == "openmeteo":
        from geointerpo.sources import OpenMeteoSource
        gdf = OpenMeteoSource(**{k: v for k, v in source_cfg.items() if k != "type"}).fetch(bbox)
    else:
        print(f"Unknown source type '{source_type}'.")
        sys.exit(1)

    print(f"Loaded {len(gdf)} stations.")

    # --- interpolators ---
    interp_cfgs = cfg.get("interpolators", [{"method": "kriging"}])
    resolution = cfg.get("resolution", 0.25)
    grids = {}

    for icfg in interp_cfgs:
        method = icfg.get("method", "kriging").lower()
        label = icfg.get("label", method)
        params = {k: v for k, v in icfg.items() if k not in ("method", "label")}
        model = _build_interpolator(method, params)
        model.fit(gdf)
        grids[label] = model.predict(bbox, resolution=resolution)
        cv = model.cross_validate(gdf, k=cfg.get("cv_folds", 5))
        print(f"  {label:20s}  RMSE={cv['rmse']:.3f}  r={cv['r']:.4f}")

    # --- clip to boundary ---
    if boundary_gdf is not None and cfg.get("clip_to_boundary", True):
        try:
            from geointerpo.io import clip_to_polygon
            grids = {
                label: clip_to_polygon(da, boundary_gdf)
                for label, da in grids.items()
            }
            print("Grids clipped to boundary.")
        except Exception as exc:
            print(f"Warning: boundary clipping skipped ({exc})")

    # --- output ---
    output_cfg = cfg.get("output", {})
    out_dir = pathlib.Path(output_cfg.get("dir", "outputs"))
    out_dir.mkdir(exist_ok=True)

    if output_cfg.get("plot", True):
        import matplotlib.pyplot as plt
        from geointerpo import viz
        fig = viz.plot_comparison(list(grids.values()), list(grids.keys()), stations=gdf)
        fig.suptitle(cfg.get("title", "Interpolation results"), y=1.02)
        plot_path = out_dir / output_cfg.get("plot_file", "result.png")
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Plot saved: {plot_path}")

    for label, da in grids.items():
        if output_cfg.get("geotiff", False):
            from geointerpo.io import export_geotiff
            export_geotiff(da, out_dir / f"{label}.tif")
        if output_cfg.get("netcdf", False):
            da.to_netcdf(out_dir / f"{label}.nc")


def _build_interpolator(method: str, params: dict):
    method = method.lower()
    if method == "idw":
        from geointerpo.interpolators import IDWInterpolator
        return IDWInterpolator(**params)
    if method == "rbf":
        from geointerpo.interpolators import RBFInterpolator
        return RBFInterpolator(**params)
    if method in ("kriging", "ok", "uk"):
        from geointerpo.interpolators import KrigingInterpolator
        if method == "uk":
            params.setdefault("mode", "universal")
        return KrigingInterpolator(**params)
    if method in ("griddata", "nearest", "linear", "cubic"):
        from geointerpo.interpolators import GridDataInterpolator
        if method in ("nearest", "linear", "cubic"):
            params["method"] = method
        return GridDataInterpolator(**params)
    if method in ("gp", "rf", "gbm"):
        from geointerpo.interpolators import MLInterpolator
        params["method"] = method
        return MLInterpolator(**params)
    if method in ("rk", "regression_kriging"):
        from geointerpo.interpolators import RegressionKrigingInterpolator
        return RegressionKrigingInterpolator(**params)
    raise ValueError(f"Unknown interpolation method '{method}'")


def _cmd_demo(args):
    sys.argv = ["geointerpo.demo", args.topic]
    from geointerpo.demo import main
    main()


def _cmd_benchmark(args):
    sys.argv = ["geointerpo.demo", "benchmark"]
    from geointerpo.demo import main
    main()


def main():
    parser = argparse.ArgumentParser(
        prog="geointerpo",
        description="Geo interpolation toolkit",
    )
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run interpolation from a YAML config file")
    p_run.add_argument("config", help="Path to YAML config file")

    p_demo = sub.add_parser("demo", help="Run an offline demo")
    p_demo.add_argument(
        "topic",
        nargs="?",
        default="temperature",
        choices=["temperature", "precipitation", "air_quality"],
    )

    sub.add_parser("benchmark", help="Benchmark all methods on synthetic data")

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "demo":
        _cmd_demo(args)
    elif args.command == "benchmark":
        _cmd_benchmark(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
