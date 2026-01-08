#!/usr/bin/env python3
"""
Reddit Comment Rank & Reply Tracker
Production-ready system for tracking comment rankings and reply activity
"""

import sys
import argparse
from pathlib import Path
from input_loader import InputLoader
from processor import CommentProcessor
from output_writer import OutputWriter

def main():
    parser = argparse.ArgumentParser(
        description='Track Reddit comment rankings and reply activity'
    )
    parser.add_argument(
        'input_source',
        help='Input spreadsheet (Google Sheets URL, download URL, or local file path)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: auto-generated with timestamp)',
        default=None
    )
    parser.add_argument(
        '--csv',
        action='store_true',
        help='Output as CSV instead of XLSX'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel processing for reply detection'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers (default: 5)'
    )
    
    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print("Reddit Comment Rank & Reply Tracker")
        print("=" * 60)
        
        # Step 1: Load input
        print(f"\n[1/3] Loading input from: {args.input_source}")
        comment_urls = InputLoader.load(args.input_source)
        print(f"✓ Loaded {len(comment_urls)} comment URLs")
        
        if len(comment_urls) == 0:
            print("⚠ No valid comment URLs found in input")
            return 1
        
        # Step 2: Process comments
        print(f"\n[2/3] Processing comments...")
        processor = CommentProcessor(max_workers=args.workers)
        
        if args.parallel:
            print(f"→ Using parallel processing with {args.workers} workers")
            results = processor.process_batch_parallel(comment_urls)
        else:
            print("→ Using sequential processing")
            results = processor.process_batch(comment_urls)
        
        print(f"✓ Processed {len(results)} comments")
        
        # Step 3: Write output
        print(f"\n[3/3] Writing output...")
        
        if args.csv:
            output_path = OutputWriter.create_csv_output(results, args.output)
        else:
            output_path = OutputWriter.create_output_spreadsheet(results, args.output)
        
        print(f"✓ Output saved to: {output_path}")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        status_counts = {}
        rank_counts = {}
        
        for result in results:
            status = result['Status']
            rank = result['Present Rank']
            status_counts[status] = status_counts.get(status, 0) + 1
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        print("\nStatus Distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        print("\nRank Distribution:")
        for rank in ['1', '2', '3', '4', '5', 'Out of Top 5']:
            if rank in rank_counts:
                print(f"  Rank {rank}: {rank_counts[rank]}")
        
        print("\n✓ Processing complete!")
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())