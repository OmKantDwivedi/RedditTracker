#!/usr/bin/env python3
"""
Verification script: Compare API ranking with actual Reddit UI
Use this to verify the system is working correctly
"""

import sys
import praw
import config

def verify_comment_rank(comment_url: str, expected_rank: int = None):
    """
    Verify comment ranking by showing all data
    
    Args:
        comment_url: Full Reddit comment URL
        expected_rank: What rank you see in the UI (optional)
    """
    
    import re
    
    # Extract IDs
    comment_match = re.search(r'/comments/[^/]+/[^/]+/([a-z0-9]+)', comment_url)
    post_match = re.search(r'/comments/([a-z0-9]+)', comment_url)
    
    if not comment_match or not post_match:
        print("❌ Invalid URL format")
        return
    
    target_comment_id = comment_match.group(1)
    post_id = post_match.group(1)
    
    # Initialize Reddit
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT
    )
    
    print("\n" + "="*80)
    print("REDDIT RANKING VERIFICATION REPORT")
    print("="*80)
    
    # Get target comment
    print(f"\n📌 Target Comment ID: {target_comment_id}")
    target = reddit.comment(id=target_comment_id)
    target.refresh()
    
    print(f"👤 Author: u/{target.author}")
    print(f"⬆️ Score: {target.score}")
    print(f"📝 Body preview: {target.body[:100].replace(chr(10), ' ')}...")
    
    # Check if top-level or reply
    is_top_level = target.parent_id.startswith('t3_')
    print(f"\n📍 Comment Type: {'TOP-LEVEL' if is_top_level else 'REPLY'}")
    
    if not is_top_level:
        parent_id = target.parent_id.replace('t1_', '')
        print(f"👆 Parent Comment ID: {parent_id}")
    
    # Get submission
    submission = reddit.submission(id=post_id)
    submission.comment_sort = 'best'
    submission.comments.replace_more(limit=0)
    
    print(f"\n📄 Post Title: {submission.title}")
    print(f"🔗 Post URL: https://reddit.com{submission.permalink}")
    
    # Get comparison set
    if is_top_level:
        print("\n" + "="*80)
        print("TOP-LEVEL COMMENTS (sorted by Best)")
        print("="*80)
        
        comments = [c for c in submission.comments if hasattr(c, 'id')]
        
        found_at = None
        for idx, comment in enumerate(comments, 1):
            is_target = "⭐⭐⭐" if comment.id == target_comment_id else "   "
            author = f"u/{comment.author}" if comment.author else "[deleted]"
            
            if comment.id == target_comment_id:
                found_at = idx
            
            if idx <= 10 or comment.id == target_comment_id:
                print(f"{is_target} {idx:3d}. {author:25s} | Score: {comment.score:5d} | ID: {comment.id}")
            elif idx == 11:
                print("   ...")
        
        print("\n" + "-"*80)
        print(f"Total top-level comments: {len(comments)}")
        
        if found_at:
            print(f"\n🎯 YOUR COMMENT POSITION: #{found_at}")
            if found_at <= 5:
                print(f"✅ Rank: {found_at} (IN TOP 5)")
            else:
                print(f"❌ Rank: Out of Top 5 (actual position: #{found_at})")
        else:
            print("\n⚠️ Comment not found in top-level comments")
    
    else:
        # Reply - need to get siblings
        parent_id = target.parent_id.replace('t1_', '')
        parent = reddit.comment(id=parent_id)
        parent.refresh()
        parent.replies.replace_more(limit=0)
        
        print("\n" + "="*80)
        print(f"REPLIES under parent comment {parent_id}")
        print("="*80)
        
        replies = [r for r in parent.replies if hasattr(r, 'id')]
        
        found_at = None
        for idx, reply in enumerate(replies, 1):
            is_target = "⭐⭐⭐" if reply.id == target_comment_id else "   "
            author = f"u/{reply.author}" if reply.author else "[deleted]"
            
            if reply.id == target_comment_id:
                found_at = idx
            
            print(f"{is_target} {idx:3d}. {author:25s} | Score: {reply.score:5d} | ID: {reply.id}")
        
        print("\n" + "-"*80)
        print(f"Total sibling replies: {len(replies)}")
        
        if found_at:
            print(f"\n🎯 YOUR REPLY POSITION: #{found_at}")
            if found_at <= 5:
                print(f"✅ Rank: {found_at} (IN TOP 5)")
            else:
                print(f"❌ Rank: Out of Top 5 (actual position: #{found_at})")
        else:
            print("\n⚠️ Reply not found in sibling list")
    
    # Compare with expected
    if expected_rank:
        print("\n" + "="*80)
        print("VERIFICATION")
        print("="*80)
        print(f"Expected rank (from UI): {expected_rank}")
        print(f"Detected rank (from API): {found_at if found_at else 'Not found'}")
        
        if found_at == expected_rank:
            print("✅ MATCH - System is working correctly!")
        else:
            print("⚠️ MISMATCH - Needs investigation")
            print("\nPossible causes:")
            print("  1. UI sort changed after API fetch")
            print("  2. Comment scores updated between checks")
            print("  3. Reddit's 'Best' algorithm differs from API order")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python verify_ranking.py <comment_url> [expected_rank]")
        print("\nExample:")
        print("  python verify_ranking.py 'https://reddit.com/r/AskReddit/comments/abc/title/xyz/' 3")
        print("\nThis will show you:")
        print("  - What the API returns")
        print("  - Where your comment appears")
        print("  - Compare with what you expect\n")
        sys.exit(1)
    
    url = sys.argv[1]
    expected = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    verify_comment_rank(url, expected)