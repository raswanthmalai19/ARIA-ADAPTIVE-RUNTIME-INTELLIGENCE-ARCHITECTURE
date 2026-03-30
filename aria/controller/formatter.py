"""
ARIA Prompt Formatter

Handles prompt formatting and chat template application.
Ensures consistent prompt structure across all execution modes.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("aria.controller.formatter")


class PromptFormatter:
    """
    Formats user queries into model-ready prompts using the model's
    chat template.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are a helpful, accurate, and concise AI assistant. "
        "Provide clear, well-structured responses. "
        "Be direct and informative."
    )

    TASK_SYSTEM_PROMPTS = {
        "factual": (
            "You are a knowledgeable assistant. Provide accurate, concise "
            "factual answers. Be direct — no unnecessary elaboration."
        ),
        "reasoning": (
            "You are an analytical assistant skilled in logical reasoning. "
            "Break down complex problems step by step. Show your reasoning "
            "clearly and reach well-supported conclusions."
        ),
        "creative": (
            "You are a creative writing assistant. Produce engaging, "
            "original, and well-crafted creative content. Be vivid "
            "and imaginative."
        ),
        "code": (
            "You are an expert programming assistant. Write clean, "
            "well-documented, production-quality code. Include comments "
            "for complex logic. Prefer practical, working solutions."
        ),
        "conversation": (
            "You are a friendly conversational AI. Be warm, concise, "
            "and natural in your responses."
        ),
        "math": (
            "You are a mathematics expert. Solve problems step by step, "
            "showing all work clearly. Be precise with notation and "
            "verify your answers."
        ),
        "instruction": (
            "You are a clear and thorough instruction provider. "
            "Give step-by-step guidance that is easy to follow. "
            "Be practical and comprehensive."
        ),
    }

    def __init__(self, tokenizer=None):
        self._tokenizer = tokenizer

    def set_tokenizer(self, tokenizer) -> None:
        """Set/update the tokenizer (called after model load)."""
        self._tokenizer = tokenizer

    def format(
        self,
        query: str,
        task_type: str = "factual",
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Format a query into a model-ready prompt string.

        Uses the model's chat template if available, otherwise
        falls back to a generic format.
        """
        if system_prompt is None:
            system_prompt = self.TASK_SYSTEM_PROMPTS.get(
                task_type, self.DEFAULT_SYSTEM_PROMPT
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        if self._tokenizer is not None and hasattr(self._tokenizer, "apply_chat_template"):
            try:
                formatted = self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                return formatted
            except Exception as e:
                logger.warning("Chat template failed, using fallback: %s", e)

        return self._fallback_format(system_prompt, query)

    def _fallback_format(self, system_prompt: str, query: str) -> str:
        """Simple fallback format when no chat template is available."""
        return f"System: {system_prompt}\n\nUser: {query}\n\nAssistant:"
