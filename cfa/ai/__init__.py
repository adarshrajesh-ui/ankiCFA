# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA exam-prep AI foundation.

See :mod:`cfa.ai.llm_client` for the single reusable OpenAI client. All AI
features route through it and degrade to deterministic fallbacks when AI is off
(no ``OPENAI_API_KEY``).
"""

from cfa.ai.llm_client import (  # noqa: F401
    CompletionResult,
    complete,
    reset_usage,
    usage_so_far,
)

__all__ = ["complete", "usage_so_far", "reset_usage", "CompletionResult"]
