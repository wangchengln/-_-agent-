"""Core Tools factory — returns all tools for the Agent."""

from pathlib import Path
from typing import List

from langchain_core.tools import BaseTool

from .amap_poi_tool import create_amap_poi_tool
from .amap_route_tool import create_amap_route_tool
from .amap_weather_tool import create_amap_weather_tool
from .terminal_tool import create_terminal_tool
from .python_repl_tool import create_python_repl_tool
from .fetch_url_tool import create_fetch_url_tool
from .read_file_tool import create_read_file_tool
from .search_knowledge_tool import create_search_knowledge_tool
from .browser_use_tool import create_browser_use_tool
from .tavily_search_tool import create_tavily_search_tool


def get_all_tools(base_dir: Path) -> List[BaseTool]:
    """Create and return all core tools, sandboxed to base_dir where applicable."""
    return [
        create_terminal_tool(base_dir),
        create_python_repl_tool(),
        create_fetch_url_tool(),
        create_read_file_tool(base_dir),
        create_search_knowledge_tool(base_dir),
        create_browser_use_tool(),
        create_tavily_search_tool(),
        create_amap_poi_tool(),
        create_amap_weather_tool(),
        create_amap_route_tool(),
    ]
