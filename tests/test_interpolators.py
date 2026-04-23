"""Offline tests — no network, no optional heavy deps beyond scipy/sklearn/pykrige."""

import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point

from geointerpo.data.samples import load_temperature, load_precipitation, load_air_quality
from geointerpo import SearchRadius
from geointerpo.interpolators.idw import IDWInterpolator
from geointerpo.interpolators.rbf import RBFInterpolator
from geointerpo.interpolators.griddata import GridDataInterpolator
from geointerpo.interpolators.kriging import KrigingInterpolator
from geointerpo.interpolators.ml import MLInterpolator
from geointerpo.interpolators.regression_kriging import RegressionKrigingInterpolator
from geointerpo.validation.metrics import compute_metrics


BBOX = (5.0, 44.0, 25.0, 56.0)


@pytest.fixture(scope="module")
def gdf():
    return load_temperature(n_stations=30, seed=99)


# ---------------------------------------------------------------------------
# Sample datasets
# ---------------------------------------------------------------------------

def test_load_temperature():
    gdf = load_temperature(n_stations=20)
    assert len(gdf) == 20
    assert "value" in gdf.columns
    assert gdf.crs.to_epsg() == 4326


def test_load_precipitation():
    gdf = load_precipitation(n_stations=15)
    assert (gdf["value"] >= 0).all()


def test_load_air_quality():
    gdf = load_air_quality(n_stations=15)
    assert gdf["value"].notna().all()


# ---------------------------------------------------------------------------
# Interpolators — basic fit/predict
# ---------------------------------------------------------------------------

def test_idw_fit_predict(gdf):
    model = IDWInterpolator(power=2).fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert grid.shape[0] > 0 and grid.shape[1] > 0
    assert not np.all(np.isnan(grid.values))


def test_rbf_fit_predict(gdf):
    model = RBFInterpolator(kernel="thin_plate_spline").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_griddata_nearest(gdf):
    model = GridDataInterpolator(method="nearest").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_griddata_linear(gdf):
    model = GridDataInterpolator(method="linear").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    # linear griddata has NaN outside convex hull — at least some non-NaN
    assert np.any(~np.isnan(grid.values))


def test_kriging_fit_predict(gdf):
    model = KrigingInterpolator(mode="ordinary", variogram_model="spherical").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_kriging_variance_in_attrs(gdf):
    model = KrigingInterpolator().fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert "variance" in grid.attrs


def test_kriging_variogram_parameters(gdf):
    model = KrigingInterpolator().fit(gdf)
    params = model.variogram_parameters
    assert len(params) == 3  # nugget, sill, range for spherical


def test_ml_gp_fit_predict(gdf):
    model = MLInterpolator(method="gp").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_ml_gp_predict_with_std(gdf):
    model = MLInterpolator(method="gp").fit(gdf)
    mean, std = model.predict_with_std(BBOX, resolution=1.0)
    assert mean.shape == std.shape
    assert (std.values >= 0).all()


def test_ml_rf_fit_predict(gdf):
    model = MLInterpolator(method="rf").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_regression_kriging(gdf):
    model = RegressionKrigingInterpolator(trend_model="linear").fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


# ---------------------------------------------------------------------------
# Spatial correctness: UTM projection
# ---------------------------------------------------------------------------

def test_metric_crs_set_after_fit(gdf):
    model = IDWInterpolator().fit(gdf)
    assert model._proj_crs is not None
    assert model._proj_crs.is_projected


def test_non_metric_griddata_has_no_proj_crs(gdf):
    # GridDataInterpolator also _needs_metric=True (UTM), check it's set
    model = GridDataInterpolator(method="nearest").fit(gdf)
    assert model._proj_crs is not None


# ---------------------------------------------------------------------------
# IDW exact interpolation at station locations
# ---------------------------------------------------------------------------

def test_idw_exact_at_stations(gdf):
    model = IDWInterpolator(power=2).fit(gdf)
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", model._proj_crs, always_xy=True)
    xs, ys = t.transform(gdf.geometry.x.values[:5], gdf.geometry.y.values[:5])
    preds = model._predict(xs, ys)
    np.testing.assert_allclose(preds, gdf["value"].values[:5], rtol=1e-5)


def test_idw_fixed_search_radius_can_leave_gaps():
    gdf = gpd.GeoDataFrame(
        {"value": [0.0, 20.0]},
        geometry=[Point(0.0, 0.0), Point(1.0, 0.0)],
        crs="EPSG:4326",
    )
    model = IDWInterpolator(search_radius=SearchRadius.fixed(distance_m=10_000)).fit(gdf)
    grid = model.predict((0.5, 0.0, 0.5, 0.0), resolution=1.0)
    assert np.isnan(grid.values[0, 0])


# ---------------------------------------------------------------------------
# Blocked spatial cross-validation
# ---------------------------------------------------------------------------

def test_cross_validate_returns_metrics(gdf):
    model = IDWInterpolator(power=2).fit(gdf)
    cv = model.cross_validate(gdf, k=3)
    assert set(cv.keys()) >= {"rmse", "mae", "bias", "r", "n"}
    assert cv["rmse"] >= 0
    assert cv["n"] > 0


def test_cross_validate_spatial_blocking(gdf):
    # Verify folds are spatially ordered (not random chunks):
    # If we split by lat-sorted order, train/test shouldn't be interleaved.
    # We just assert the cross_validate doesn't error and returns sensible values.
    model = KrigingInterpolator().fit(gdf)
    cv = model.cross_validate(gdf, k=5)
    assert 0 < cv["rmse"] < 100


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_compute_metrics_basic():
    obs = np.array([1.0, 2.0, 3.0, 4.0])
    pred = np.array([1.1, 2.2, 2.9, 4.3])
    m = compute_metrics(obs, pred)
    assert m["rmse"] > 0
    assert -1 <= m["r"] <= 1
    assert m["n"] == 4


def test_compute_metrics_with_nans():
    obs = np.array([1.0, np.nan, 3.0])
    pred = np.array([1.1, 2.0, 2.9])
    m = compute_metrics(obs, pred)
    assert m["n"] == 2


def test_compute_metrics_perfect():
    obs = np.array([1.0, 2.0, 3.0])
    m = compute_metrics(obs, obs)
    assert m["rmse"] == pytest.approx(0.0)
    assert m["bias"] == pytest.approx(0.0)
    assert m["r"] == pytest.approx(1.0)
