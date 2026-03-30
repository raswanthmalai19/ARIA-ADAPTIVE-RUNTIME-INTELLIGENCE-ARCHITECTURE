"""ARIA Controller module — Model inference with adaptive execution."""
from aria.controller.engine import ModelEngine, ExecutionMode, GenerationResult
from aria.controller.formatter import PromptFormatter
from aria.controller.adaptive_model import AdaptiveModelWrapper
from aria.controller.cascade import ModelCascade
from aria.controller.speculative import SelfSpeculativeDecoder
from aria.controller.attention_profiler import AttentionProfiler

__all__ = [
    "ModelEngine",
    "ExecutionMode",
    "GenerationResult",
    "PromptFormatter",
    "AdaptiveModelWrapper",
    "ModelCascade",
    "SelfSpeculativeDecoder",
    "AttentionProfiler",
]
