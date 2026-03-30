from enum import Enum

from pydantic import BaseModel, Field

from tools import mcp


class TemperatureType(Enum):
    CELSIUS = "Celsius"
    FAHRENHEIT = "Fahrenheit"


class TemperatureInput(BaseModel):
    value: float = Field(..., description="Temperature value")
    type: TemperatureType


class TemperatureOutput(BaseModel):
    value: float
    type: TemperatureType


@mcp.tool(description="Converts temperatures between Celsius and Fahrenheit.")
def convert_temperature(temperature_data: TemperatureInput) -> TemperatureOutput:
    if temperature_data.type == TemperatureType.CELSIUS:
        return TemperatureOutput(
            value=temperature_data.value * 9 / 5 + 32,
            type=TemperatureType.FAHRENHEIT,
        )
    elif temperature_data.type == TemperatureType.FAHRENHEIT:
        return TemperatureOutput(
            value=(temperature_data.value - 32) * 5 / 9,
            type=TemperatureType.CELSIUS,
        )
    raise ValueError(f"Unsupported temperature type: {temperature_data.type}")
