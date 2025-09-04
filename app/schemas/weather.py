from typing import Optional
from pydantic import BaseModel, Field


# Input schema
class WeatherInput(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="Region, state, or oblast")
    country: Optional[str] = Field(None, description="Country ISO code")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")


# Response schema
class WeatherResponse(BaseModel):
    city: str = Field(..., description="Resolved city name")
    state: Optional[str] = Field(None, description="Region, state, or oblast")
    country: str = Field(..., description="Country ISO code")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    temperature: float = Field(..., description="Current temperature in Celsius")
    description: str = Field(..., description="Weather description")
