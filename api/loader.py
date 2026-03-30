"""
Async Model Loader

Loads models in background without blocking the main thread.
Allows FastAPI to respond immediately while warming up the engine.
"""

import asyncio
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger("aria.loader")


class LoaderState(str, Enum):
    """States of the model loader."""
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class AsyncModelLoader:
    """Non-blocking model loader for FastAPI startup."""

    def __init__(self):
        self.state = LoaderState.IDLE
        self.progress = 0.0  # 0.0 to 1.0
        self.error_message: Optional[str] = None
        self._engine = None
        self._load_task: Optional[asyncio.Task] = None

    async def start_loading(self, engine):
        """Start loading the model in background."""
        if self.state != LoaderState.IDLE:
            logger.warning("Loader already running (state=%s)", self.state)
            return

        self._engine = engine
        self.state = LoaderState.LOADING
        self.progress = 0.0

        # Schedule the actual load in the background
        self._load_task = asyncio.create_task(self._load())

    async def _load(self):
        """Background task to load the model."""
        try:
            logger.info("Starting async model load...")
            
            # Mark starting
            self.progress = 0.1
            
            # Run the blocking load in a thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._engine.initialize
            )
            
            # Mark complete
            self.progress = 1.0
            self.state = LoaderState.READY
            logger.info("Model loaded successfully")

        except Exception as e:
            self.error_message = str(e)
            self.state = LoaderState.ERROR
            logger.error("Model load failed: %s", e)

    async def wait_ready(self, timeout_s: float = 300.0):
        """Wait for model to be ready, with timeout."""
        if self.state == LoaderState.READY:
            return True

        if self.state == LoaderState.ERROR:
            raise RuntimeError(f"Model load error: {self.error_message}")

        try:
            if self._load_task:
                await asyncio.wait_for(self._load_task, timeout=timeout_s)
            return self.state == LoaderState.READY
        except asyncio.TimeoutError:
            logger.error("Model load timeout after %.0fs", timeout_s)
            return False

    def is_ready(self) -> bool:
        """Check if model is ready for inference."""
        return self.state == LoaderState.READY

    def get_status(self) -> dict:
        """Get current loader status."""
        return {
            "state": self.state.value,
            "progress": self.progress,
            "error": self.error_message,
            "ready": self.is_ready(),
        }
