"""Parser Agent prompt assembly."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from domain.irf_state import ParserInput
from utils.encoding import safe_read_text

PROMPTS_DIR = Path(__file__).parent / "prompts"
PARSER_SYSTEM_PATH = PROMPTS_DIR / "parser_system.md"
PARSER_USER_TEMPLATE_PATH = PROMPTS_DIR / "parser_user.template.md"

MAX_SYSTEM_PROMPT_LENGTH = 24000


def _substitute(template: str, mapping: dict[str, str]) -> str:
    """Replace ``{{key}}`` placeholders without pulling in Jinja2."""
    result = template
    for key, value in mapping.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def load_parser_system_prompt(*, truncate: bool = True) -> str:
    """Load Parser system prompt from markdown file."""
    content = safe_read_text(PARSER_SYSTEM_PATH)
    if truncate and len(content) > MAX_SYSTEM_PROMPT_LENGTH:
        content = content[:MAX_SYSTEM_PROMPT_LENGTH] + "\n...[truncated]"
    return content


def load_parser_user_template() -> str:
    """Load Parser user message template."""
    return safe_read_text(PARSER_USER_TEMPLATE_PATH)


def build_parser_user_prompt(
    parser_input: ParserInput,
    *,
    max_feed_items: int = 5,
) -> str:
    """Render user message for a single Parser turn."""
    template = load_parser_user_template()
    mapping = {
        "round": str(parser_input.round),
        "command": parser_input.command,
        "preference_context": parser_input.preference_context(),
        "feed_context": parser_input.feed_context(max_items=max_feed_items),
        "history_context": parser_input.history_context(),
    }
    return _substitute(template, mapping)


def build_parser_messages(
    parser_input: ParserInput,
    *,
    max_feed_items: int = 5,
) -> list[BaseMessage]:
    """Build LangChain messages for ParserAgent.parse()."""
    return [
        SystemMessage(content=load_parser_system_prompt()),
        HumanMessage(
            content=build_parser_user_prompt(
                parser_input,
                max_feed_items=max_feed_items,
            )
        ),
    ]
