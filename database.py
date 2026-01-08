import sqlite3
from datetime import datetime
from typing import Optional, Dict
import config

class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_tracking (
                    comment_url TEXT PRIMARY KEY,
                    last_known_rank TEXT,
                    last_checked_timestamp TEXT,
                    last_reply_timestamp TEXT
                )
            """)
            conn.commit()
    
    def get_last_known_data(self, comment_url: str) -> Optional[Dict]:
        """Retrieve historical data for a comment"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT last_known_rank, last_checked_timestamp, last_reply_timestamp
                FROM comment_tracking
                WHERE comment_url = ?
            """, (comment_url,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'last_known_rank': row[0],
                    'last_checked_timestamp': row[1],
                    'last_reply_timestamp': row[2]
                }
            return None
    
    def update_tracking_data(self, comment_url: str, current_rank: str, 
                            reply_timestamp: Optional[str] = None):
        """Update or insert tracking data"""
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Get existing data
            existing = self.get_last_known_data(comment_url)
            
            # Preserve last_reply_timestamp if no new reply
            last_reply = reply_timestamp
            if last_reply is None and existing:
                last_reply = existing['last_reply_timestamp']
            
            conn.execute("""
                INSERT OR REPLACE INTO comment_tracking 
                (comment_url, last_known_rank, last_checked_timestamp, last_reply_timestamp)
                VALUES (?, ?, ?, ?)
            """, (comment_url, current_rank, now, last_reply))
            conn.commit()
    
    def has_rank_changed(self, comment_url: str, current_rank: str) -> bool:
        """Check if rank has changed since last check"""
        data = self.get_last_known_data(comment_url)
        if not data:
            return False  # First time tracking
        return data['last_known_rank'] != current_rank