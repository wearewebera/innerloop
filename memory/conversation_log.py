"""SQLite-based conversation logger for persistent history."""

import aiosqlite
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import structlog

logger = structlog.get_logger()


class ConversationLogger:
    """SQLite logger for conversation history and agent interactions."""
    
    def __init__(self, db_path: str = "conversation_history.db"):
        self.db_path = db_path
        self.logger = logger.bind(component="conversation_logger")
        self._db = None
    
    async def initialize(self):
        """Initialize the database and create tables."""
        self._db = await aiosqlite.connect(self.db_path)
        
        # Create tables
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                speaker TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'conversation',
                metadata TEXT
            )
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS agent_thoughts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent_id TEXT NOT NULL,
                thought_type TEXT NOT NULL,
                content TEXT NOT NULL,
                priority REAL DEFAULT 0.5,
                metadata TEXT
            )
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                priority REAL DEFAULT 0.5,
                metadata TEXT
            )
        """)
        
        # Create indices
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session 
            ON conversations(session_id)
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
            ON conversations(timestamp)
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_thoughts_agent 
            ON agent_thoughts(agent_id)
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_sender 
            ON agent_messages(sender)
        """)
        
        await self._db.commit()
        self.logger.info("Conversation logger initialized", db_path=self.db_path)
    
    async def log_conversation(self, session_id: str, speaker: str, 
                             content: str, message_type: str = "conversation",
                             metadata: Optional[Dict[str, Any]] = None):
        """Log a conversation entry."""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            await self._db.execute("""
                INSERT INTO conversations 
                (session_id, speaker, content, message_type, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, speaker, content, message_type, metadata_json))
            
            await self._db.commit()
            
            self.logger.debug("Conversation logged",
                            session_id=session_id,
                            speaker=speaker,
                            type=message_type)
            
        except Exception as e:
            self.logger.error("Failed to log conversation", error=str(e))
    
    async def log_thought(self, agent_id: str, thought_type: str,
                         content: str, priority: float = 0.5,
                         metadata: Optional[Dict[str, Any]] = None):
        """Log an agent thought."""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            await self._db.execute("""
                INSERT INTO agent_thoughts
                (agent_id, thought_type, content, priority, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, thought_type, content, priority, metadata_json))
            
            await self._db.commit()
            
        except Exception as e:
            self.logger.error("Failed to log thought", error=str(e))
    
    async def log_agent_message(self, sender: str, recipient: str,
                               message_type: str, content: str,
                               priority: float = 0.5,
                               metadata: Optional[Dict[str, Any]] = None):
        """Log an inter-agent message."""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            await self._db.execute("""
                INSERT INTO agent_messages
                (sender, recipient, message_type, content, priority, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sender, recipient, message_type, content, priority, metadata_json))
            
            await self._db.commit()
            
        except Exception as e:
            self.logger.error("Failed to log agent message", error=str(e))
    
    async def get_conversation_history(self, session_id: str,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        try:
            cursor = await self._db.execute("""
                SELECT timestamp, speaker, content, message_type, metadata
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            rows = await cursor.fetchall()
            
            history = []
            for row in reversed(rows):  # Reverse to get chronological order
                entry = {
                    'timestamp': row[0],
                    'speaker': row[1],
                    'content': row[2],
                    'message_type': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {}
                }
                history.append(entry)
            
            return history
            
        except Exception as e:
            self.logger.error("Failed to get conversation history", error=str(e))
            return []
    
    async def get_agent_thoughts(self, agent_id: str,
                               thought_type: Optional[str] = None,
                               since: Optional[datetime] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """Get thoughts from a specific agent."""
        try:
            query = """
                SELECT timestamp, thought_type, content, priority, metadata
                FROM agent_thoughts
                WHERE agent_id = ?
            """
            params = [agent_id]
            
            if thought_type:
                query += " AND thought_type = ?"
                params.append(thought_type)
            
            if since:
                query += " AND timestamp > ?"
                params.append(since.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = await self._db.execute(query, params)
            rows = await cursor.fetchall()
            
            thoughts = []
            for row in rows:
                thought = {
                    'timestamp': row[0],
                    'thought_type': row[1],
                    'content': row[2],
                    'priority': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {}
                }
                thoughts.append(thought)
            
            return thoughts
            
        except Exception as e:
            self.logger.error("Failed to get agent thoughts", error=str(e))
            return []
    
    async def get_agent_messages(self, agent_id: str,
                                role: str = "both",  # "sender", "recipient", "both"
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages sent or received by an agent."""
        try:
            if role == "sender":
                query = "SELECT * FROM agent_messages WHERE sender = ?"
            elif role == "recipient":
                query = "SELECT * FROM agent_messages WHERE recipient = ?"
            else:  # both
                query = "SELECT * FROM agent_messages WHERE sender = ? OR recipient = ?"
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            
            if role == "both":
                cursor = await self._db.execute(query, (agent_id, agent_id, limit))
            else:
                cursor = await self._db.execute(query, (agent_id, limit))
            
            rows = await cursor.fetchall()
            
            messages = []
            for row in rows:
                message = {
                    'id': row[0],
                    'timestamp': row[1],
                    'sender': row[2],
                    'recipient': row[3],
                    'message_type': row[4],
                    'content': row[5],
                    'priority': row[6],
                    'metadata': json.loads(row[7]) if row[7] else {}
                }
                messages.append(message)
            
            return messages
            
        except Exception as e:
            self.logger.error("Failed to get agent messages", error=str(e))
            return []
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up data older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clean conversations
            await self._db.execute("""
                DELETE FROM conversations WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            # Clean thoughts
            await self._db.execute("""
                DELETE FROM agent_thoughts WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            # Clean messages
            await self._db.execute("""
                DELETE FROM agent_messages WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            await self._db.commit()
            
            self.logger.info("Cleaned up old data", cutoff_date=cutoff_date)
            
        except Exception as e:
            self.logger.error("Failed to cleanup old data", error=str(e))
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {}
            
            # Conversation count
            cursor = await self._db.execute("SELECT COUNT(*) FROM conversations")
            stats['total_conversations'] = (await cursor.fetchone())[0]
            
            # Thought count
            cursor = await self._db.execute("SELECT COUNT(*) FROM agent_thoughts")
            stats['total_thoughts'] = (await cursor.fetchone())[0]
            
            # Message count
            cursor = await self._db.execute("SELECT COUNT(*) FROM agent_messages")
            stats['total_messages'] = (await cursor.fetchone())[0]
            
            # Get file size
            stats['db_size_mb'] = Path(self.db_path).stat().st_size / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            self.logger.error("Failed to get statistics", error=str(e))
            return {}
    
    async def close(self):
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self.logger.info("Conversation logger closed")