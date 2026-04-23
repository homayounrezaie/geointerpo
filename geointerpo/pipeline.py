"""High-level interpolation pipeline — ArcGIS Spatial Analyst style.

Mirrors the ArcGIS workflow:
  1. Define study area  →  location / bbox
  2. Load point data    →  source + variable
  3. (Optional) DEM     →  elevation covariate
  4. Select method(s)   →  method
  5. Set output params  →  resolution, search_radius
  6. Run → get grid + metrics + interactive map

Quick start
-----------
    from geointerpo import Pipeline

    result = Pipeline(
        location="Tehran, Iran",
        variable="temperature",
        date="2024-07-15",
        method="kriging",
    ).run()

    result.plot()               # matplotlib comparison figure
    result.plot_interactive()   # interactive plotly/leafmap map
    result.save("outputs/")
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
import numpy as np
import xarray as xr
import geopandas as gpd


# ---------------------------------------------------------------------------
# ArcGIS-style search radius specification
# ---------------------------------------------------------------------------

@dataclass
class SearchRadius:
    """Mirror of ArcGIS SearchRadius parameter.

    type:     'variable' — use n nearest points (ArcGIS default: 12).
              'fixed'    — all points within distance_m metres.
    n:        number of neighbours for 'variable' type.
    distance_m: max distance in metres for 'fixed' type.
    """
    type: str = "variable"
    n: int = 12
    distance_m: float | None = None

    def __post_init__(self) -> None:
        if self.type not in {"variable", "fixed"}:
            raise ValueError("SearchRadius.type must be 'variable' or 'fixed'")
        if self.type == "variable" and self.n < 1:
            raise ValueError("SearchRadius.variable(n=...) requires n >= 1")
        if self.type == "fixed":
            if self.distance_m is None or self.distance_m <= 0:
                raise ValueError(
                    "SearchRadius.fixed(distance_m=...) requires a positive distance"
                )

    @classmethod
    def variable(cls, n: int = 12) -> "SearchRadius":
        return cls(type="variable", n=n)

    @classmethod
    def fixed(cls, distance_m: float) -> "SearchRadius":
        return cls(type="fixed", distance_m=distance_m)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class InterpolationResult:
    """Holds every output from a Pipeline.run() call."""

    grid: xr.DataArray                               # primary interpolated surface
    stations: gpd.GeoDataFrame                       # input point data
    dem: xr.DataArray | None = None                  # elevation grid (if requested)
    grids: dict[str, xr.DataArray] = field(default_factory=dict)           # all methods
    variance_grids: dict[str, xr.DataArray] = field(default_factory=dict)  # kriging/SGS variance
    cv_metrics: dict[str, dict] = field(default_factory=dict)              # per-method CV
    boundary: gpd.GeoDataFrame | None = None         # study-area boundary
    method: str = "kriging"
    variable: str = "value"
    bbox: tuple = ()
    resolution_deg: float = 0.25

    # ------------------------------------------------------------------

    def boundary_polygon(self):
        """Return the Shapely geometry of the study-area boundary, or None."""
        if self.boundary is not None:
            return self.boundary.geometry.iloc[0]
        return None

    def plot(self, **kwargs):
        """Side-by-side comparison of all interpolated methods."""
        from geointerpo import viz
        import matplotlib.pyplot as plt

        if len(self.grids) > 1:
            fig = viz.plot_comparison(
                list(self.grids.values()),
                list(self.grids.keys()),
                stations=self.stations,
                boundary=self.boundary,
                **kwargs,
            )
        else:
            fig = viz.plot_interpolated(
                self.grid, stations=self.stations, boundary=self.boundary, **kwargs
            )
        backend = plt.get_backend().lower()
        if "agg" not in backend:
            plt.show()
        return fig

    def plot_interactive(self, backend: str = "auto", **kwargs):
        """Interactive map using plotly (default) or leafmap.

        Parameters
        ----------
        backend: 'plotly' | 'leafmap' | 'auto' (auto-detects installed backend)
        """
        from geointerpo.viz_interactive import plot_interactive
        return plot_interactive(
            self.grid,
            stations=self.stations,
            boundary=self.boundary,
            backend=backend,
            title=self.variable,
            **kwargs,
        )

    def metrics_table(self):
        """Return cross-validation metrics as a pandas DataFrame."""
        import pandas as pd
        return pd.DataFrame(self.cv_metrics).T.drop(columns=["n"], errors="ignore").round(3)

    def best_method(self, by: str = "rmse") -> str:
        """Return the name of the best-performing method based on CV metrics.

        Parameters
        ----------
        by: metric to rank by — 'rmse' (default), 'mae', 'bias', or 'r'.
            For 'r', higher is better; for all others, lower is better.
        """
        if not self.cv_metrics:
            raise RuntimeError("No CV metrics available — run with cv_folds > 0.")
        ascending = by != "r"
        table = self.metrics_table()
        if by not in table.columns:
            raise ValueError(f"Metric '{by}' not found. Available: {list(table.columns)}")
        return table.sort_values(by, ascending=ascending).index[0]

    def rank_methods(self, by: str = "rmse"):
        """Return a ranked DataFrame of methods by CV metric.

        Parameters
        ----------
        by: metric to rank by — 'rmse' (default), 'mae', 'bias', or 'r'.
        """
        if not self.cv_metrics:
            raise RuntimeError("No CV metrics available — run with cv_folds > 0.")
        ascending = by != "r"
        table = self.metrics_table()
        if by not in table.columns:
            raise ValueError(f"Metric '{by}' not found. Available: {list(table.columns)}")
        ranked = table.sort_values(by, ascending=ascending).copy()
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        return ranked

    def save(self, output_dir: str | pathlib.Path = "outputs", geotiff: bool = True,
             netcdf: bool = False, plot: bool = True):
        """Save grid(s), metrics CSV, and optional plot to output_dir."""
        from geointerpo.io import export_geotiff, export_netcdf
        out = pathlib.Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for name, da in self.grids.items():
            safe = name.replace(" ", "_").lower()
            if geotiff:
                export_geotiff(da, out / f"{safe}.tif")
            if netcdf:
                export_netcdf(da, out / f"{safe}.nc")

        # Save variance grids if present
        for name, da in self.variance_grids.items():
            safe = name.replace(" ", "_").lower()
            if geotiff:
                try:
                    export_geotiff(da, out / f"{safe}_variance.tif")
                except Exception:
                    pass

        self.metrics_table().to_csv(out / "cv_metrics.csv")

        if plot:
            import matplotlib.pyplot as plt
            fig = self.plot()
            fig.savefig(out / "interpolation_comparison.png", dpi=150, bbox_inches="tight")
            plt.close(fig)


# ---------------------------------------------------------------------------
# Method registry — string → class name
# ---------------------------------------------------------------------------

_METHOD_ALIASES: dict[str, str] = {
    # ArcGIS tool names
    "idw":              "IDWInterpolator",
    "kriging":          "KrigingInterpolator",
    "ok":               "KrigingInterpolator",
    "ordinary_kriging": "KrigingInterpolator",
    "uk":               "KrigingInterpolator",
    "universal_kriging":"KrigingInterpolator",
    "natural_neighbor": "NaturalNeighborInterpolator",
    "nn":               "NaturalNeighborInterpolator",
    "spline":           "SplineInterpolator",
    "spline_regularized": "SplineInterpolator",
    "spline_tension":   "SplineInterpolator",
    "trend":            "TrendInterpolator",
    # Additional
    "rbf":              "RBFInterpolator",
    "nearest":          "GridDataInterpolator",
    "linear":           "GridDataInterpolator",
    "cubic":            "GridDataInterpolator",
    "gp":               "MLInterpolator",
    "gaussian_process": "MLInterpolator",
    "rf":               "MLInterpolator",
    "random_forest":    "MLInterpolator",
    "gbm":              "MLInterpolator",
    "gradient_boosting":"MLInterpolator",
    "rk":               "RegressionKrigingInterpolator",
    "regression_kriging":"RegressionKrigingInterpolator",
    # Geostatistical — new
    "cokriging":        "CokrigingInterpolator",
    "ked":              "CokrigingInterpolator",
    "sgs":              "SGSInterpolator",
    "simulation":       "SGSInterpolator",
}

_METHOD_DEFAULTS: dict[str, dict] = {
    "uk":               {"mode": "universal"},
    "universal_kriging":{"mode": "universal"},
    "spline_tension":   {"spline_type": "tension"},
    "nearest":          {"method": "nearest"},
    "linear":           {"method": "linear"},
    "cubic":            {"method": "cubic"},
    "gp":               {"method": "gp"},
    "gaussian_process": {"method": "gp"},
    "rf":               {"method": "rf"},
    "random_forest":    {"method": "rf"},
    "gbm":              {"method": "gbm"},
    "gradient_boosting":{"method": "gbm"},
}

ALL_METHODS = sorted(_METHOD_ALIASES)


def _build_model(
    method_key: str,
    extra_params: dict,
    covariates_fn=None,
    search_radius: SearchRadius | None = None,
):
    import importlib

    key = method_key.lower()
    cls_name = _METHOD_ALIASES.get(key)
    if cls_name is None:
        raise ValueError(f"Unknown method '{method_key}'. Available: {ALL_METHODS}")

    mod_map = {
        "IDWInterpolator":              "geointerpo.interpolators.idw",
        "RBFInterpolator":              "geointerpo.interpolators.rbf",
        "KrigingInterpolator":          "geointerpo.interpolators.kriging",
        "MLInterpolator":               "geointerpo.interpolators.ml",
        "GridDataInterpolator":         "geointerpo.interpolators.griddata",
        "NaturalNeighborInterpolator":  "geointerpo.interpolators.natural_neighbor",
        "SplineInterpolator":           "geointerpo.interpolators.spline",
        "TrendInterpolator":            "geointerpo.interpolators.trend",
        "RegressionKrigingInterpolator":"geointerpo.interpolators.regression_kriging",
        "CokrigingInterpolator":        "geointerpo.interpolators.cokriging",
        "SGSInterpolator":              "geointerpo.interpolators.sgs",
    }
    cls = getattr(importlib.import_module(mod_map[cls_name]), cls_name)
    params = dict(_METHOD_DEFAULTS.get(key, {}))

    # For MLInterpolator, route model-specific kwargs into model_params
    if cls_name == "MLInterpolator":
        ml_keys = {"n_estimators", "max_depth", "learning_rate",
                   "n_restarts_optimizer", "alpha"}
        ml_params = {k: v for k, v in extra_params.items() if k in ml_keys}
        base_params = {k: v for k, v in extra_params.items() if k not in ml_keys}
        if ml_params:
            base_params["model_params"] = ml_params
        params.update(base_params)
    else:
        params.update(extra_params)

    # Inject covariates_fn for methods that support it
    if covariates_fn is not None and cls_name in (
        "MLInterpolator", "RegressionKrigingInterpolator", "CokrigingInterpolator"
    ):
        params["covariates_fn"] = covariates_fn

    if search_radius is not None:
        params.setdefault("search_radius", search_radius)

    return cls(**params)


# ---------------------------------------------------------------------------
# Resolution parsing helper
# ---------------------------------------------------------------------------

def _parse_resolution(resolution) -> float:
    """Accept degrees (float) or a km string like '5km' or '500m'."""
    if isinstance(resolution, (int, float)):
        return float(resolution)
    if isinstance(resolution, str):
        s = resolution.strip().lower()
        if s.endswith("km"):
            km = float(s[:-2])
            return km / 111.0  # 1° ≈ 111 km at equator
        if s.endswith("m"):
            m = float(s[:-1])
            return m / 111_000.0
        # Bare number string
        return float(s)
    raise TypeError(f"resolution must be a float or string like '5km', got {type(resolution)}")


# ---------------------------------------------------------------------------
# Main Pipeline class
# ---------------------------------------------------------------------------

class Pipeline:
    """Three-step spatial interpolation pipeline.

    Step 1 — Point data (``data``)
    --------------------------------
    Pass the data you want to interpolate.  Three options:

    * **File path** (str or Path)
      - CSV with lat/lon/value columns  → ``data="stations.csv"``
      - Geo file (.shp / .geojson / .gpkg / .zip)  → ``data="stations.shp"``
    * **GeoDataFrame** already in memory  → ``data=my_gdf``
    * **API source string** — fetches live station data:
      ``"meteostat"`` · ``"openaq"`` · ``"openmeteo"`` · ``"era5"`` ·
      ``"nasapower"`` · ``"sample"`` (offline)
      Combine with ``variable`` and ``date`` to select what is fetched.

    Step 2 — Boundary (``boundary``)
    ----------------------------------
    Define the study area.  All output grids are clipped to this boundary.

    Step 3 — Methods (``method`` + ``method_params``)
    ---------------------------------------------------
    One method or a list for side-by-side comparison:
    ``"idw"`` · ``"kriging"`` · ``"spline"`` · ``"rbf"`` · ``"natural_neighbor"``
    ``"trend"`` · ``"gp"`` · ``"rf"`` · ``"gbm"`` · ``"rk"`` ·
    ``"cokriging"`` · ``"sgs"`` · and more.

    Other parameters
    -----------------
    resolution : float or str
        Grid cell size — float in degrees (default ``0.25``) **or** a string
        like ``"5km"`` or ``"500m"`` for metric units.
    """

    def __init__(
        self,
        data=None,
        boundary=None,
        method: str | list[str] = "kriging",
        # --- data options ---
        variable: str = "value",
        date: str | None = None,
        lon_col: str = "lon",
        lat_col: str = "lat",
        value_col: str = "value",
        # --- grid options ---
        resolution: float | str = 0.25,
        padding_deg: float = 0.5,
        # --- method options ---
        method_params: dict | None = None,
        # --- boundary options ---
        boundary_provider: str = "nominatim",
        clip_to_boundary: bool = True,
        # --- advanced ---
        include_dem: bool = False,
        dem_source: str = "auto",
        cv_folds: int = 5,
        search_radius: SearchRadius | None = None,
        openaq_api_key: str | None = None,
        # --- backward-compat aliases ---
        source: str | None = None,
        location=None,
    ):
        if data is None and source is None and location is None and boundary is None:
            raise ValueError(
                "Provide at least one of: data=, source=, location=, or boundary=."
            )
        self.data = data
        self.boundary = boundary
        self.methods = [method] if isinstance(method, str) else list(method)
        self.variable = variable
        self.date = date or _yesterday()
        self.lon_col = lon_col
        self.lat_col = lat_col
        self.value_col = value_col
        self.resolution = _parse_resolution(resolution)
        self.padding_deg = padding_deg
        self.method_params = method_params or {}
        self.boundary_provider = boundary_provider
        self.clip_to_boundary = clip_to_boundary
        self.include_dem = include_dem
        self.dem_source = dem_source
        self.cv_folds = cv_folds
        self.search_radius = search_radius
        self.openaq_api_key = openaq_api_key
        self._source = source
        self._location = location

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> InterpolationResult:
        """Execute the full pipeline and return an InterpolationResult."""

        print("[1/5] Resolving boundary…")
        boundary_gdf = self._resolve_boundary()

        print(f"[2/5] Loading point data…")
        gdf = self._load_data(boundary_gdf)
        print(f"      {len(gdf)} points loaded")

        bbox = self._resolve_bbox(boundary_gdf, gdf)
        print(f"      bbox = {tuple(round(v, 4) for v in bbox)}")

        dem = None
        covariates_fn = None
        if self.include_dem:
            print(f"[3/5] Fetching DEM ({self.dem_source})…")
            from geointerpo.covariate import fetch_dem, make_covariate_fn
            dem = fetch_dem(bbox, resolution=self.resolution, source=self.dem_source)
            covariates_fn = make_covariate_fn(dem)
            print(f"      DEM shape = {dem.shape}, source = {dem.attrs.get('source')}")
        else:
            print("[3/5] Skipping DEM")

        print(f"[4/5] Interpolating with: {', '.join(self.methods)}")
        grids, variance_grids, cv_metrics = self._interpolate(gdf, bbox, covariates_fn)

        if boundary_gdf is not None and self.clip_to_boundary:
            grids = self._clip_grids(grids, boundary_gdf)

        primary = grids[self.methods[0]]
        result = InterpolationResult(
            grid=primary,
            stations=gdf,
            dem=dem,
            grids=grids,
            variance_grids=variance_grids,
            cv_metrics=cv_metrics,
            boundary=boundary_gdf,
            method=self.methods[0],
            variable=self.variable,
            bbox=bbox,
            resolution_deg=self.resolution,
        )

        if cv_metrics:
            best = result.best_method()
            print(f"\n[5/5] Best method by RMSE: {best}")
            ranked = result.rank_methods()
            print(ranked.to_string())

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_boundary(self) -> gpd.GeoDataFrame | None:
        if self.boundary is None:
            return None
        from geointerpo.boundaries import load_boundary
        return load_boundary(self.boundary, provider=self.boundary_provider)

    def _resolve_bbox(
        self,
        boundary_gdf: gpd.GeoDataFrame | None,
        gdf: gpd.GeoDataFrame,
    ) -> tuple:
        p = self.padding_deg

        if boundary_gdf is not None:
            from geointerpo.boundaries import boundary_bbox
            mn_lon, mn_lat, mx_lon, mx_lat = boundary_bbox(boundary_gdf)
            return (mn_lon - p, mn_lat - p, mx_lon + p, mx_lat + p)

        if self._location is not None:
            return self._geocode_location(self._location)

        mn_lon = float(gdf.geometry.x.min())
        mn_lat = float(gdf.geometry.y.min())
        mx_lon = float(gdf.geometry.x.max())
        mx_lat = float(gdf.geometry.y.max())
        return (mn_lon - p, mn_lat - p, mx_lon + p, mx_lat + p)

    def _geocode_location(self, location) -> tuple:
        if isinstance(location, (list, tuple)) and len(location) == 4:
            return tuple(float(v) for v in location)
        try:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter
        except ImportError as e:
            raise ImportError(
                "Install geopy for named-location support: pip install geopy"
            ) from e
        geolocator = Nominatim(user_agent="geointerpo/0.1")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        loc = geocode(str(location), exactly_one=True, timeout=15)
        if loc is None:
            raise ValueError(f"Could not geocode location '{location}'")
        raw = loc.raw
        p = self.padding_deg
        if "boundingbox" in raw:
            s, n, w, e = [float(x) for x in raw["boundingbox"]]
            return (w - p, s - p, e + p, n + p)
        lat, lon = loc.latitude, loc.longitude
        return (lon - p, lat - p, lon + p, lat + p)

    _API_SOURCES = frozenset(
        {"auto", "sample", "meteostat", "openaq", "openmeteo", "era5", "nasapower"}
    )

    def _load_data(self, boundary_gdf: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
        import pathlib

        d = self.data

        if isinstance(d, gpd.GeoDataFrame):
            return _ensure_value_col(d, self.value_col)

        if isinstance(d, str) and d.lower() in self._API_SOURCES:
            src = d.lower()
        elif d is None and self._source is not None and self._source.lower() in self._API_SOURCES:
            src = self._source.lower()
        elif isinstance(d, (str, pathlib.Path)):
            p = pathlib.Path(d)
            if not p.exists():
                raise FileNotFoundError(f"Data file not found: {p}")
            suffix = p.suffix.lower()
            if suffix == ".csv":
                return _load_csv(p, self.lon_col, self.lat_col, self.value_col)
            if suffix in (".shp", ".geojson", ".json", ".gpkg", ".zip"):
                return _load_geo_file(p, self.value_col)
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                "Supported: .csv, .shp, .geojson, .gpkg, .zip"
            )
        else:
            src = "auto"

        src = (src or self._source or "auto").lower()
        var = self.variable.lower()
        fetch_bbox = self._api_fetch_bbox(boundary_gdf)

        if src == "auto":
            if var in ("pm25", "pm10", "no2", "o3", "so2", "co"):
                src = "openaq"
            elif var in ("temperature", "precipitation", "tavg", "tmin", "tmax", "prcp"):
                src = "meteostat"
            else:
                src = "openmeteo"

        if src == "sample":
            from geointerpo.data.samples import (
                load_temperature, load_precipitation, load_air_quality,
            )
            fn = {
                "temperature": load_temperature,
                "precipitation": load_precipitation,
                "air_quality": load_air_quality,
                "pm25": load_air_quality,
            }.get(var, load_temperature)
            if boundary_gdf is None and self._location is None:
                return fn()
            return fn(bbox=fetch_bbox)

        if src == "meteostat":
            from geointerpo.sources.meteostat import MeteostatSource
            col = {"temperature": "tavg", "precipitation": "prcp"}.get(var, var)
            return MeteostatSource(variable=col, start=self.date, end=self.date).fetch(fetch_bbox)

        if src == "openaq":
            from geointerpo.sources.openaq import OpenAQSource
            return OpenAQSource(
                parameter=var, date_from=self.date, date_to=self.date,
                api_key=self.openaq_api_key,
            ).fetch(fetch_bbox)

        if src == "openmeteo":
            from geointerpo.sources.openmeteo import OpenMeteoSource
            col = {
                "temperature": "temperature_2m_mean",
                "precipitation": "precipitation_sum",
            }.get(var, var)
            return OpenMeteoSource(variable=col, date=self.date).fetch(fetch_bbox)

        if src == "era5":
            from geointerpo.sources.era5 import ERA5Source
            return ERA5Source(variable=var, date=self.date).fetch(fetch_bbox)

        if src == "nasapower":
            from geointerpo.sources.nasapower import NASAPowerSource
            return NASAPowerSource(variable=var, date=self.date).fetch(fetch_bbox)

        raise ValueError(
            f"Unknown data source '{src}'. "
            "Use a file path, GeoDataFrame, or one of: "
            "'meteostat', 'openaq', 'openmeteo', 'era5', 'nasapower', 'sample'."
        )

    def _api_fetch_bbox(self, boundary_gdf: gpd.GeoDataFrame | None) -> tuple:
        p = self.padding_deg
        if boundary_gdf is not None:
            from geointerpo.boundaries import boundary_bbox
            mn_lon, mn_lat, mx_lon, mx_lat = boundary_bbox(boundary_gdf)
            return (mn_lon - p, mn_lat - p, mx_lon + p, mx_lat + p)
        if self._location is not None:
            return self._geocode_location(self._location)
        return (-180.0, -90.0, 180.0, 90.0)

    def _clip_grids(
        self,
        grids: dict[str, xr.DataArray],
        boundary_gdf: gpd.GeoDataFrame,
    ) -> dict[str, xr.DataArray]:
        try:
            from geointerpo.io import clip_to_polygon
        except ImportError:
            return grids
        clipped = {}
        for name, da in grids.items():
            try:
                clipped[name] = clip_to_polygon(da, boundary_gdf)
            except Exception:
                clipped[name] = da
        return clipped

    def _interpolate(self, gdf, bbox, covariates_fn):
        grids: dict[str, xr.DataArray] = {}
        variance_grids: dict[str, xr.DataArray] = {}
        cv: dict[str, dict] = {}

        for method_key in self.methods:
            extra = {}
            if isinstance(self.method_params, dict) and self.method_params:
                is_nested = any(isinstance(v, dict) for v in self.method_params.values())
                if is_nested:
                    extra = self.method_params.get(method_key, {})
                else:
                    extra = self.method_params

            try:
                model = _build_model(
                    method_key,
                    extra,
                    covariates_fn=covariates_fn,
                    search_radius=self.search_radius,
                )
                model.fit(gdf)

                # Collect variance surface where available (Kriging, SGS, Cokriging)
                if hasattr(model, "predict_with_variance"):
                    mean_da, var_da = model.predict_with_variance(bbox, resolution=self.resolution)
                    grids[method_key] = mean_da
                    variance_grids[method_key] = var_da
                else:
                    grids[method_key] = model.predict(bbox, resolution=self.resolution)

                if self.cv_folds > 0:
                    cv[method_key] = model.cross_validate(gdf, k=self.cv_folds)
                    m = cv[method_key]
                    print(f"      {method_key:25s}  RMSE={m['rmse']:.3f}  r={m['r']:.4f}")
                else:
                    print(f"      {method_key:25s}  (no CV)")
            except Exception as exc:
                print(f"      {method_key:25s}  SKIPPED ({type(exc).__name__}: {exc})")

        return grids, variance_grids, cv


# ---------------------------------------------------------------------------
# File-loading helpers
# ---------------------------------------------------------------------------

def _load_csv(
    path,
    lon_col: str = "lon",
    lat_col: str = "lat",
    value_col: str = "value",
) -> gpd.GeoDataFrame:
    import pandas as pd
    from shapely.geometry import Point

    df = pd.read_csv(path)

    lon_candidates = [lon_col, "longitude", "x", "X", "Longitude", "LON"]
    lat_candidates = [lat_col, "latitude", "y", "Y", "Latitude", "LAT"]
    val_candidates = [value_col, "value", "val", "z", "Z"]

    col_lon = next((c for c in lon_candidates if c in df.columns), None)
    col_lat = next((c for c in lat_candidates if c in df.columns), None)
    col_val = next((c for c in val_candidates if c in df.columns), None)

    if col_lon is None or col_lat is None:
        raise ValueError(
            f"CSV '{path}' must have longitude and latitude columns. "
            f"Found columns: {list(df.columns)}. "
            f"Expected names like: {lon_candidates[:3]} / {lat_candidates[:3]}"
        )
    if col_val is None:
        raise ValueError(
            f"CSV '{path}' must have a value column. "
            f"Found columns: {list(df.columns)}. "
            f"Expected names like: {val_candidates}"
        )

    df = df.dropna(subset=[col_lon, col_lat, col_val])
    gdf = gpd.GeoDataFrame(
        {"value": df[col_val].values},
        geometry=[Point(lon, lat) for lon, lat in zip(df[col_lon], df[col_lat])],
        crs="EPSG:4326",
    )
    return gdf


def _load_geo_file(path, value_col: str = "value") -> gpd.GeoDataFrame:
    import pathlib

    p = pathlib.Path(path)
    if p.suffix.lower() == ".zip":
        gdf = gpd.read_file(f"zip://{p}")
    else:
        gdf = gpd.read_file(p)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    return _ensure_value_col(gdf, value_col)


def _ensure_value_col(gdf: gpd.GeoDataFrame, value_col: str) -> gpd.GeoDataFrame:
    """Rename value_col → 'value' if needed; raise if column is missing."""
    if "value" in gdf.columns:
        return gdf
    if value_col in gdf.columns and value_col != "value":
        return gdf.rename(columns={value_col: "value"})
    for alias in ("val", "z", "Z", "data"):
        if alias in gdf.columns:
            return gdf.rename(columns={alias: "value"})
    raise ValueError(
        f"Could not find a value column in the data. "
        f"Columns present: {list(gdf.columns)}. "
        f"Set value_col= to the correct column name."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _yesterday() -> str:
    import pandas as pd
    return (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
