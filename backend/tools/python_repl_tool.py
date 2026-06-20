"""Python REPL Tool — wraps LangChain experimental PythonREPLTool with UTF-8 default."""

import io
import sys
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class PythonReplInput(BaseModel):
    code: str = Field(description="Python code to execute")


class Utf8PythonReplTool(BaseTool):
    """Python REPL that forces UTF-8 for all I/O operations."""

    name: str = "python_repl"
    description: str = (
        "Execute Python code in an interactive REPL environment. "
        "Use this for calculations, data processing, running scripts, "
        "and any task that benefits from programmatic execution. "
        "Input should be valid Python code. Use print() to see output. "
        "IMPORTANT: When writing files, always specify encoding='utf-8' in open()."
    )
    args_schema: Type[BaseModel] = PythonReplInput

    def _run(self, code: str) -> str:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            exec(code, {"__builtins__": __builtins__})
            output = buf.getvalue()
        except Exception as e:
            output = f"Error: {type(e).__name__}: {e}"
        finally:
            sys.stdout = old_stdout

        if not output.strip():
            output = "(code executed with no output)"
        if len(output) > 5000:
            output = output[:5000] + "\n...[truncated]"
        return output


def create_python_repl_tool() -> BaseTool:
    return Utf8PythonReplTool()
