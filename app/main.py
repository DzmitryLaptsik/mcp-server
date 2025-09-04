from mcp.server.fastmcp import FastMCP

from tools.temperature_tools import convert_temperature_tool
from tools.weather_tools import get_weather_tool
from utils.dotenv_config import MCP_HOST, MCP_PORT

mcp = FastMCP("MCP", dependencies=["requests", "httpx"], host=MCP_HOST, port=MCP_PORT)

mcp.add_tool(get_weather_tool, name="get_weather", description="Get current weather for a location. Also get the "
                                                               "temperature in Celsius.")
mcp.add_tool(convert_temperature_tool, name="convert_temperature", description="Converts temperatures between Celsius "
                                                                               "and Fahrenheit.")

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
