import httpx
from schemas.weather import WeatherInput, WeatherResponse
from utils.dotenv_config import OPENWEATHER_API_KEY, STATIC_GEO_URL, STATIC_WEATHER_URL


class WeatherService:
    def __init__(self):
        self.api_key = OPENWEATHER_API_KEY
        self.static_geo_url = STATIC_GEO_URL
        self.static_weather_url = STATIC_WEATHER_URL
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY environment variable not set.")

    async def get_weather(self, location: WeatherInput) -> WeatherResponse:
        lat, lon, city_name, state, country = await self._resolve_location(location)
        temperature, description = await self._fetch_weather(lat, lon)
        return WeatherResponse(
            city=city_name,
            state=state,
            country=country,
            lat=lat,
            lon=lon,
            temperature=temperature,
            description=description,
        )

    async def _resolve_location(self, location: WeatherInput):
        if location.lat is not None and location.lon is not None:
            return location.lat, location.lon, location.city or "Unknown", location.state, location.country or "Unknown"

        if location.city:
            query = location.city
            if location.state:
                query += f",{location.state}"
            if location.country:
                query += f",{location.country}"

            geo_url = f"{self.static_geo_url}{query}&limit=5&appid={self.api_key}"
            async with httpx.AsyncClient() as client:
                response = await client.get(geo_url, timeout=10.0)
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

    async def _fetch_weather(self, lat: float, lon: float):
        weather_url = f"{self.static_weather_url}lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        async with httpx.AsyncClient() as client:
            response = await client.get(weather_url, timeout=10.0)
            response.raise_for_status()
            weather_data = response.json()

        return weather_data["main"]["temp"], weather_data["weather"][0]["main"]
