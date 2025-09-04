from schemas.temperature import TemperatureInput, TemperatureOutput, TemperatureType


class TemperatureService:
    @staticmethod
    def convert_temperature(data: TemperatureInput) -> TemperatureOutput:
        if data.type == TemperatureType.CELSIUS:
            return TemperatureOutput(
                value=data.value * 9 / 5 + 32,
                type=TemperatureType.FAHRENHEIT
            )
        elif data.type == TemperatureType.FAHRENHEIT:
            return TemperatureOutput(
                value=(data.value - 32) * 5 / 9,
                type=TemperatureType.CELSIUS
            )
