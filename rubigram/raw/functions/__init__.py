"""Payload builders that need logic beyond field serialization.

The declarative :mod:`rubigram.raw.methods` classes cover plain inputs; the
helpers here build message metadata from parse modes, ``file_inline`` blocks,
``updated_parameters`` lists and the request envelopes.
"""

from .envelope import build_data_object, build_plain_payload, build_service_client_info, build_web_client_info
from .files import build_file_inline, guess_upload_mime
from .messages import build_message_metadata, entities_to_metadata, parse_html, parse_markdown
from .settings import build_settings_input, build_updated_parameters

__all__ = [
    "build_data_object",
    "build_file_inline",
    "build_message_metadata",
    "build_plain_payload",
    "build_service_client_info",
    "build_settings_input",
    "build_updated_parameters",
    "build_web_client_info",
    "entities_to_metadata",
    "guess_upload_mime",
    "parse_html",
    "parse_markdown",
]
