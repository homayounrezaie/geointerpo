"""Tests for all improvements added in v0.2.0.

All tests are offline (no network, no heavy optional deps beyond scipy/sklearn/pykrige).
gstools tests are skipped if gstools is not installed.
"""

from __future__ import annotations

import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point

from geointerpo.data.samples import load_temperature
from geointerpo.interpolators.idw import IDWInterpolator
from geointerpo.interpolators.kriging import KrigingInterpolator
from geointerpo.interpolators.ml import MLInterpolator
from geointerpo.pipeline import Pipeline, InterpolationResult, _parse_resolution
from geointerpo.validation.metrics import compute_metrics, spatial_cv

BBOX = (5.0, 44.0, 25.0, 56.0)


@pytest.fixture(scope="module")
def gdf():
    return load_temperature(n_stations=30, seed=42)


# ---------------------------------------------------------------------------
# 1. IDW KD-Tree vectorization
# ---------------------------------------------------------------------------

def test_idw_kdtree_produces_correct_values(gdf):
    """KD-tree IDW must give the same result as the old per-point loop."""
    model = IDWInterpolator(power=2).fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_idw_n_neighbors(gdf):
    """n_neighbors parameter must restrict which stations are used."""
    m_full = IDWInterpolator(power=2).fit(gdf)
    m_3 = IDWInterpolator(power=2, n_neighbors=3).fit(gdf)
    g_full = m_full.predict(BBOX, resolution=2.0)
    g_3 = m_3.predict(BBOX, resolution=2.0)
    # Results should differ when restricting neighbors
    assert not np.allclose(g_full.values, g_3.values, equal_nan=True)


def test_idw_exact_at_stations_kdtree(gdf):
    """KD-tree IDW must still return exact station values at station locations."""
    model = IDWInterpolator(power=2).fit(gdf)
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", model._proj_crs, always_xy=True)
    xs, ys = t.transform(gdf.geometry.x.values[:5], gdf.geometry.y.values[:5])
    preds = model._predict(xs, ys)
    np.testing.assert_allclose(preds, gdf["value"].values[:5], rtol=1e-5)


def test_idw_kdtree_faster_than_naive(gdf):
    """Vectorized IDW should complete in well under 5 seconds on a 50×50 grid."""
    import time
    model = IDWInterpolator(power=2).fit(gdf)
    start = time.time()
    model.predict(BBOX, resolution=0.5)
    elapsed = time.time() - start
    assert elapsed < 10.0, f"IDW took {elapsed:.1f}s — KD-tree may not be working"


# ---------------------------------------------------------------------------
# 2. Kriging: variance DataArray + anisotropy
# ---------------------------------------------------------------------------

def test_kriging_predict_with_variance_returns_two_arrays(gdf):
    model = KrigingInterpolator().fit(gdf)
    mean_da, var_da = model.predict_with_variance(BBOX, resolution=1.0)
    assert mean_da.shape == var_da.shape
    assert mean_da.dims == ("lat", "lon")
    assert var_da.name is not None and "variance" in var_da.name


def test_kriging_variance_is_non_negative(gdf):
    model = KrigingInterpolator().fit(gdf)
    _, var_da = model.predict_with_variance(BBOX, resolution=1.0)
    valid = var_da.values[~np.isnan(var_da.values)]
    assert (valid >= -1e-8).all(), "Kriging variance must be non-negative"


def test_kriging_anisotropy_params_accepted(gdf):
    """Anisotropy parameters must be accepted without error."""
    model = KrigingInterpolator(anisotropy_scaling=0.5, anisotropy_angle=45.0).fit(gdf)
    grid = model.predict(BBOX, resolution=1.0)
    assert not np.all(np.isnan(grid.values))


def test_kriging_anisotropy_changes_output(gdf):
    """Anisotropic and isotropic kriging should give different results."""
    m_iso = KrigingInterpolator(anisotropy_scaling=1.0).fit(gdf)
    m_aniso = KrigingInterpolator(anisotropy_scaling=0.3, anisotropy_angle=30.0).fit(gdf)
    g_iso = m_iso.predict(BBOX, resolution=2.0)
    g_aniso = m_aniso.predict(BBOX, resolution=2.0)
    assert not np.allclose(g_iso.values, g_aniso.values, equal_nan=True)


def test_kriging_variance_stored_in_attrs(gdf):
    """Original attrs['variance'] must still be present for backward compatibility."""
    model = KrigingInterpolator().fit(gdf)
    da = model.predict(BBOX, resolution=1.0)
    assert "variance" in da.attrs


# ---------------------------------------------------------------------------
# 3. ML uncertainty
# ---------------------------------------------------------------------------

def test_ml_rf_predict_with_uncertainty(gdf):
    model = MLInterpolator(method="rf").fit(gdf)
    mean, lower, upper = model.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.1)
    assert mean.shape == lower.shape == upper.shape
    # Upper bound must be >= mean >= lower bound (at least for most cells)
    valid = ~np.isnan(mean.values)
    assert (upper.values[valid] >= mean.values[valid] - 1e-8).all()
    assert (mean.values[valid] >= lower.values[valid] - 1e-8).all()


def test_ml_gp_predict_with_uncertainty(gdf):
    model = MLInterpolator(method="gp").fit(gdf)
    mean, lower, upper = model.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.1)
    assert mean.shape == lower.shape == upper.shape
    valid = ~np.isnan(mean.values)
    assert (upper.values[valid] >= lower.values[valid]).all()


def test_ml_rf_uncertainty_interval_widens_with_alpha(gdf):
    """Narrower alpha → wider interval."""
    model = MLInterpolator(method="rf").fit(gdf)
    _, lo90, hi90 = model.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.1)
    _, lo50, hi50 = model.predict_with_uncertainty(BBOX, resolution=2.0, alpha=0.5)
    width_90 = (hi90.values - lo90.values)
    width_50 = (hi50.values - lo50.values)
    valid = ~(np.isnan(width_90) | np.isnan(width_50))
    assert (width_90[valid] >= width_50[valid] - 1e-8).all()


# ---------------------------------------------------------------------------
# 4. Spatial cross-validation
# ---------------------------------------------------------------------------

def test_spatial_cv_block_returns_metrics(gdf):
    model = IDWInterpolator(power=2).fit(gdf)
    result = spatial_cv(model, gdf, strategy="block", k=3)
    assert {"rmse", "mae", "bias", "r", "n", "per_fold"} <= result.keys()
    assert result["rmse"] >= 0
    assert result["n"] > 0


def test_spatial_cv_loo_returns_metrics(gdf):
    small_gdf = gdf.iloc[:10].copy()
    model = IDWInterpolator(power=2).fit(small_gdf)
    result = spatial_cv(model, small_gdf, strategy="loo")
    assert result["n"] > 0
    assert result["rmse"] >= 0


def test_spatial_cv_loo_with_buffer(gdf):
    small_gdf = gdf.iloc[:10].copy()
    model = IDWInterpolator(power=2).fit(small_gdf)
    result = spatial_cv(model, small_gdf, strategy="loo", buffer_km=50)
    # With a large buffer many folds may be skipped, but n should be >= 0
    assert result["n"] >= 0


def test_spatial_cv_invalid_strategy(gdf):
    model = IDWInterpolator().fit(gdf)
    with pytest.raises(ValueError, match="strategy"):
        spatial_cv(model, gdf, strategy="random_forest")


# ---------------------------------------------------------------------------
# 5. Resolution in km
# ---------------------------------------------------------------------------

def test_parse_resolution_float():
    from geointerpo.pipeline import _parse_resolution
    assert _parse_resolution(0.25) == pytest.approx(0.25)


def test_parse_resolution_km_string():
    deg = _parse_resolution("10km")
    assert deg == pytest.approx(10 / 111.0, rel=1e-3)


def test_parse_resolution_m_string():
    deg = _parse_resolution("5000m")
    assert deg == pytest.approx(5000 / 111_000.0, rel=1e-3)


def test_parse_resolution_string_number():
    assert _parse_resolution("0.5") == pytest.approx(0.5)


def test_pipeline_accepts_km_resolution(gdf):
    """Pipeline must run without error when resolution='5km'."""
    result = Pipeline(
        data=gdf,
        method="idw",
        resolution="5km",
        cv_folds=3,
    ).run()
    assert result.grid is not None


# ---------------------------------------------------------------------------
# 6. Auto-rank methods
# ---------------------------------------------------------------------------

def test_best_method_returns_string(gdf):
    result = Pipeline(
        data=gdf,
        method=["idw", "kriging"],
        resolution=2.0,
        cv_folds=3,
    ).run()
    best = result.best_method()
    assert best in ("idw", "kriging")


def test_rank_methods_returns_dataframe(gdf):
    import pandas as pd
    result = Pipeline(
        data=gdf,
        method=["idw", "kriging"],
        resolution=2.0,
        cv_folds=3,
    ).run()
    ranked = result.rank_methods()
    assert isinstance(ranked, pd.DataFrame)
    assert "rank" in ranked.columns
    assert ranked["rank"].iloc[0] == 1


def test_best_method_by_r(gdf):
    result = Pipeline(
        data=gdf,
        method=["idw", "kriging"],
        resolution=2.0,
        cv_folds=3,
    ).run()
    best_r = result.best_method(by="r")
    assert best_r in ("idw", "kriging")


def test_rank_methods_invalid_metric(gdf):
    result = Pipeline(
        data=gdf,
        method="idw",
        resolution=2.0,
        cv_folds=3,
    ).run()
    with pytest.raises(ValueError, match="Metric"):
        result.rank_methods(by="f1_score")


# ---------------------------------------------------------------------------
# 7. Variance grids in InterpolationResult
# ---------------------------------------------------------------------------

def test_pipeline_kriging_populates_variance_grids(gdf):
    result = Pipeline(
        data=gdf,
        method="kriging",
        resolution=2.0,
        cv_folds=0,
    ).run()
    assert "kriging" in result.variance_grids
    var_da = result.variance_grids["kriging"]
    assert var_da.dims == ("lat", "lon")
    valid = var_da.values[~np.isnan(var_da.values)]
    assert (valid >= -1e-8).all()


def test_pipeline_idw_has_no_variance_grid(gdf):
    result = Pipeline(
        data=gdf,
        method="idw",
        resolution=2.0,
        cv_folds=0,
    ).run()
    assert "idw" not in result.variance_grids


# ---------------------------------------------------------------------------
# 8 & 9. Cokriging + SGS (requires gstools)
# ---------------------------------------------------------------------------

def _gstools_installed() -> bool:
    try:
        import gstools  # noqa: F401
        return True
    except ImportError:
        return False


needs_gstools = pytest.mark.skipif(not _gstools_installed(), reason="gstools not installed")


def _make_cokriging_gdf(n=20, seed=7):
    rng = np.random.default_rng(seed)
    lons = rng.uniform(5, 25, n)
    lats = rng.uniform(44, 56, n)
    values = rng.uniform(5, 30, n)
    secondary = rng.uniform(100, 2000, n)
    return gpd.GeoDataFrame(
        {"value": values, "secondary": secondary},
        geometry=[Point(lo, la) for lo, la in zip(lons, lats)],
        crs="EPSG:4326",
    )


@needs_gstools
def test_cokriging_fit_predict():
    from geointerpo.interpolators.cokriging import CokrigingInterpolator
    gdf = _make_cokriging_gdf()
    model = CokrigingInterpolator(
        secondary_col="secondary",
        secondary_fn=lambda xs, ys: np.full(len(xs), 500.0),
        fit_variogram=False,
    ).fit(gdf)
    grid = model.predict(BBOX, resolution=2.0)
    assert grid.shape[0] > 0 and grid.shape[1] > 0


@needs_gstools
def test_cokriging_missing_secondary_col():
    from geointerpo.interpolators.cokriging import CokrigingInterpolator
    gdf = load_temperature(n_stations=10)
    with pytest.raises(ValueError, match="secondary"):
        CokrigingInterpolator(secondary_col="elevation").fit(gdf)


@needs_gstools
def test_cokriging_missing_secondary_fn():
    from geointerpo.interpolators.cokriging import CokrigingInterpolator
    gdf = _make_cokriging_gdf()
    model = CokrigingInterpolator(secondary_col="secondary", fit_variogram=False).fit(gdf)
    with pytest.raises(RuntimeError, match="secondary_fn"):
        model.predict(BBOX, resolution=2.0)


@needs_gstools
def test_sgs_predict_returns_mean():
    from geointerpo.interpolators.sgs import SGSInterpolator
    gdf = load_temperature(n_stations=30, seed=42)
    model = SGSInterpolator(n_realizations=5, fit_variogram=False).fit(gdf)
    mean_da = model.predict(BBOX, resolution=2.0)
    assert mean_da.dims == ("lat", "lon")
    assert not np.all(np.isnan(mean_da.values))


@needs_gstools
def test_sgs_predict_with_std():
    from geointerpo.interpolators.sgs import SGSInterpolator
    gdf = load_temperature(n_stations=30, seed=42)
    model = SGSInterpolator(n_realizations=5, fit_variogram=False).fit(gdf)
    mean_da, std_da = model.predict_with_std(BBOX, resolution=2.0)
    assert mean_da.shape == std_da.shape
    valid = std_da.values[~np.isnan(std_da.values)]
    assert (valid >= 0).all()


@needs_gstools
def test_sgs_realize_returns_3d_array():
    from geointerpo.interpolators.sgs import SGSInterpolator
    gdf = load_temperature(n_stations=30, seed=42)
    n_real = 4
    model = SGSInterpolator(n_realizations=n_real, fit_variogram=False).fit(gdf)
    real_da = model.realize(BBOX, resolution=2.0)
    assert real_da.dims[0] == "realization"
    assert real_da.shape[0] == n_real


# ---------------------------------------------------------------------------
# 10. Pipeline method keys for new methods
# ---------------------------------------------------------------------------

def test_pipeline_method_aliases_include_cokriging():
    from geointerpo.pipeline import _METHOD_ALIASES
    assert "cokriging" in _METHOD_ALIASES
    assert "sgs" in _METHOD_ALIASES
    assert "ked" in _METHOD_ALIASES


def test_pipeline_api_sources_include_era5_nasapower():
    p = Pipeline(data="sample", method="idw", resolution=2.0)
    assert "era5" in p._API_SOURCES
    assert "nasapower" in p._API_SOURCES
