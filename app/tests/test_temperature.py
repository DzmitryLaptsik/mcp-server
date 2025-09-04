from schemas.temperature import TemperatureInput, TemperatureOutput, TemperatureType
from services.temperature_calculation_service import TemperatureService


def test_convert_celsius_to_fahrenheit():
    input_data = TemperatureInput(value=0, type=TemperatureType.CELSIUS)
    expected_output = TemperatureOutput(value=32.0, type=TemperatureType.FAHRENHEIT)

    result = TemperatureService.convert_temperature(input_data)
    assert result == expected_output


def test_convert_fahrenheit_to_celsius():
    input_data = TemperatureInput(value=32, type=TemperatureType.FAHRENHEIT)
    expected_output = TemperatureOutput(value=0.0, type=TemperatureType.CELSIUS)

    result = TemperatureService.convert_temperature(input_data)
    assert result == expected_output


def test_convert_fahrenheit_to_celsius_decimal():
    input_data = TemperatureInput(value=68, type=TemperatureType.FAHRENHEIT)
    expected_output = TemperatureOutput(value=20.0, type=TemperatureType.CELSIUS)

    result = TemperatureService.convert_temperature(input_data)
    assert result == expected_output


def test_convert_celsius_to_fahrenheit_decimal():
    input_data = TemperatureInput(value=20, type=TemperatureType.CELSIUS)
    expected_output = TemperatureOutput(value=68.0, type=TemperatureType.FAHRENHEIT)

    result = TemperatureService.convert_temperature(input_data)
    assert result == expected_output
