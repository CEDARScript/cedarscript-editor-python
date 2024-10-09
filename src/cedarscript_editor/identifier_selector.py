from typing import Callable

from cedarscript_ast_parser import Marker

import logging

from cedarscript_editor.python_identifier_finder import find_python_identifier
from cedarscript_editor.text_editor_kit import IdentifierBoundaries

_log = logging.getLogger(__name__)


def select_finder(
    root_path: str, file_name: str, source: str
) -> Callable[[str, str, str, Marker], IdentifierBoundaries | None]:
    # TODO
    _log.info("[select_finder] Python selected")
    return find_python_identifier
