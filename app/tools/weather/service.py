from collections import Counter

import httpx

from tools.weather.schemas import (
    ForecastDay,
    ForecastInput,
    ForecastResponse,
    WeatherInput,
    WeatherResponse,
)
from utils.dotenv_config import settings


class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.static_geo_url = settings.STATIC_GEO_URL
        self.static_weather_url = settings.STATIC_WEATHER_URL
        self.static_forecast_url = settings.STATIC_FORECAST_URL
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY environment variable not set.")

    async def get_weather(self, location: WeatherInput) -> WeatherResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            lat, lon, city_name, state, country = await self._resolve_location(client, location)
            temperature, description = await self._fetch_weather(client, lat, lon)
        return WeatherResponse(
            city=city_name,
            state=state,
            country=country,
            lat=lat,
            lon=lon,
            temperature=temperature,
            description=description,
        )

    async def get_forecast(self, input: ForecastInput) -> ForecastResponse:
        location = WeatherInput(
            city=input.city,
            state=input.state,
            country=input.country,
            lat=input.lat,
            lon=input.lon,
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            lat, lon, city_name, _, country = await self._resolve_location(client, location)
            forecast_data = await self._fetch_forecast(client, lat, lon)
        days = self._aggregate_forecast(forecast_data, input.days)
        return ForecastResponse(city=city_name, country=country, days=days)

    async def _resolve_location(self, client: httpx.AsyncClient, location: WeatherInput):
        if location.lat is not None and location.lon is not None:
            return location.lat, location.lon, location.city or "Unknown", location.state, location.country or "Unknown"

        if location.city:
            query = location.city
            if location.state:
                query += f",{location.state}"
            if location.country:
                query += f",{location.country}"

            response = await client.get(
                self.static_geo_url,
                params={"q": query, "limit": 5, "appid": self.api_key},
            )
            response.raise_for_status()
            geo_data = response.json()

            if not geo_data:
                raise ValueError(f"City '{query}' not found.")

            city_info = geo_data[0]
            return (
                city_info.get("lat"),
                city_info.get("lon"),
                city_info.get("name"),
                city_info.get("state"),
                city_info.get("country"),
            )

        raise ValueError("You must provide either lat/lon or city name.")

    async def _fetch_weather(self, client: httpx.AsyncClient, lat: float, lon: float):
        response = await client.get(
            self.static_weather_url,
            params={"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"},
        )
        response.raise_for_status()
        weather_data = response.json()

        return weather_data["main"]["temp"], weather_data["weather"][0]["main"]

    async def _fetch_forecast(self, client: httpx.AsyncClient, lat: float, lon: float) -> list[dict]:
        response = await client.get(
            self.static_forecast_url,
            params={"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"},
        )
        response.raise_for_status()
        return response.json()["list"]

    def _aggregate_forecast(self, forecast_list: list[dict], days: int) -> list[ForecastDay]:
        daily: dict[str, list[dict]] = {}
        for entry in forecast_list:
            date = entry["dt_txt"].split(" ")[0]
            daily.setdefault(date, []).append(entry)

        result = []
        for date, entries in list(daily.items())[:days]:
            temps = [e["main"]["temp"] for e in entries]
            descriptions = [e["weather"][0]["main"] for e in entries]
            rain_entries = sum(1 for e in entries if e.get("pop", 0) > 0.3)
            most_common_desc = Counter(descriptions).most_common(1)[0][0]

            result.append(ForecastDay(
                date=date,
                temp_min=round(min(temps), 1),
                temp_max=round(max(temps), 1),
                description=most_common_desc,
                rain_chance=round((rain_entries / len(entries)) * 100),
            ))

        return result
