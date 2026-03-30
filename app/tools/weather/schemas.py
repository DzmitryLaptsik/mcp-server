from typing import Optional

from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="Region, state, or oblast")
    country: Optional[str] = Field(None, description="Country ISO code")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")


class WeatherResponse(BaseModel):
    city: str = Field(..., description="Resolved city name")
    state: Optional[str] = Field(None, description="Region, state, or oblast")
    country: str = Field(..., description="Country ISO code")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    temperature: float = Field(..., description="Current temperature in Celsius")
    description: str = Field(..., description="Weather description")


class ForecastInput(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="Region, state, or oblast")
    country: Optional[str] = Field(None, description="Country ISO code")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")
    days: int = Field(3, ge=1, le=5, description="Number of days to forecast (1-5)")


class ForecastDay(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    temp_min: float = Field(..., description="Minimum temperature in Celsius")
    temp_max: float = Field(..., description="Maximum temperature in Celsius")
    description: str = Field(..., description="Most common weather description for the day")
    rain_chance: int = Field(..., description="Chance of rain as percentage (0-100)")


class ForecastResponse(BaseModel):
    city: str = Field(..., description="Resolved city name")
    country: str = Field(..., description="Country ISO code")
    days: list[ForecastDay] = Field(..., description="Daily forecast breakdown")
