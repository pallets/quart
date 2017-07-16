import asyncio
from typing import Any, List, Union

from quart.templating import (
    render_template as quart_render_template,
    render_template_string as quart_render_template_string,
)


def render_template(template_name_or_list: Union[str, List[str]], **context: Any) -> str:
    return asyncio.get_event_loop().sync_wait(  # type: ignore
        quart_render_template(template_name_or_list, **context),
    )


def render_template_string(source: str, **context: Any) -> str:
    return asyncio.get_event_loop().sync_wait(  # type: ignore
        quart_render_template_string(source, **context),
    )


__all__ = ('render_template', 'render_template_string')
