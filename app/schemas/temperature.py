from enum import Enum

from pydantic import BaseModel, Field


class TemperatureType(Enum):
    CELSIUS = 'Celsius'
    FAHRENHEIT = 'Fahrenheit'


class TemperatureInput(BaseModel):
    value: float = Field(..., description="Temperature value")
    type: TemperatureType


class TemperatureOutput(BaseModel):
    value: float
    type: TemperatureType
