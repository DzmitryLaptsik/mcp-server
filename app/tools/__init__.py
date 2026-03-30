import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP
from utils.dotenv_config import settings

mcp = FastMCP("MCP", dependencies=["httpx"], host=settings.MCP_HOST, port=settings.MCP_PORT)

# Auto-register all tool modules in this package.
# Any .py file or sub-package under tools/ that uses @mcp.tool() will be discovered.
for module_info in pkgutil.iter_modules(__path__):
    importlib.import_module(f".{module_info.name}", __package__)
