"""Tests for the 3-step Pipeline API: data, boundary, method.

All tests are offline — no network, no GEE.
"""

from __future__ import annotations

import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box, mapping


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BBOX = (-114.5, 50.8, -113.8, 51.3)   # approximate Calgary extent
RNG = np.random.default_rng(42)


def _make_gdf(n=40, bbox=BBOX):
    lons = RNG.uniform(bbox[0], bbox[2], n)
    lats = RNG.uniform(bbox[1], bbox[3], n)
    vals = 15 + lons * 0.1 + lats * 0.2 + RNG.normal(0, 0.5, n)
    return gpd.GeoDataFrame(
        {"value": vals},
        geometry=[Point(lo, la) for lo, la in zip(lons, lats)],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_gdf():
    return _make_gdf()


@pytest.fixture
def csv_file(tmp_path, sample_gdf):
    df = pd.DataFrame({
        "lon": sample_gdf.geometry.x,
        "lat": sample_gdf.geometry.y,
        "value": sample_gdf["value"],
    })
    p = tmp_path / "stations.csv"
    df.to_csv(p, index=False)
    return p


@pytest.fixture
def csv_alt_cols(tmp_path, sample_gdf):
    """CSV with non-standard column names."""
    df = pd.DataFrame({
        "longitude": sample_gdf.geometry.x,
        "latitude": sample_gdf.geometry.y,
        "temperature": sample_gdf["value"],
    })
    p = tmp_path / "stations_alt.csv"
    df.to_csv(p, index=False)
    return p


@pytest.fixture
def geojson_file(tmp_path, sample_gdf):
    p = tmp_path / "stations.geojson"
    sample_gdf.to_file(p, driver="GeoJSON")
    return p


@pytest.fixture
def shp_file(tmp_path, sample_gdf):
    p = tmp_path / "stations.shp"
    sample_gdf.to_file(p)
    return p


@pytest.fixture
def boundary_box():
    return box(*BBOX)


# ---------------------------------------------------------------------------
# Step 1: data input — file paths
# ---------------------------------------------------------------------------

class TestDataCSV:
    def test_csv_path_string(self, csv_file):
        from geointerpo.pipeline import _load_csv
        gdf = _load_csv(csv_file)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) > 0
        assert "value" in gdf.columns
        assert gdf.crs.to_epsg() == 4326

    def test_csv_auto_alias_columns(self, csv_alt_cols):
        """'longitude'/'latitude' should be auto-detected without setting lon_col/lat_col."""
        from geointerpo.pipeline import _load_csv
        gdf = _load_csv(csv_alt_cols, value_col="temperature")
        assert len(gdf) > 0
        assert "value" in gdf.columns

    def test_csv_missing_lat_raises(self, tmp_path):
        from geointerpo.pipeline import _load_csv
        p = tmp_path / "bad.csv"
        pd.DataFrame({"x_coord": [1], "value": [1]}).to_csv(p, index=False)
        with pytest.raises(ValueError, match="latitude"):
            _load_csv(p)

    def test_csv_missing_value_raises(self, tmp_path):
        from geointerpo.pipeline import _load_csv
        p = tmp_path / "bad.csv"
        pd.DataFrame({"lon": [1], "lat": [1], "other": [1]}).to_csv(p, index=False)
        with pytest.raises(ValueError, match="value column"):
            _load_csv(p)


class TestDataGeoFile:
    def test_geojson_file(self, geojson_file):
        from geointerpo.pipeline import _load_geo_file
        gdf = _load_geo_file(geojson_file)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert "value" in gdf.columns
        assert gdf.crs.to_epsg() == 4326

    def test_shp_file(self, shp_file):
        from geointerpo.pipeline import _load_geo_file
        gdf = _load_geo_file(shp_file)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert "value" in gdf.columns

    def test_geodataframe_passthrough(self, sample_gdf):
        from geointerpo.pipeline import _ensure_value_col
        gdf = _ensure_value_col(sample_gdf, "value")
        assert "value" in gdf.columns


# ---------------------------------------------------------------------------
# Step 2: boundary input variants
# ---------------------------------------------------------------------------

class TestBoundaryInputs:
    def test_tuple_bbox_as_boundary(self, sample_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            data=sample_gdf,
            boundary=BBOX,              # 4-tuple
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.boundary is not None
        assert result.grid is not None

    def test_shapely_geom_as_boundary(self, sample_gdf, boundary_box):
        from geointerpo import Pipeline
        result = Pipeline(
            data=sample_gdf,
            boundary=boundary_box,
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.boundary is not None

    def test_geodataframe_as_boundary(self, sample_gdf):
        from geointerpo import Pipeline
        bnd = gpd.GeoDataFrame(geometry=[box(*BBOX)], crs="EPSG:4326")
        result = Pipeline(
            data=sample_gdf,
            boundary=bnd,
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.boundary is not None

    def test_no_boundary_bbox_from_data(self, sample_gdf):
        """When boundary=None, bbox should be derived from data extent."""
        from geointerpo import Pipeline
        result = Pipeline(
            data=sample_gdf,
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.grid is not None
        assert result.boundary is None


# ---------------------------------------------------------------------------
# Full 3-step pipeline with file input
# ---------------------------------------------------------------------------

class TestFullPipelineFileInput:
    def test_csv_input_with_bbox_boundary(self, csv_file):
        from geointerpo import Pipeline
        result = Pipeline(
            data=str(csv_file),
            boundary=BBOX,
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.grid is not None
        assert len(result.stations) > 0

    def test_geojson_input_no_boundary(self, geojson_file):
        from geointerpo import Pipeline
        result = Pipeline(
            data=str(geojson_file),
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.grid is not None

    def test_geodataframe_input(self, sample_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            data=sample_gdf,
            method="kriging",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.grid is not None
        assert "kriging" in result.grids

    def test_multiple_methods(self, sample_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            data=sample_gdf,
            method=["idw", "kriging"],
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert set(result.grids.keys()) == {"idw", "kriging"}

    def test_per_method_params(self, sample_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            data=sample_gdf,
            method=["idw", "spline"],
            method_params={
                "idw":    {"power": 3},
                "spline": {"smoothing": 0.2},
            },
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert set(result.grids.keys()) == {"idw", "spline"}


# ---------------------------------------------------------------------------
# Step 1: API source string
# ---------------------------------------------------------------------------

class TestDataAPISource:
    def test_api_source_string_sample(self, boundary_box):
        from geointerpo import Pipeline
        result = Pipeline(
            data="sample",
            variable="temperature",
            boundary=boundary_box,
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.grid is not None

    def test_backward_compat_source_kwarg(self):
        """Old-style source= kwarg should still work."""
        from geointerpo import Pipeline
        result = Pipeline(
            source="sample",
            variable="temperature",
            boundary=BBOX,
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.grid is not None


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_file_raises(self):
        from geointerpo import Pipeline
        with pytest.raises(FileNotFoundError):
            Pipeline(
                data="/nonexistent/stations.csv",
                method="idw",
                resolution=0.1,
            ).run()

    def test_unsupported_extension_raises(self, tmp_path):
        from geointerpo import Pipeline
        p = tmp_path / "data.xlsx"
        p.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported file type"):
            Pipeline(
                data=str(p),
                method="idw",
                resolution=0.1,
            ).run()

    def test_no_data_no_source_no_boundary_raises(self):
        from geointerpo import Pipeline
        with pytest.raises(ValueError):
            Pipeline(method="idw")
