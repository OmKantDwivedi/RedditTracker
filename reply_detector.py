import re
from datetime import datetime, timedelta
from typing import Optional
import praw
from praw.exceptions import PRAWException
import config

class ReplyDetector:
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT
        )
    
    @staticmethod
    def extract_comment_id(url: str) -> Optional[str]:
        """Extract comment ID from URL"""
        match = re.search(r'/comments/[^/]+/[^/]+/([a-z0-9]+)', url)
        return match.group(1) if match else None
    
    def has_recent_reply(self, comment_url: str) -> tuple[bool, Optional[str]]:
        """
        Check if comment has replies in last 72 hours
        Returns: (has_recent_reply, most_recent_reply_timestamp)
        """
        comment_id = self.extract_comment_id(comment_url)
        if not comment_id:
            return False, None
        
        try:
            # Fetch comment with all replies
            comment = self.reddit.comment(id=comment_id)
            comment.refresh()
            
            cutoff_time = datetime.utcnow() - timedelta(hours=config.REPLY_WINDOW_HOURS)
            cutoff_timestamp = cutoff_time.timestamp()
            
            most_recent_reply_time = None
            
            # Traverse all replies recursively
            def check_replies(comment_obj):
                nonlocal most_recent_reply_time
                
                try:
                    comment_obj.replies.replace_more(limit=0)
                    for reply in comment_obj.replies:
                        reply_time = reply.created_utc
                        
                        if reply_time >= cutoff_timestamp:
                            if most_recent_reply_time is None or reply_time > most_recent_reply_time:
                                most_recent_reply_time = reply_time
                        
                        # Check nested replies
                        check_replies(reply)
                except Exception:
                    pass
            
            check_replies(comment)
            
            if most_recent_reply_time:
                timestamp_str = datetime.utcfromtimestamp(most_recent_reply_time).isoformat()
                return True, timestamp_str
            
            return False, None
            
        except PRAWException as e:
            print(f"Error fetching replies for {comment_url}: {e}")
            return False, None
        except Exception as e:
            print(f"Unexpected error for {comment_url}: {e}")
            return False, None