#!/usr/bin/env python3
"""
Test script for debugging single comment ranking
Shows exactly what Reddit API returns vs what the UI shows
"""

import sys
import praw
from rank_detector import RankDetector
from reply_detector import ReplyDetector
import config

def test_comment(comment_url: str):
    """Test ranking detection for a single comment"""
    
    print("\n" + "="*70)
    print(" " * 20 + "REDDIT COMMENT RANK DEBUGGER")
    print("="*70)
    print(f"\n🔗 Target URL: {comment_url}\n")
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT
    )
    
    print("="*70)
    print("STEP 1: RANK DETECTION")
    print("="*70)
    
    rank_detector = RankDetector(reddit)
    rank = rank_detector.detect_rank(comment_url)
    
    print("\n" + "="*70)
    print("STEP 2: REPLY DETECTION")
    print("="*70)
    
    reply_detector = ReplyDetector()
    has_reply, timestamp = reply_detector.has_recent_reply(comment_url)
    
    print(f"\n📬 Recent replies (last 72 hours): {'YES' if has_reply else 'NO'}")
    if timestamp:
        print(f"📅 Most recent reply timestamp: {timestamp}")
    
    print("\n" + "="*70)
    print("FINAL RESULT")
    print("="*70)
    print(f"\n📊 Present Rank: {rank}")
    print(f"💬 Reply Activity: {'YES' if has_reply else 'NO'}")
    
    # Status determination
    if rank != 'Out of Top 5':
        print(f"✅ Comment is in TOP 5 (Position #{rank})")
    else:
        print(f"❌ Comment is OUTSIDE top 5")
    
    print("\n" + "="*70)
    print("\n💡 TIP: Compare this rank with what you see in Reddit UI")
    print("   Go to the post and sort by 'Best' to verify")
    print("="*70 + "\n")

def show_post_top_comments(post_url: str, limit: int = 10):
    """
    Show top N comments from a post for manual verification
    """
    import re
    match = re.search(r'/comments/([a-z0-9]+)', post_url)
    if not match:
        print("Invalid post URL")
        return
    
    post_id = match.group(1)
    
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT
    )
    
    submission = reddit.submission(id=post_id)
    submission.comment_sort = 'best'
    submission.comments.replace_more(limit=0)
    
    print("\n" + "="*70)
    print(f"TOP {limit} COMMENTS (sorted by Best)")
    print("="*70)
    
    for idx, comment in enumerate(submission.comments[:limit], 1):
        if hasattr(comment, 'author') and comment.author:
            author = f"u/{comment.author}"
        else:
            author = "[deleted]"
        
        body_preview = comment.body[:60].replace('\n', ' ') if hasattr(comment, 'body') else "[removed]"
        
        print(f"\n{idx}. {author} (Score: {comment.score})")
        print(f"   ID: {comment.id}")
        print(f"   Preview: {body_preview}...")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("USAGE")
        print("="*70)
        print("\nTest single comment:")
        print("  python test_single_comment.py <comment_url>")
        print("\nShow top comments from post:")
        print("  python test_single_comment.py <post_url> --show-top")
        print("\nEXAMPLES:")
        print("  python test_single_comment.py 'https://reddit.com/r/AskReddit/comments/abc/title/xyz/'")
        print("  python test_single_comment.py 'https://reddit.com/r/AskReddit/comments/abc/title/' --show-top")
        print("="*70 + "\n")
        sys.exit(1)
    
    url = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--show-top':
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        show_post_top_comments(url, limit)
    else:
        test_comment(url)