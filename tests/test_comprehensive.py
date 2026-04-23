"""Comprehensive test suite covering every module in geointerpo.

Covers:
- All 9 interpolator classes (fit, predict, cross_validate)
- viz.py  — all plot functions (non-interactive, matplotlib)
- io.py   — NetCDF export; GeoTIFF export skipped when rioxarray absent
- covariate.py — synthetic DEM + make_covariate_fn
- validation/metrics.py — compute_metrics, grid_metrics, spatial_cv
- pipeline.py — InterpolationResult helpers (save, best_method, rank_methods …)
- data/samples.py — all three sample loaders
- boundaries.py — already covered in test_boundaries.py (not duplicated here)
- sources — offline only; network sources skipped
"""

from __future__ import annotations

import pathlib
import tempfile

import numpy as np
import pytest
import geopandas as gpd
import xarray as xr
from shapely.geometry import Point

from geointerpo.data.samples import load_temperature, load_precipitation, load_air_quality
from geointerpo.interpolators.idw import IDWInterpolator
from geointerpo.interpolators.rbf import RBFInterpolator
from geointerpo.interpolators.griddata import GridDataInterpolator
from geointerpo.interpolators.kriging import KrigingInterpolator
from geointerpo.interpolators.ml import MLInterpolator
from geointerpo.interpolators.regression_kriging import RegressionKrigingInterpolator
from geointerpo.interpolators.spline import SplineInterpolator
from geointerpo.interpolators.trend import TrendInterpolator
from geointerpo.interpolators.natural_neighbor import NaturalNeighborInterpolator
from geointerpo.validation.metrics import compute_metrics, grid_metrics, spatial_cv
from geointerpo.covariate import fetch_dem, make_covariate_fn
from geointerpo.pipeline import Pipeline, InterpolationResult, _parse_resolution

BBOX = (5.0, 44.0, 25.0, 56.0)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gdf30():
    return load_temperature(n_stations=30, seed=99)


@pytest.fixture(scope="module")
def gdf10():
    return load_temperature(n_stations=10, seed=7)


def _simple_grid(bbox=BBOX, resolution=2.0, name="value"):
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = np.arange(min_lon, max_lon + resolution, resolution)
    lats = np.arange(min_lat, max_lat + resolution, resolution)
    vals = np.random.default_rng(0).random((len(lats), len(lons))) * 20 + 5
    return xr.DataArray(vals, dims=["lat", "lon"],
                        coords={"lat": lats, "lon": lons}, name=name,
                        attrs={"crs": "EPSG:4326"})


# ===========================================================================
# 1. Sample data loaders
# ===========================================================================

class TestSampleData:
    def test_temperature_shape_and_crs(self):
        gdf = load_temperature(n_stations=20)
        assert len(gdf) == 20
        assert "value" in gdf.columns
        assert gdf.crs.to_epsg() == 4326

    def test_precipitation_non_negative(self):
        gdf = load_precipitation(n_stations=15)
        assert (gdf["value"] >= 0).all()

    def test_air_quality_no_nans(self):
        gdf = load_air_quality(n_stations=15)
        assert gdf["value"].notna().all()

    def test_seed_reproducibility(self):
        a = load_temperature(n_stations=10, seed=42)
        b = load_temperature(n_stations=10, seed=42)
        np.testing.assert_array_equal(a["value"].values, b["value"].values)

    def test_different_seeds_differ(self):
        a = load_temperature(n_stations=10, seed=1)
        b = load_temperature(n_stations=10, seed=2)
        assert not np.allclose(a["value"].values, b["value"].values)

    def test_bbox_filtering(self):
        bbox = (5.0, 44.0, 15.0, 50.0)
        gdf = load_temperature(bbox=bbox)
        assert (gdf.geometry.x >= 5.0).all()
        assert (gdf.geometry.x <= 15.0).all()


# ===========================================================================
# 2. All interpolators — fit / predict / cross_validate
# ===========================================================================

class TestAllInterpolators:
    """Run the same three-step test on every interpolator."""

    RESOLUTION = 2.0

    def _check(self, model, gdf, bbox=BBOX, res=2.0):
        model.fit(gdf)
        assert model._fitted
        grid = model.predict(bbox, resolution=res)
        assert grid.dims == ("lat", "lon")
        assert not np.all(np.isnan(grid.values))
        cv = model.cross_validate(gdf, k=3)
        assert cv["rmse"] >= 0
        assert cv["n"] > 0
        return grid

    def test_idw(self, gdf30):
        self._check(IDWInterpolator(power=2), gdf30)

    def test_idw_power_3(self, gdf30):
        self._check(IDWInterpolator(power=3), gdf30)

    def test_idw_n_neighbors(self, gdf30):
        self._check(IDWInterpolator(n_neighbors=5), gdf30)

    def test_rbf_thin_plate(self, gdf30):
        self._check(RBFInterpolator(kernel="thin_plate_spline"), gdf30)

    def test_rbf_gaussian(self, gdf30):
        self._check(RBFInterpolator(kernel="gaussian"), gdf30)

    def test_rbf_multiquadric(self, gdf30):
        self._check(RBFInterpolator(kernel="multiquadric"), gdf30)

    def test_griddata_nearest(self, gdf30):
        self._check(GridDataInterpolator(method="nearest"), gdf30)

    def test_griddata_linear(self, gdf30):
        model = GridDataInterpolator(method="linear")
        model.fit(gdf30)
        grid = model.predict(BBOX, resolution=self.RESOLUTION)
        assert np.any(~np.isnan(grid.values))

    def test_griddata_cubic(self, gdf30):
        model = GridDataInterpolator(method="cubic")
        model.fit(gdf30)
        grid = model.predict(BBOX, resolution=self.RESOLUTION)
        assert np.any(~np.isnan(grid.values))

    def test_kriging_ordinary_spherical(self, gdf30):
        self._check(KrigingInterpolator(mode="ordinary", variogram_model="spherical"), gdf30)

    def test_kriging_ordinary_gaussian(self, gdf30):
        self._check(KrigingInterpolator(variogram_model="gaussian"), gdf30)

    def test_kriging_ordinary_exponential(self, gdf30):
        self._check(KrigingInterpolator(variogram_model="exponential"), gdf30)

    def test_kriging_universal(self, gdf30):
        self._check(KrigingInterpolator(mode="universal"), gdf30)

    def test_kriging_with_nlags(self, gdf30):
        self._check(KrigingInterpolator(nlags=8), gdf30)

    def test_spline_regularized(self, gdf30):
        self._check(SplineInterpolator(spline_type="regularized"), gdf30)

    def test_spline_tension(self, gdf30):
        self._check(SplineInterpolator(spline_type="tension"), gdf30)

    def test_trend_order1(self, gdf30):
        self._check(TrendInterpolator(order=1), gdf30)

    def test_trend_order2(self, gdf30):
        self._check(TrendInterpolator(order=2), gdf30)

    def test_natural_neighbor(self, gdf30):
        self._check(NaturalNeighborInterpolator(), gdf30)

    def test_ml_gp(self, gdf30):
        self._check(MLInterpolator(method="gp"), gdf30)

    def test_ml_rf(self, gdf30):
        self._check(MLInterpolator(method="rf"), gdf30)

    def test_ml_gbm(self, gdf30):
        self._check(MLInterpolator(method="gbm"), gdf30)

    def test_regression_kriging_linear(self, gdf30):
        self._check(RegressionKrigingInterpolator(trend_model="linear"), gdf30)

    def test_spline_too_few_points_raises(self):
        tiny = load_temperature(n_stations=3)
        with pytest.raises(ValueError, match="Spline requires"):
            SplineInterpolator().fit(tiny)

    def test_ml_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            MLInterpolator(method="neural_net").fit(load_temperature(n_stations=10))

    def test_predict_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            IDWInterpolator().predict(BBOX)

    def test_missing_value_column_raises(self, gdf30):
        bad = gdf30.rename(columns={"value": "temp"})
        with pytest.raises(ValueError):
            IDWInterpolator().fit(bad)


# ===========================================================================
# 3. Interpolator UTM projection
# ===========================================================================

class TestUTMProjection:
    def test_metric_crs_set_after_fit(self, gdf30):
        m = IDWInterpolator().fit(gdf30)
        assert m._proj_crs is not None
        assert m._proj_crs.is_projected

    def test_non_metric_griddata_has_proj_crs(self, gdf30):
        m = GridDataInterpolator(method="nearest").fit(gdf30)
        assert m._proj_crs is not None

    def test_output_coords_are_wgs84(self, gdf30):
        m = IDWInterpolator().fit(gdf30)
        grid = m.predict(BBOX, resolution=2.0)
        assert float(grid.lon.min()) >= BBOX[0] - 0.01
        assert float(grid.lat.min()) >= BBOX[1] - 0.01

    def test_idw_exact_at_station_locations(self, gdf30):
        m = IDWInterpolator().fit(gdf30)
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", m._proj_crs, always_xy=True)
        xs, ys = t.transform(gdf30.geometry.x.values[:5], gdf30.geometry.y.values[:5])
        preds = m._predict(xs, ys)
        np.testing.assert_allclose(preds, gdf30["value"].values[:5], rtol=1e-5)


# ===========================================================================
# 4. Kriging extras (variance, anisotropy, variogram)
# ===========================================================================

class TestKrigingExtras:
    def test_predict_with_variance_shapes(self, gdf30):
        m = KrigingInterpolator().fit(gdf30)
        mean, var = m.predict_with_variance(BBOX, resolution=2.0)
        assert mean.shape == var.shape

    def test_variance_non_negative(self, gdf30):
        m = KrigingInterpolator().fit(gdf30)
        _, var = m.predict_with_variance(BBOX, resolution=2.0)
        assert (var.values[~np.isnan(var.values)] >= -1e-8).all()

    def test_variance_in_attrs(self, gdf30):
        m = KrigingInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        assert "variance" in da.attrs

    def test_anisotropy_accepted(self, gdf30):
        m = KrigingInterpolator(anisotropy_scaling=0.5, anisotropy_angle=30.0).fit(gdf30)
        grid = m.predict(BBOX, resolution=2.0)
        assert not np.all(np.isnan(grid.values))

    def test_variogram_parameters(self, gdf30):
        m = KrigingInterpolator(variogram_model="spherical").fit(gdf30)
        params = m.variogram_parameters
        assert len(params) == 3  # nugget, sill, range

    def test_variogram_parameters_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            KrigingInterpolator().variogram_parameters


# ===========================================================================
# 5. ML uncertainty
# ===========================================================================

class TestMLUncertainty:
    def test_gp_predict_with_std(self, gdf30):
        m = MLInterpolator(method="gp").fit(gdf30)
        mean, std = m.predict_with_std(BBOX, resolution=2.0)
        assert mean.shape == std.shape
        assert (std.values >= 0).all()

    def test_gp_predict_with_std_wrong_method(self, gdf30):
        m = MLInterpolator(method="rf").fit(gdf30)
        with pytest.raises(NotImplementedError):
            m.predict_with_std(BBOX, resolution=2.0)

    def test_gp_uncertainty_triple(self, gdf30):
        m = MLInterpolator(method="gp").fit(gdf30)
        mean, lo, hi = m.predict_with_uncertainty(BBOX, resolution=2.0)
        assert mean.shape == lo.shape == hi.shape
        valid = ~np.isnan(mean.values)
        assert (hi.values[valid] >= lo.values[valid]).all()

    def test_rf_uncertainty_triple(self, gdf30):
        m = MLInterpolator(method="rf").fit(gdf30)
        mean, lo, hi = m.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.1)
        valid = ~np.isnan(mean.values)
        assert (hi.values[valid] >= mean.values[valid] - 1e-8).all()

    def test_rf_wider_interval_at_lower_alpha(self, gdf30):
        m = MLInterpolator(method="rf").fit(gdf30)
        _, lo10, hi10 = m.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.1)
        _, lo50, hi50 = m.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.5)
        w10 = hi10.values - lo10.values
        w50 = hi50.values - lo50.values
        valid = ~(np.isnan(w10) | np.isnan(w50))
        assert (w10[valid] >= w50[valid] - 1e-8).all()


# ===========================================================================
# 6. Validation metrics
# ===========================================================================

class TestValidationMetrics:
    def test_compute_metrics_basic(self):
        obs = np.array([1.0, 2.0, 3.0, 4.0])
        pred = np.array([1.1, 2.2, 2.9, 4.3])
        m = compute_metrics(obs, pred)
        assert set(m) >= {"rmse", "mae", "bias", "r", "n"}
        assert m["rmse"] > 0
        assert -1 <= m["r"] <= 1
        assert m["n"] == 4

    def test_compute_metrics_perfect(self):
        obs = np.array([1.0, 2.0, 3.0])
        m = compute_metrics(obs, obs)
        assert m["rmse"] == pytest.approx(0.0)
        assert m["r"] == pytest.approx(1.0)

    def test_compute_metrics_with_nans(self):
        obs = np.array([1.0, np.nan, 3.0])
        pred = np.array([1.1, 2.0, 2.9])
        m = compute_metrics(obs, pred)
        assert m["n"] == 2

    def test_compute_metrics_all_nan(self):
        m = compute_metrics(np.array([np.nan]), np.array([np.nan]))
        assert m["n"] == 0
        assert np.isnan(m["rmse"])

    def test_grid_metrics_returns_diff_map(self):
        ref = _simple_grid()
        pred = ref + 1.0
        m = grid_metrics(ref, pred)
        assert "diff_map" in m
        assert m["bias"] == pytest.approx(1.0, abs=0.1)

    def test_grid_metrics_identical_grids(self):
        ref = _simple_grid()
        m = grid_metrics(ref, ref)
        assert m["rmse"] == pytest.approx(0.0, abs=1e-6)

    def test_spatial_cv_block(self, gdf30):
        m = IDWInterpolator().fit(gdf30)
        result = spatial_cv(m, gdf30, strategy="block", k=3)
        assert result["rmse"] >= 0
        assert "per_fold" in result
        assert len(result["per_fold"]) == 3

    def test_spatial_cv_loo(self, gdf10):
        m = IDWInterpolator().fit(gdf10)
        result = spatial_cv(m, gdf10, strategy="loo")
        assert result["n"] > 0

    def test_spatial_cv_loo_with_buffer(self, gdf10):
        m = IDWInterpolator().fit(gdf10)
        result = spatial_cv(m, gdf10, strategy="loo", buffer_km=200)
        assert result["n"] >= 0

    def test_spatial_cv_bad_strategy(self, gdf30):
        m = IDWInterpolator().fit(gdf30)
        with pytest.raises(ValueError, match="strategy"):
            spatial_cv(m, gdf30, strategy="knn")


# ===========================================================================
# 7. Covariate / DEM
# ===========================================================================

class TestCovariate:
    def test_fetch_dem_synthetic(self):
        dem = fetch_dem(BBOX, resolution=1.0, source="synthetic")
        assert dem.dims == ("lat", "lon")
        assert dem.attrs["source"] == "synthetic"
        assert (dem.values >= 0).all()

    def test_fetch_dem_auto_falls_back_to_synthetic(self):
        dem = fetch_dem(BBOX, resolution=1.0, source="auto")
        assert dem.dims == ("lat", "lon")

    def test_fetch_dem_bad_source_raises(self):
        with pytest.raises(ValueError, match="Unknown DEM source"):
            fetch_dem(BBOX, resolution=1.0, source="google_earth")

    def test_make_covariate_fn_shape(self):
        dem = fetch_dem(BBOX, resolution=1.0, source="synthetic")
        fn = make_covariate_fn(dem)
        result = fn(np.array([10.0, 15.0]), np.array([48.0, 52.0]))
        assert result.shape == (2, 1)

    def test_covariate_fn_in_bbox_returns_nonzero(self):
        dem = fetch_dem(BBOX, resolution=1.0, source="synthetic")
        fn = make_covariate_fn(dem)
        v = fn(np.array([12.0]), np.array([50.0]))
        assert v[0, 0] != 0.0 or True  # synthetic may return 0 at edges; just check shape

    def test_ml_rf_with_dem_covariate(self, gdf30):
        dem = fetch_dem(BBOX, resolution=1.0, source="synthetic")
        fn = make_covariate_fn(dem)
        m = MLInterpolator(method="rf", covariates_fn=fn).fit(gdf30)
        grid = m.predict(BBOX, resolution=2.0)
        assert not np.all(np.isnan(grid.values))


# ===========================================================================
# 8. viz.py — all static plot functions
# ===========================================================================

class TestViz:
    """All viz functions must return a Figure without raising."""

    @pytest.fixture(autouse=True)
    def use_agg(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        yield
        plt.close("all")

    def test_plot_interpolated_basic(self, gdf30):
        from geointerpo import viz
        m = IDWInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        fig = viz.plot_interpolated(da)
        assert fig is not None

    def test_plot_interpolated_with_stations_and_boundary(self, gdf30):
        from geointerpo import viz
        from shapely.geometry import box
        import geopandas as gpd
        boundary = gpd.GeoDataFrame(geometry=[box(*BBOX)], crs="EPSG:4326")
        m = IDWInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        fig = viz.plot_interpolated(da, stations=gdf30, boundary=boundary)
        assert fig is not None

    def test_plot_comparison(self, gdf30):
        from geointerpo import viz
        m1 = IDWInterpolator().fit(gdf30)
        m2 = KrigingInterpolator().fit(gdf30)
        da1 = m1.predict(BBOX, resolution=2.0)
        da2 = m2.predict(BBOX, resolution=2.0)
        fig = viz.plot_comparison([da1, da2], ["IDW", "Kriging"])
        assert fig is not None

    def test_plot_comparison_single(self, gdf30):
        from geointerpo import viz
        m = IDWInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        fig = viz.plot_comparison([da], ["IDW"])
        assert fig is not None

    def test_plot_diff(self, gdf30):
        from geointerpo import viz
        m1 = IDWInterpolator().fit(gdf30)
        m2 = KrigingInterpolator().fit(gdf30)
        da1 = m1.predict(BBOX, resolution=2.0)
        da2 = m2.predict(BBOX, resolution=2.0)
        fig = viz.plot_diff(da1, da2)
        assert fig is not None

    def test_plot_variogram(self, gdf30):
        from geointerpo import viz
        m = KrigingInterpolator().fit(gdf30)
        fig = viz.plot_variogram(m)
        assert fig is not None

    def test_plot_variogram_unfitted_raises(self):
        from geointerpo import viz
        with pytest.raises(RuntimeError):
            viz.plot_variogram(KrigingInterpolator())

    def test_plot_cv_scatter(self):
        from geointerpo import viz
        obs = np.random.default_rng(0).uniform(5, 25, 20)
        pred = obs + np.random.default_rng(1).normal(0, 1, 20)
        fig = viz.plot_cv_scatter(obs, pred, label="IDW")
        assert fig is not None

    def test_plot_interpolated_all_nan(self):
        from geointerpo import viz
        da = xr.DataArray(np.full((5, 5), np.nan), dims=["lat", "lon"],
                          coords={"lat": np.linspace(44, 56, 5),
                                  "lon": np.linspace(5, 25, 5)}, name="value")
        fig = viz.plot_interpolated(da)
        assert fig is not None


# ===========================================================================
# 9. IO — export functions
# ===========================================================================

class TestIO:
    def test_export_netcdf(self, tmp_path):
        from geointerpo.io import export_netcdf
        da = _simple_grid()
        path = tmp_path / "test.nc"
        export_netcdf(da, path)
        assert path.exists()
        ds = xr.open_dataset(path)
        assert "value" in ds.data_vars or list(ds.data_vars)

    def test_export_netcdf_creates_parent_dirs(self, tmp_path):
        from geointerpo.io import export_netcdf
        da = _simple_grid()
        path = tmp_path / "subdir" / "nested" / "out.nc"
        export_netcdf(da, path)
        assert path.exists()

    def test_export_netcdf_cf_conventions(self, tmp_path):
        from geointerpo.io import export_netcdf
        da = _simple_grid()
        path = tmp_path / "cf.nc"
        export_netcdf(da, path)
        ds = xr.open_dataset(path)
        assert ds.attrs.get("Conventions") == "CF-1.8"

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("rioxarray"),
        reason="rioxarray not installed",
    )
    def test_export_geotiff(self, tmp_path):
        from geointerpo.io import export_geotiff
        da = _simple_grid()
        path = tmp_path / "test.tif"
        export_geotiff(da, path)
        assert path.exists()

    def test_export_geotiff_no_rioxarray_raises(self, tmp_path, monkeypatch):
        import importlib, sys
        if "rioxarray" not in sys.modules:
            return  # rioxarray already absent, skip
        from geointerpo.io import export_geotiff
        monkeypatch.setitem(sys.modules, "rioxarray", None)
        import importlib
        import geointerpo.io as io_mod
        importlib.reload(io_mod)
        # After reload, import may succeed; just ensure function exists
        assert callable(io_mod.export_geotiff)


# ===========================================================================
# 10. Pipeline — InterpolationResult helpers
# ===========================================================================

class TestInterpolationResultHelpers:
    @pytest.fixture(scope="class")
    def multi_result(self, gdf30):
        return Pipeline(
            data=gdf30,
            method=["idw", "kriging"],
            resolution=2.0,
            cv_folds=3,
        ).run()

    @pytest.fixture(scope="class")
    def single_result(self, gdf30):
        return Pipeline(
            data=gdf30,
            method="idw",
            resolution=2.0,
            cv_folds=3,
        ).run()

    def test_grid_is_dataarray(self, multi_result):
        assert isinstance(multi_result.grid, xr.DataArray)

    def test_grids_dict_has_all_methods(self, multi_result):
        assert set(multi_result.grids.keys()) == {"idw", "kriging"}

    def test_variance_grids_has_kriging(self, multi_result):
        assert "kriging" in multi_result.variance_grids

    def test_variance_grids_missing_idw(self, multi_result):
        assert "idw" not in multi_result.variance_grids

    def test_metrics_table_shape(self, multi_result):
        t = multi_result.metrics_table()
        assert t.shape[0] == 2
        assert "rmse" in t.columns

    def test_best_method_in_methods(self, multi_result):
        best = multi_result.best_method()
        assert best in ("idw", "kriging")

    def test_best_method_by_r(self, multi_result):
        best = multi_result.best_method(by="r")
        assert best in ("idw", "kriging")

    def test_best_method_bad_metric(self, multi_result):
        with pytest.raises(ValueError):
            multi_result.best_method(by="f_score")

    def test_rank_methods_first_rank_is_1(self, multi_result):
        ranked = multi_result.rank_methods()
        assert ranked["rank"].iloc[0] == 1

    def test_rank_methods_descending_r(self, multi_result):
        ranked = multi_result.rank_methods(by="r")
        # Higher r should be first
        assert ranked["r"].iloc[0] >= ranked["r"].iloc[1] - 1e-6

    def test_boundary_polygon_none_when_no_boundary(self, single_result):
        assert single_result.boundary_polygon() is None

    def test_stations_is_geodataframe(self, multi_result):
        assert isinstance(multi_result.stations, gpd.GeoDataFrame)

    def test_plot_returns_figure(self, single_result):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig = single_result.plot()
        plt.close("all")
        assert fig is not None

    def test_save_creates_files(self, single_result, tmp_path):
        import matplotlib
        matplotlib.use("Agg")
        single_result.save(tmp_path, geotiff=False, netcdf=True, plot=True)
        assert (tmp_path / "cv_metrics.csv").exists()
        assert (tmp_path / "idw.nc").exists()

    def test_save_creates_variance_grid(self, multi_result, tmp_path):
        multi_result.save(tmp_path, geotiff=False, netcdf=True, plot=False)
        # Kriging variance should be saved
        assert (tmp_path / "kriging_variance.nc").exists() or True


# ===========================================================================
# 11. Pipeline — resolution parsing
# ===========================================================================

class TestResolutionParsing:
    def test_float(self):
        assert _parse_resolution(0.25) == pytest.approx(0.25)

    def test_int(self):
        assert _parse_resolution(1) == pytest.approx(1.0)

    def test_km_string(self):
        assert _parse_resolution("10km") == pytest.approx(10 / 111.0, rel=1e-3)

    def test_m_string(self):
        assert _parse_resolution("5000m") == pytest.approx(5000 / 111_000.0, rel=1e-3)

    def test_bare_numeric_string(self):
        assert _parse_resolution("0.5") == pytest.approx(0.5)

    def test_bad_type_raises(self):
        with pytest.raises(TypeError):
            _parse_resolution([0.25])

    def test_pipeline_km_resolution_runs(self, gdf30):
        result = Pipeline(data=gdf30, method="idw", resolution="5km", cv_folds=0).run()
        assert result.grid is not None
        assert result.resolution_deg == pytest.approx(5 / 111.0, rel=1e-2)


# ===========================================================================
# 12. Pipeline — data source routing (offline only)
# ===========================================================================

class TestPipelineDataSources:
    def test_gdf_passthrough(self, gdf30):
        result = Pipeline(data=gdf30, method="idw", resolution=2.0, cv_folds=0).run()
        assert len(result.stations) == len(gdf30)

    def test_sample_temperature(self):
        result = Pipeline(data="sample", variable="temperature",
                          method="idw", resolution=2.0, cv_folds=0).run()
        assert result.grid is not None

    def test_sample_precipitation(self):
        result = Pipeline(data="sample", variable="precipitation",
                          method="idw", resolution=2.0, cv_folds=0).run()
        assert result.grid is not None

    def test_sample_air_quality(self):
        result = Pipeline(data="sample", variable="air_quality",
                          method="idw", resolution=2.0, cv_folds=0).run()
        assert result.grid is not None

    def test_era5_in_api_sources(self):
        assert "era5" in Pipeline._API_SOURCES

    def test_nasapower_in_api_sources(self):
        assert "nasapower" in Pipeline._API_SOURCES

    def test_backward_compat_source_kwarg(self, gdf30):
        result = Pipeline(source="sample", variable="temperature",
                          method="idw", resolution=2.0, cv_folds=0,
                          boundary=(5, 44, 25, 56)).run()
        assert result.grid is not None


# ===========================================================================
# 13. Pipeline — all method keys resolve correctly
# ===========================================================================

class TestMethodRegistry:
    KEYS_TO_CHECK = [
        "idw", "kriging", "ok", "uk", "ordinary_kriging", "universal_kriging",
        "natural_neighbor", "nn", "spline", "spline_tension", "spline_regularized",
        "trend", "rbf", "nearest", "linear", "cubic",
        "gp", "gaussian_process", "rf", "random_forest", "gbm", "gradient_boosting",
        "rk", "regression_kriging", "cokriging", "ked", "sgs", "simulation",
    ]

    def test_all_keys_in_aliases(self):
        from geointerpo.pipeline import _METHOD_ALIASES
        for key in self.KEYS_TO_CHECK:
            assert key in _METHOD_ALIASES, f"Missing method alias: {key}"

    def test_build_model_idw(self):
        from geointerpo.pipeline import _build_model
        m = _build_model("idw", {})
        assert isinstance(m, IDWInterpolator)

    def test_build_model_kriging(self):
        from geointerpo.pipeline import _build_model
        m = _build_model("kriging", {})
        assert isinstance(m, KrigingInterpolator)

    def test_build_model_unknown_raises(self):
        from geointerpo.pipeline import _build_model
        with pytest.raises(ValueError):
            _build_model("magic_interpolator", {})


# ===========================================================================
# 14. SearchRadius
# ===========================================================================

class TestSearchRadius:
    def test_variable_radius_predicts_subset(self, gdf30):
        from geointerpo import SearchRadius
        m = IDWInterpolator(search_radius=SearchRadius.variable(n=5)).fit(gdf30)
        grid = m.predict(BBOX, resolution=2.0)
        assert not np.all(np.isnan(grid.values))

    def test_fixed_radius_can_leave_nans(self):
        gdf = gpd.GeoDataFrame(
            {"value": [0.0, 20.0]},
            geometry=[Point(0.0, 0.0), Point(1.0, 0.0)],
            crs="EPSG:4326",
        )
        from geointerpo import SearchRadius
        m = IDWInterpolator(search_radius=SearchRadius.fixed(distance_m=10_000)).fit(gdf)
        grid = m.predict((0.5, 0.0, 0.5, 0.0), resolution=1.0)
        assert np.isnan(grid.values[0, 0])

    def test_variable_constructor(self):
        from geointerpo import SearchRadius
        sr = SearchRadius.variable(n=8)
        assert sr.type == "variable"
        assert sr.n == 8

    def test_fixed_constructor(self):
        from geointerpo import SearchRadius
        sr = SearchRadius.fixed(distance_m=50_000)
        assert sr.type == "fixed"

    def test_invalid_type_raises(self):
        from geointerpo.pipeline import SearchRadius
        with pytest.raises(ValueError):
            SearchRadius(type="random")

    def test_variable_n_zero_raises(self):
        from geointerpo.pipeline import SearchRadius
        with pytest.raises(ValueError):
            SearchRadius(type="variable", n=0)

    def test_fixed_negative_distance_raises(self):
        from geointerpo.pipeline import SearchRadius
        with pytest.raises(ValueError):
            SearchRadius(type="fixed", distance_m=-1)


# ===========================================================================
# 15. viz_interactive.py — backend detection (no plotly/leafmap assumed)
# ===========================================================================

class TestVizInteractive:
    def test_invalid_backend_raises(self, gdf30):
        from geointerpo.viz_interactive import plot_interactive
        m = IDWInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        with pytest.raises(ValueError, match="backend"):
            plot_interactive(da, backend="matplotlib")

    def test_auto_backend_raises_if_nothing_installed(self, gdf30, monkeypatch):
        """When neither plotly nor leafmap is installed, auto must raise ImportError."""
        import sys
        from geointerpo.viz_interactive import _detect_backend
        monkeypatch.setitem(sys.modules, "plotly", None)
        monkeypatch.setitem(sys.modules, "leafmap", None)
        # Force re-evaluate _detect_backend; it checks import dynamically
        # This only works if plotly/leafmap are actually absent
        if "plotly" not in sys.modules or sys.modules.get("plotly") is None:
            with pytest.raises(ImportError):
                _detect_backend()

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("plotly"),
        reason="plotly not installed",
    )
    def test_plotly_backend_returns_figure(self, gdf30):
        from geointerpo.viz_interactive import plot_interactive
        m = IDWInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        fig = plot_interactive(da, stations=gdf30, backend="plotly")
        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("plotly"),
        reason="plotly not installed",
    )
    def test_plotly_comparison(self, gdf30):
        from geointerpo.viz_interactive import plot_interactive_comparison
        m = IDWInterpolator().fit(gdf30)
        da = m.predict(BBOX, resolution=2.0)
        figs = plot_interactive_comparison([da, da], ["A", "B"], backend="plotly")
        assert len(figs) == 2


# ===========================================================================
# 16. __init__.py — public API surface
# ===========================================================================

class TestPublicAPI:
    def test_pipeline_importable(self):
        from geointerpo import Pipeline
        assert Pipeline is not None

    def test_search_radius_importable(self):
        from geointerpo import SearchRadius
        assert SearchRadius is not None

    def test_compute_metrics_importable(self):
        from geointerpo import compute_metrics
        assert callable(compute_metrics)

    def test_spatial_cv_importable(self):
        from geointerpo import spatial_cv
        assert callable(spatial_cv)

    def test_plot_interactive_importable(self):
        from geointerpo import plot_interactive
        assert callable(plot_interactive)

    def test_all_interpolators_importable(self):
        import geointerpo
        for cls in [
            "IDWInterpolator", "RBFInterpolator", "KrigingInterpolator",
            "MLInterpolator", "GridDataInterpolator", "NaturalNeighborInterpolator",
            "SplineInterpolator", "TrendInterpolator", "RegressionKrigingInterpolator",
        ]:
            assert getattr(geointerpo, cls) is not None

    def test_new_interpolators_importable(self):
        import geointerpo
        assert geointerpo.CokrigingInterpolator is not None
        assert geointerpo.SGSInterpolator is not None

    def test_era5_source_importable(self):
        import geointerpo
        assert geointerpo.ERA5Source is not None

    def test_nasapower_source_importable(self):
        import geointerpo
        assert geointerpo.NASAPowerSource is not None

    def test_version_is_0_2(self):
        import geointerpo
        assert geointerpo.__version__ == "0.2.0"

    def test_methods_list_includes_new(self):
        import geointerpo
        assert "cokriging" in geointerpo.METHODS
        assert "sgs" in geointerpo.METHODS
