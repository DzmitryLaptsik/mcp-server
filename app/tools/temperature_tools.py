from schemas.temperature import TemperatureInput
from services.temperature_calculation_service import TemperatureService


def convert_temperature_tool(temperature_data: TemperatureInput):
    return TemperatureService.convert_temperature(temperature_data)
