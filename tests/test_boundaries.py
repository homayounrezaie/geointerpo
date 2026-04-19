"""Offline tests for geointerpo.boundaries.

All tests in this file run without any network access.
"""

from __future__ import annotations

import json
import pathlib
import tempfile

import geopandas as gpd
import pytest
import shapely.geometry
from shapely.geometry import box, shape


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_BBOX = (-114.5, 50.8, -113.8, 51.3)  # approximate Calgary extent


@pytest.fixture
def square_geom():
    return box(*SIMPLE_BBOX)


@pytest.fixture
def simple_gdf(square_geom):
    return gpd.GeoDataFrame(geometry=[square_geom], crs="EPSG:4326")


@pytest.fixture
def geojson_file(square_geom, tmp_path):
    """Write a temporary GeoJSON file and return its path."""
    feature = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": shapely.geometry.mapping(square_geom), "properties": {}}
        ],
    }
    p = tmp_path / "calgary.geojson"
    p.write_text(json.dumps(feature))
    return p


@pytest.fixture
def projected_gdf(square_geom):
    """GeoDataFrame in UTM zone 11N (EPSG:32611) to test reprojection."""
    gdf = gpd.GeoDataFrame(geometry=[square_geom], crs="EPSG:4326")
    return gdf.to_crs("EPSG:32611")


# ---------------------------------------------------------------------------
# load_boundary — passthrough inputs
# ---------------------------------------------------------------------------

class TestLoadBoundaryPassthrough:
    def test_shapely_geometry(self, square_geom):
        from geointerpo.boundaries import load_boundary
        result = load_boundary(square_geom)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 1
        assert result.crs.to_epsg() == 4326

    def test_geodataframe_passthrough(self, simple_gdf):
        from geointerpo.boundaries import load_boundary
        result = load_boundary(simple_gdf)
        assert isinstance(result, gpd.GeoDataFrame)
        assert result.crs.to_epsg() == 4326

    def test_projected_gdf_reprojected(self, projected_gdf):
        from geointerpo.boundaries import load_boundary
        result = load_boundary(projected_gdf)
        assert result.crs.to_epsg() == 4326

    def test_invalid_type_raises(self):
        from geointerpo.boundaries import load_boundary
        with pytest.raises(TypeError):
            load_boundary(12345)


# ---------------------------------------------------------------------------
# load_boundary — file inputs
# ---------------------------------------------------------------------------

class TestLoadBoundaryFile:
    def test_geojson_file(self, geojson_file):
        from geointerpo.boundaries import load_boundary
        result = load_boundary(geojson_file)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 1
        assert result.crs.to_epsg() == 4326

    def test_geojson_file_as_string(self, geojson_file):
        from geointerpo.boundaries import load_boundary
        result = load_boundary(str(geojson_file))
        assert isinstance(result, gpd.GeoDataFrame)

    def test_missing_file_raises(self):
        from geointerpo.boundaries import load_boundary
        with pytest.raises(FileNotFoundError):
            load_boundary(pathlib.Path("/nonexistent/path/boundary.geojson"))

    def test_gpkg_file(self, simple_gdf, tmp_path):
        from geointerpo.boundaries import load_boundary
        path = tmp_path / "test.gpkg"
        simple_gdf.to_file(path, driver="GPKG")
        result = load_boundary(path)
        assert result.crs.to_epsg() == 4326


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_dissolves_multi_row(self):
        from geointerpo.boundaries import load_boundary
        geoms = [box(-114.5, 50.8, -114.0, 51.0), box(-114.0, 50.8, -113.8, 51.3)]
        gdf = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")
        result = load_boundary(gdf)
        assert len(result) == 1  # dissolved to one row

    def test_geometry_is_valid(self, simple_gdf):
        from geointerpo.boundaries import load_boundary
        result = load_boundary(simple_gdf)
        assert result.geometry.iloc[0].is_valid

    def test_multipolygon_input_dissolves(self):
        from geointerpo.boundaries import load_boundary
        multi = shapely.geometry.MultiPolygon([
            box(-114.5, 50.8, -114.2, 51.0),
            box(-114.1, 50.9, -113.8, 51.3),
        ])
        gdf = gpd.GeoDataFrame(geometry=[multi], crs="EPSG:4326")
        result = load_boundary(gdf)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# boundary_bbox
# ---------------------------------------------------------------------------

class TestBoundaryBbox:
    def test_bbox_matches_geometry(self, simple_gdf):
        from geointerpo.boundaries import load_boundary, boundary_bbox
        boundary = load_boundary(simple_gdf)
        min_lon, min_lat, max_lon, max_lat = boundary_bbox(boundary)
        assert min_lon == pytest.approx(SIMPLE_BBOX[0], abs=1e-6)
        assert min_lat == pytest.approx(SIMPLE_BBOX[1], abs=1e-6)
        assert max_lon == pytest.approx(SIMPLE_BBOX[2], abs=1e-6)
        assert max_lat == pytest.approx(SIMPLE_BBOX[3], abs=1e-6)

    def test_bbox_is_tuple_of_four_floats(self, simple_gdf):
        from geointerpo.boundaries import load_boundary, boundary_bbox
        boundary = load_boundary(simple_gdf)
        bbox = boundary_bbox(boundary)
        assert len(bbox) == 4
        assert all(isinstance(v, float) for v in bbox)


# ---------------------------------------------------------------------------
# padding
# ---------------------------------------------------------------------------

class TestPadding:
    def test_padding_expands_bbox(self, simple_gdf):
        from geointerpo.boundaries import load_boundary, boundary_bbox
        base = load_boundary(simple_gdf, padding_deg=0.0)
        padded = load_boundary(simple_gdf, padding_deg=0.5)
        b_base = boundary_bbox(base)
        b_padded = boundary_bbox(padded)
        assert b_padded[0] < b_base[0]   # min_lon smaller
        assert b_padded[1] < b_base[1]   # min_lat smaller
        assert b_padded[2] > b_base[2]   # max_lon larger
        assert b_padded[3] > b_base[3]   # max_lat larger


# ---------------------------------------------------------------------------
# Pipeline integration (offline — geometry passthrough, no network)
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    def test_pipeline_with_geometry_boundary(self, square_geom):
        from geointerpo import Pipeline
        result = Pipeline(
            boundary=square_geom,
            variable="temperature",
            source="sample",
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.boundary is not None
        assert result.grid is not None

    def test_pipeline_with_geodataframe_boundary(self, simple_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            boundary=simple_gdf,
            variable="temperature",
            source="sample",
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.boundary is not None

    def test_pipeline_location_overrides_with_boundary(self, simple_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            location=SIMPLE_BBOX,
            boundary=simple_gdf,
            variable="temperature",
            source="sample",
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        assert result.boundary is not None
        assert result.grid is not None

    def test_pipeline_no_location_no_boundary_raises(self):
        from geointerpo import Pipeline
        with pytest.raises(ValueError):
            Pipeline(variable="temperature", method="idw")

    def test_boundary_polygon_property(self, simple_gdf):
        from geointerpo import Pipeline
        result = Pipeline(
            boundary=simple_gdf,
            variable="temperature",
            source="sample",
            method="idw",
            resolution=0.1,
            cv_folds=3,
        ).run()
        poly = result.boundary_polygon()
        assert poly is not None
        assert poly.is_valid


# ---------------------------------------------------------------------------
# Unknown provider — graceful error
# ---------------------------------------------------------------------------

class TestProviderErrors:
    def test_unknown_provider_raises(self, simple_gdf):
        from geointerpo.boundaries import load_boundary
        # Only string place names hit the provider; GeoDataFrame skips it
        with pytest.raises(ValueError, match="Unknown boundary provider"):
            from geointerpo.boundaries import resolve_place
            resolve_place("Calgary", provider="nonexistent")
