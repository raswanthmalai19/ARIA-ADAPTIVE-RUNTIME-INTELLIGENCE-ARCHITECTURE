"""
ARIA Conversation History Manager
Persists conversations to SQLite database
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import threading

logger = logging.getLogger("aria.history")


class ConversationDB:
    """SQLite-backed conversation storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        if db_path is None:
            # Store in user's home directory
            home = Path.home()
            aria_dir = home / ".aria"
            aria_dir.mkdir(exist_ok=True)
            db_path = aria_dir / "conversations.db"
        
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        
        # Create tables if they don't exist
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL DEFAULT 'New Conversation',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model TEXT DEFAULT 'qwen2.5-3b',
                    summary TEXT
                )
            ''')
            
            # Create messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    mode TEXT DEFAULT 'adaptive',
                    tokens INTEGER,
                    latency_ms FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_id ON messages(conversation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created ON conversations(created_at)')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()
    
    def create_conversation(self, title: str = "New Conversation", 
                          model: str = "qwen2.5-3b") -> int:
        """Create new conversation, return ID."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO conversations (title, model)
                    VALUES (?, ?)
                ''', (title, model))
                
                conv_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created conversation {conv_id}: {title}")
                return conv_id
        
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise
        finally:
            conn.close()
    
    def add_message(self, conversation_id: int, role: str, content: str,
                   mode: str = "adaptive", tokens: int = 0, 
                   latency_ms: float = 0) -> int:
        """Add message to conversation."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO messages 
                    (conversation_id, role, content, mode, tokens, latency_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (conversation_id, role, content, mode, tokens, latency_ms))
                
                # Update conversation timestamp
                cursor.execute('''
                    UPDATE conversations 
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (conversation_id,))
                
                msg_id = cursor.lastrowid
                conn.commit()
                
                return msg_id
        
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise
        finally:
            conn.close()
    
    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM conversations WHERE id=?', 
                             (conversation_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        finally:
            conn.close()
    
    def get_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Get all messages in conversation."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM messages 
                    WHERE conversation_id=?
                    ORDER BY created_at ASC
                ''', (conversation_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent conversations."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, title, created_at, updated_at, model
                    FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete conversation and all messages."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Delete messages first
                cursor.execute('DELETE FROM messages WHERE conversation_id=?',
                             (conversation_id,))
                
                # Delete conversation
                cursor.execute('DELETE FROM conversations WHERE id=?',
                             (conversation_id,))
                
                conn.commit()
                logger.info(f"Deleted conversation {conversation_id}")
                
                return cursor.rowcount > 0
        finally:
            conn.close()
    
    def export_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """Export conversation as JSON."""
        try:
            conv = self.get_conversation(conversation_id)
            if not conv:
                return None
            
            messages = self.get_messages(conversation_id)
            
            return {
                "id": conv["id"],
                "title": conv["title"],
                "model": conv["model"],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"],
                "messages": messages
            }
        except Exception as e:
            logger.error(f"Failed to export conversation: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM conversations')
                num_conversations = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM messages')
                num_messages = cursor.fetchone()[0]
                
                cursor.execute('SELECT SUM(tokens) FROM messages')
                total_tokens = cursor.fetchone()[0] or 0
                
                return {
                    "conversations": num_conversations,
                    "messages": num_messages,
                    "total_tokens": total_tokens
                }
        finally:
            conn.close()


# Global database instance
_db_instance = None

def get_db() -> ConversationDB:
    """Get global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ConversationDB()
    return _db_instance
