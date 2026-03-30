#!/usr/bin/env python3
"""
ARIA macOS Application Launcher

Handles:
- Background runtime service management
- GUI window creation and management
- System tray integration
- Auto-update checks
- Crash recovery
"""

import sys
import os
import json
import subprocess
import threading
import time
import signal
import logging
from pathlib import Path
from typing import Optional
import sqlite3
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / 'Library/Logs/ARIA/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('aria.app')

# Ensure log directory exists
Path.home().joinpath('Library/Logs/ARIA').mkdir(parents=True, exist_ok=True)


class ARIAApp:
    """Main ARIA application manager."""
    
    VERSION = "0.2.0"
    RUNTIME_PORT = 8000
    
    def __init__(self):
        self.runtime_process: Optional[subprocess.Popen] = None
        self.runtime_pid_file = Path.home() / '.aria' / 'runtime.pid'
        self.config_dir = Path.home() / '.aria'
        self.db_path = self.config_dir / 'aria.db'
        
        # Create config directory
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"ARIA App v{self.VERSION} initializing...")
    
    def _init_db(self):
        """Initialize application database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY,
                query_text TEXT,
                response_text TEXT,
                mode TEXT,
                latency_ms INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_runtime(self, debug: bool = False) -> bool:
        """Start the ARIA runtime service in background."""
        logger.info("Starting ARIA Runtime Service...")
        
        try:
            # Check if already running
            if self._is_runtime_running():
                logger.info("Runtime already running")
                return True
            
            # Start runtime
            cmd = ["aria-runtime"]
            if debug:
                cmd.append("--dev")
            
            self.runtime_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for proper cleanup
            )
            
            # Save PID
            self.runtime_pid_file.write_text(str(self.runtime_process.pid))
            
            # Wait for service to be ready
            if self._wait_for_runtime(timeout=60):
                logger.info(f"Runtime started successfully (PID: {self.runtime_process.pid})")
                return True
            else:
                logger.error("Runtime failed to start in time")
                self.stop_runtime()
                return False
                
        except Exception as e:
            logger.error(f"Failed to start runtime: {e}")
            return False
    
    def _is_runtime_running(self) -> bool:
        """Check if runtime is already running."""
        if not self.runtime_pid_file.exists():
            return False
        
        try:
            pid = int(self.runtime_pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)  # Raises OSError if process doesn't exist
            return True
        except (ValueError, OSError, ProcessLookupError):
            return False
    
    def _wait_for_runtime(self, timeout: int = 60) -> bool:
        """Wait for runtime service to be healthy."""
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = urllib.request.urlopen(f'http://localhost:{self.RUNTIME_PORT}/health', timeout=2)
                if response.status == 200:
                    return True
            except (urllib.error.URLError, urllib.error.HTTPError):
                pass
            
            time.sleep(1)
        
        return False
    
    def stop_runtime(self):
        """Stop the ARIA runtime service."""
        logger.info("Stopping ARIA Runtime Service...")
        
        try:
            if self.runtime_process:
                # Use process group to terminate all child processes
                try:
                    os.killpg(os.getpgid(self.runtime_process.pid), signal.SIGTERM)
                except:
                    self.runtime_process.terminate()
                
                self.runtime_process.wait(timeout=5)
            
            # Clean up PID file
            if self.runtime_pid_file.exists():
                self.runtime_pid_file.unlink()
            
            logger.info("Runtime stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping runtime: {e}")
    
    def open_gui(self):
        """Open the ARIA GUI in the default browser."""
        import webbrowser
        
        gui_url = f'http://localhost:{self.RUNTIME_PORT}/docs'
        logger.info(f"Opening GUI: {gui_url}")
        webbrowser.open(gui_url)
    
    def save_metric(self, query: str, response: str, mode: str, latency_ms: int):
        """Save query metric to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO metrics (query_text, response_text, mode, latency_ms) VALUES (?, ?, ?, ?)',
                (query, response, mode, latency_ms)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save metric: {e}")
    
    def get_metrics(self, limit: int = 50) -> list:
        """Retrieve recent metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT query_text, response_text, mode, latency_ms, timestamp FROM metrics ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            metrics = cursor.fetchall()
            conn.close()
            return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    def check_for_updates(self) -> Optional[str]:
        """Check if a new version is available."""
        # This would check GitHub releases or your update server
        logger.info("Checking for updates...")
        # TODO: Implement update checking
        return None
    
    def cleanup(self):
        """Cleanup on exit."""
        logger.info("ARIA App shutting down...")
        self.stop_runtime()
    
    def run(self):
        """Run the application."""
        # Set up signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self.cleanup())
        signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
        
        try:
            # Start runtime
            if not self.start_runtime(debug=False):
                logger.error("Failed to start runtime")
                return False
            
            # Open GUI
            self.open_gui()
            
            # Keep app running
            logger.info("ARIA App is running. Press Ctrl+C to quit.")
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.cleanup()


def main():
    """Entry point for macOS app."""
    app = ARIAApp()
    app.run()


if __name__ == '__main__':
    main()
