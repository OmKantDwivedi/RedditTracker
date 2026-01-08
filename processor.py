from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import praw
from database import Database
from rank_detector import RankDetector
from reply_detector import ReplyDetector
from status_calculator import StatusCalculator
import config

class CommentProcessor:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.db = Database()
        self.status_calc = StatusCalculator(self.db)
        
        # Initialize Reddit client (shared across rank and reply detection)
        self.reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT
        )
    
    def process_single_comment(self, comment_url: str, 
                               rank_detector: RankDetector,
                               reply_detector: ReplyDetector) -> Dict:
        """
        Process a single comment URL
        Returns dict with URL, Status, Present Rank
        """
        print(f"\n{'='*60}")
        print(f"Processing: {comment_url}")
        print(f"{'='*60}")
        
        try:
            # Detect current rank using Best algorithm
            current_rank = rank_detector.detect_rank(comment_url)
            
            # Check for recent replies
            has_reply, reply_timestamp = reply_detector.has_recent_reply(comment_url)
            
            # Calculate status
            status = self.status_calc.calculate_status(
                comment_url, 
                current_rank, 
                has_reply,
                reply_timestamp
            )
            
            result = {
                'URL': comment_url,
                'Status': status,
                'Present Rank': current_rank
            }
            
            print(f"\n✅ RESULT: {status} | Rank: {current_rank}")
            return result
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                'URL': comment_url,
                'Status': 'No Change',
                'Present Rank': 'Out of Top 5'
            }
    
    def process_batch(self, comment_urls: List[str]) -> List[Dict]:
        """
        Process batch of comment URLs sequentially
        Returns list of results
        """
        results = []
        
        # Create detector instances (share Reddit client)
        rank_detector = RankDetector(self.reddit)
        reply_detector = ReplyDetector()  # Uses its own Reddit client
        
        # Process comments sequentially
        for idx, url in enumerate(comment_urls, 1):
            print(f"\n\n{'#'*60}")
            print(f"# COMMENT {idx}/{len(comment_urls)}")
            print(f"{'#'*60}")
            
            result = self.process_single_comment(url, rank_detector, reply_detector)
            results.append(result)
        
        return results
    
    def process_batch_parallel(self, comment_urls: List[str]) -> List[Dict]:
        """
        Process batch with parallel execution for reply detection
        Rank detection is sequential (uses shared Reddit API client)
        """
        results = []
        
        rank_detector = RankDetector(self.reddit)
        
        print(f"\n{'='*60}")
        print("PHASE 1: RANK DETECTION (Sequential)")
        print(f"{'='*60}")
        
        # First pass: detect ranks (sequential to avoid API rate limits)
        rank_results = {}
        for idx, url in enumerate(comment_urls, 1):
            print(f"\n[{idx}/{len(comment_urls)}] Detecting rank: {url}")
            try:
                rank = rank_detector.detect_rank(url)
                rank_results[url] = rank
                print(f"✓ Rank: {rank}")
            except Exception as e:
                print(f"✗ Error: {e}")
                rank_results[url] = 'Out of Top 5'
        
        print(f"\n{'='*60}")
        print("PHASE 2: REPLY DETECTION (Parallel)")
        print(f"{'='*60}")
        
        # Second pass: check replies (parallel)
        def check_reply(url):
            reply_detector = ReplyDetector()  # Each thread gets own instance
            try:
                has_reply, timestamp = reply_detector.has_recent_reply(url)
                print(f"✓ {url}: Reply={has_reply}")
                return url, (has_reply, timestamp)
            except Exception as e:
                print(f"✗ {url}: Error={e}")
                return url, (False, None)
        
        reply_results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(check_reply, url) for url in comment_urls]
            for future in as_completed(futures):
                url, (has_reply, timestamp) = future.result()
                reply_results[url] = (has_reply, timestamp)
        
        print(f"\n{'='*60}")
        print("PHASE 3: STATUS CALCULATION")
        print(f"{'='*60}")
        
        # Combine results
        for url in comment_urls:
            rank = rank_results.get(url, 'Out of Top 5')
            has_reply, reply_timestamp = reply_results.get(url, (False, None))
            
            status = self.status_calc.calculate_status(
                url, rank, has_reply, reply_timestamp
            )
            
            results.append({
                'URL': url,
                'Status': status,
                'Present Rank': rank
            })
            
            print(f"✓ {url}")
            print(f"  Status: {status} | Rank: {rank}")
        
        return results