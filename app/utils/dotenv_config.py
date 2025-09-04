from dotenv import load_dotenv
import os

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
STATIC_GEO_URL = os.getenv("STATIC_GEO_URL")
STATIC_WEATHER_URL = os.getenv("STATIC_WEATHER_URL")
MCP_HOST = os.getenv("MCP_HOST")
MCP_PORT = os.getenv("MCP_PORT")
