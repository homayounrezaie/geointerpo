# Data Sources API

All sources implement `BaseDataSource.fetch(bbox) -> GeoDataFrame`.

The returned GeoDataFrame always has:
- `geometry`: Point (lon, lat), CRS = EPSG:4326
- `value`: float scalar being interpolated
- `attrs["source"]`: source name string
- `attrs["variable"]`: variable name string

## MeteostatSource

```python
from geointerpo.sources import MeteostatSource

src = MeteostatSource(variable="tavg", start="2024-07-15", end="2024-07-15", freq="daily")
gdf = src.fetch(bbox=(5, 44, 25, 56))
```

| Parameter | Default | Description |
|---|---|---|
| `variable` | `"tavg"` | Daily: `tavg tmin tmax prcp snow wspd pres` / Hourly: `temp rhum prcp` |
| `start` | yesterday | Start date (str, date, datetime) |
| `end` | = start | End date |
| `freq` | `"daily"` | `"daily"`, `"hourly"`, `"monthly"` |

## OpenAQSource

```python
from geointerpo.sources import OpenAQSource

src = OpenAQSource(parameter="pm25", date_from="2024-01-15", date_to="2024-01-15")
gdf = src.fetch(bbox=(68, 20, 90, 35))
```

| Parameter | Default | Description |
|---|---|---|
| `parameter` | `"pm25"` | `pm25 pm10 o3 no2 so2 co` |
| `date_from` | yesterday | ISO date string |
| `date_to` | today | ISO date string |
| `limit` | 1000 | Max measurements |
| `api_key` | None | Optional OpenAQ API key for higher rate limits |

## OpenMeteoSource

```python
from geointerpo.sources import OpenMeteoSource

src = OpenMeteoSource(variable="precipitation_sum", date="2024-01-10", n_points=64)
gdf = src.fetch(bbox=(-10, 35, 30, 55))
```

| Parameter | Default | Description |
|---|---|---|
| `variable` | `"temperature_2m_mean"` | Any Open-Meteo daily variable |
| `date` | 2 days ago | ISO date string |
| `n_points` | 25 | Number of grid sample points |

Common variables: `temperature_2m_mean`, `precipitation_sum`, `wind_speed_10m_max`, `et0_fao_evapotranspiration`
