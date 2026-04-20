# Contributing

## Setup

```bash
git clone https://github.com/homayounrezaie/geointerpo
cd geointerpo
pip install -e ".[dev]"
```

## Tests

```bash
# Offline only (fast, CI-safe)
pytest tests/ -m "not network and not gee" -v

# All tests (requires network)
pytest tests/ -v

# With coverage
pytest tests/ -m "not network and not gee" --cov=geointerpo --cov-report=term-missing
```

## Linting

```bash
ruff check geointerpo/
ruff format geointerpo/
```

## Docs (local preview)

```bash
pip install mkdocs mkdocs-material
mkdocs serve
# open http://127.0.0.1:8000
```

## Adding an interpolator

1. Create `geointerpo/interpolators/my_method.py` subclassing `BaseInterpolator`
2. Implement `_fit(xs, ys, values)` and `_predict(xs, ys)`
3. Set `_needs_metric = True` if the method requires metric (UTM) coordinates
4. Register in `geointerpo/pipeline.py`: add an entry to `_METHOD_ALIASES` and `mod_map`
5. Add a test in `tests/test_interpolators.py`

## Pull requests

- Keep PRs focused — one feature or fix per PR
- Run the offline test suite before opening a PR
- Add or update tests for any new behaviour
- Update `CHANGELOG.md` under `[Unreleased]`
