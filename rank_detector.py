import re
import time
from typing import Optional, List
import praw
from praw.models import Comment, MoreComments
import config

class RankDetector:
    def __init__(self, reddit_client: praw.Reddit):
        self.reddit = reddit_client
    
    @staticmethod
    def extract_comment_id(url: str) -> Optional[str]:
        """Extract comment ID from Reddit URL"""
        match = re.search(r'/comments/[^/]+/[^/]+/([a-z0-9]+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def extract_post_id(url: str) -> Optional[str]:
        """Extract post ID from URL"""
        match = re.search(r'/comments/([a-z0-9]+)', url)
        return match.group(1) if match else None
    
    def get_parent_comment_id(self, comment: Comment) -> Optional[str]:
        """Get parent comment ID if this is a reply"""
        try:
            if comment.parent_id.startswith('t1_'):  # t1_ = comment
                return comment.parent_id.replace('t1_', '')
            return None  # Parent is post (t3_)
        except Exception:
            return None
    
    def is_top_level_comment(self, comment: Comment) -> bool:
        """Check if comment is top-level (direct reply to post)"""
        return comment.parent_id.startswith('t3_')
    
    def get_all_comments_flat(self, submission) -> List[Comment]:
        """
        Get all comments in flat list (Reddit's API order)
        This preserves Reddit's internal sorting
        """
        comments_list = []
        
        # Replace MoreComments objects to get full comment tree
        submission.comments.replace_more(limit=None)
        
        # Get all comments in a flat list
        for comment in submission.comments.list():
            if isinstance(comment, Comment):
                comments_list.append(comment)
        
        return comments_list
    
    def get_top_level_comments_ordered(self, post_id: str) -> List[Comment]:
        """
        Fetch top-level comments in Reddit's 'Best' sort order
        This is the KEY fix - we use Reddit's actual sort parameter
        """
        try:
            # Fetch submission with 'best' sort (Reddit's default)
            submission = self.reddit.submission(id=post_id)
            
            # CRITICAL: Set comment sort to 'best'
            submission.comment_sort = 'best'
            
            # Refresh to apply sort
            submission.comments.replace_more(limit=0)
            
            # Extract ONLY top-level comments in order
            top_level_comments = []
            for comment in submission.comments:
                if isinstance(comment, Comment):
                    top_level_comments.append(comment)
            
            print(f"📊 Fetched {len(top_level_comments)} top-level comments (sorted by Best)")
            return top_level_comments
            
        except Exception as e:
            print(f"❌ Error fetching comments: {e}")
            return []
    
    def get_sibling_comments_ordered(self, comment: Comment) -> tuple[List[Comment], str]:
        """
        Get all sibling comments (replies to same parent) in order
        Returns: (siblings_list, parent_id)
        """
        try:
            parent_id = self.get_parent_comment_id(comment)
            if not parent_id:
                return [], None
            
            parent_comment = self.reddit.comment(id=parent_id)
            parent_comment.refresh()
            parent_comment.replies.replace_more(limit=0)
            
            # Get replies in order (Reddit API preserves sort order)
            siblings = []
            for reply in parent_comment.replies:
                if isinstance(reply, Comment):
                    siblings.append(reply)
            
            print(f"📊 Fetched {len(siblings)} sibling replies under parent {parent_id}")
            return siblings, parent_id
            
        except Exception as e:
            print(f"❌ Error fetching siblings: {e}")
            return [], None
    
    def find_comment_rank(self, target_comment_id: str, comments_list: List[Comment]) -> Optional[int]:
        """
        Find the position of target comment in ordered list
        Returns 1-based index (1, 2, 3, ...) or None
        """
        for idx, comment in enumerate(comments_list, 1):
            if comment.id == target_comment_id:
                return idx
        return None
    
    def detect_rank(self, comment_url: str) -> str:
        """
        Detect comment rank using Reddit's actual 'best' sort order
        Returns: '1'-'5' or 'Out of Top 5'
        """
        target_comment_id = self.extract_comment_id(comment_url)
        post_id = self.extract_post_id(comment_url)
        
        if not target_comment_id or not post_id:
            print("❌ Invalid URL format")
            return 'Out of Top 5'
        
        try:
            print(f"\n🔍 Target Comment ID: {target_comment_id}")
            print(f"📄 Post ID: {post_id}")
            
            # Fetch target comment
            target_comment = self.reddit.comment(id=target_comment_id)
            target_comment.refresh()
            
            # Check if deleted/removed
            if hasattr(target_comment, 'body') and target_comment.body in ['[deleted]', '[removed]']:
                print("⚠️ Comment is deleted or removed")
                return 'Out of Top 5'
            
            print(f"👤 Author: u/{target_comment.author}")
            print(f"⬆️ Score: {target_comment.score}")
            
            # Determine if top-level or reply
            is_top_level = self.is_top_level_comment(target_comment)
            print(f"📍 Type: {'Top-level comment' if is_top_level else 'Reply to another comment'}")
            
            if is_top_level:
                # Compare against all top-level comments
                comparison_set = self.get_top_level_comments_ordered(post_id)
                comparison_context = "top-level comments"
            else:
                # Compare against sibling replies
                comparison_set, parent_id = self.get_sibling_comments_ordered(target_comment)
                comparison_context = f"replies under parent {parent_id}"
                
                if not comparison_set:
                    print("⚠️ Could not fetch sibling comments")
                    return 'Out of Top 5'
            
            if not comparison_set:
                print("⚠️ No comments found for comparison")
                return 'Out of Top 5'
            
            # Find position in ordered list
            rank = self.find_comment_rank(target_comment_id, comparison_set)
            
            if rank is None:
                print(f"⚠️ Target comment not found in {comparison_context}")
                return 'Out of Top 5'
            
            # Debug: Show top 5 with comparison
            print(f"\n🏆 Top 5 {comparison_context}:")
            for idx, comment in enumerate(comparison_set[:10], 1):
                is_target = "⭐" if comment.id == target_comment_id else "  "
                author = f"u/{comment.author}" if comment.author else "[deleted]"
                print(f"{is_target} {idx:2d}. {author:20s} | Score: {comment.score:4d} | ID: {comment.id}")
                
                if idx == 5:
                    print("   " + "-" * 60)
            
            # Determine final rank
            if rank <= config.TOP_N_COMMENTS:
                print(f"\n✅ Target comment is ranked #{rank} (in top 5)")
                return str(rank)
            else:
                print(f"\n❌ Target comment is ranked #{rank} (outside top 5)")
                return 'Out of Top 5'
            
        except Exception as e:
            print(f"\n❌ Error detecting rank: {e}")
            import traceback
            traceback.print_exc()
            return 'Out of Top 5'