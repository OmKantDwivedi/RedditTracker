from typing import Dict
from database import Database

class StatusCalculator:
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_status(self, comment_url: str, current_rank: str, 
                        has_recent_reply: bool, reply_timestamp: str = None) -> str:
        """
        Calculate status based on rank change and reply activity
        Returns one of:
        - 'Ranking Changed'
        - 'Reply Received'
        - 'Ranking Changed + Reply Received'
        - 'No Change'
        """
        rank_changed = self.db.has_rank_changed(comment_url, current_rank)
        
        # Update database with current data
        self.db.update_tracking_data(comment_url, current_rank, reply_timestamp)
        
        # Determine status
        if rank_changed and has_recent_reply:
            return 'Ranking Changed + Reply Received'
        elif rank_changed:
            return 'Ranking Changed'
        elif has_recent_reply:
            return 'Reply Received'
        else:
            return 'No Change'