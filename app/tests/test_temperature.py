import pytest

from tools.temperature import (
    TemperatureInput,
    TemperatureOutput,
    TemperatureType,
    convert_temperature,
)


def test_convert_celsius_to_fahrenheit():
    input_data = TemperatureInput(value=0, type=TemperatureType.CELSIUS)
    expected_output = TemperatureOutput(value=32.0, type=TemperatureType.FAHRENHEIT)

    result = convert_temperature(temperature_data=input_data)
    assert result == expected_output


def test_convert_fahrenheit_to_celsius():
    input_data = TemperatureInput(value=32, type=TemperatureType.FAHRENHEIT)
    expected_output = TemperatureOutput(value=0.0, type=TemperatureType.CELSIUS)

    result = convert_temperature(temperature_data=input_data)
    assert result == expected_output


def test_convert_fahrenheit_to_celsius_decimal():
    input_data = TemperatureInput(value=68, type=TemperatureType.FAHRENHEIT)
    expected_output = TemperatureOutput(value=20.0, type=TemperatureType.CELSIUS)

    result = convert_temperature(temperature_data=input_data)
    assert result == expected_output


def test_convert_celsius_to_fahrenheit_decimal():
    input_data = TemperatureInput(value=20, type=TemperatureType.CELSIUS)
    expected_output = TemperatureOutput(value=68.0, type=TemperatureType.FAHRENHEIT)

    result = convert_temperature(temperature_data=input_data)
    assert result == expected_output
