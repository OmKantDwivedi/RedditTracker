#!/usr/bin/env python3
"""
Reddit Comment Tracker - Production Version (Fixed for Multi-User)
"""

from flask import Flask, render_template, request, jsonify, send_file, session
import os
import threading
import praw
from datetime import datetime
from pathlib import Path
import secrets
import logging
from logging.handlers import RotatingFileHandler
import uuid
import time

from database import Database
from rank_detector import RankDetector
from reply_detector import ReplyDetector
from status_calculator import StatusCalculator
from output_writer import OutputWriter
from input_loader import InputLoader
import config

# Initialize Flask app
app = Flask(__name__)

# Production configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ENV'] = 'production'
app.config['DEBUG'] = False

# Setup logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/reddit_tracker.log', maxBytes=10240000, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Reddit Comment Tracker startup')

# NEW: Dictionary to track jobs per session
active_jobs = {}
job_lock = threading.Lock()

def process_comments_background(job_id, comment_urls):
    """Background task to process comments"""
    
    try:
        with job_lock:
            active_jobs[job_id] = {
                'is_running': True,
                'progress': 0,
                'total': len(comment_urls),
                'current_url': '',
                'results': [],
                'error': None,
                'started_at': time.time()
            }
        
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT
        )
        
        db = Database()
        rank_detector = RankDetector(reddit)
        reply_detector = ReplyDetector()
        status_calc = StatusCalculator(db)
        
        for idx, url in enumerate(comment_urls):
            with job_lock:
                if job_id in active_jobs:
                    active_jobs[job_id]['current_url'] = url
                    active_jobs[job_id]['progress'] = idx
            
            try:
                # Get previous rank BEFORE updating
                previous_rank = db.get_previous_rank(url)
                
                current_rank = rank_detector.detect_rank(url)
                has_reply, reply_timestamp = reply_detector.has_recent_reply(url)
                status = status_calc.calculate_status(url, current_rank, has_reply, reply_timestamp)
                
                result = {
                    'URL': url,
                    'Status': status,
                    'Present Rank': current_rank,
                    'Previous Rank': previous_rank if previous_rank else 'N/A'
                }
                
                with job_lock:
                    if job_id in active_jobs:
                        active_jobs[job_id]['results'].append(result)
                
            except Exception as e:
                app.logger.error(f"Error processing {url}: {e}")
                with job_lock:
                    if job_id in active_jobs:
                        active_jobs[job_id]['results'].append({
                            'URL': url,
                            'Status': 'Error',
                            'Present Rank': 'Out of Top 5',
                            'Previous Rank': 'N/A'
                        })
        
        with job_lock:
            if job_id in active_jobs:
                active_jobs[job_id]['progress'] = len(comment_urls)
                active_jobs[job_id]['is_running'] = False
        
    except Exception as e:
        app.logger.error(f"Background task error: {e}")
        with job_lock:
            if job_id in active_jobs:
                active_jobs[job_id]['error'] = str(e)
                active_jobs[job_id]['is_running'] = False

@app.route('/')
def index():
    # Create session ID if doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'active_jobs': len(active_jobs)
    })

@app.route('/api/process-spreadsheet', methods=['POST'])
def process_spreadsheet():
    data = request.get_json()
    
    if not data or 'spreadsheet_url' not in data:
        return jsonify({'error': 'No spreadsheet URL provided'}), 400
    
    spreadsheet_url = data['spreadsheet_url'].strip()
    
    if not spreadsheet_url:
        return jsonify({'error': 'Spreadsheet URL is empty'}), 400
    
    # Get or create session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    
    try:
        app.logger.info(f"Processing spreadsheet for session {session_id}: {spreadsheet_url}")
        comment_urls = InputLoader.load(spreadsheet_url)
        
        if not comment_urls:
            return jsonify({'error': 'No valid comment URLs found'}), 400
        
        # Check if this session already has a running job
        with job_lock:
            if session_id in active_jobs and active_jobs[session_id].get('is_running', False):
                return jsonify({'error': 'You already have a tracking job running. Please wait for it to complete.'}), 409
        
        # Create new job ID
        job_id = session_id
        
        # Start background processing
        thread = threading.Thread(target=process_comments_background, args=(job_id, comment_urls))
        thread.daemon = True
        thread.start()
        
        app.logger.info(f"Started processing {len(comment_urls)} URLs for session {session_id}")
        
        return jsonify({
            'success': True,
            'message': f'Started processing {len(comment_urls)} URLs',
            'job_id': job_id
        })
        
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({'error': f'Failed to load spreadsheet: {str(e)}'}), 400

@app.route('/api/status')
def get_status():
    # Get session ID
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({
            'is_running': False,
            'progress': 0,
            'total': 0,
            'current_url': '',
            'results_count': 0,
            'error': None
        })
    
    with job_lock:
        job_data = active_jobs.get(session_id, {})
    
    return jsonify({
        'is_running': job_data.get('is_running', False),
        'progress': job_data.get('progress', 0),
        'total': job_data.get('total', 0),
        'current_url': job_data.get('current_url', ''),
        'results_count': len(job_data.get('results', [])),
        'error': job_data.get('error')
    })

@app.route('/api/results')
def get_results():
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'results': []})
    
    with job_lock:
        job_data = active_jobs.get(session_id, {})
    
    return jsonify({'results': job_data.get('results', [])})

@app.route('/api/export')
def export_results():
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No results to export'}), 400
    
    with job_lock:
        job_data = active_jobs.get(session_id, {})
        results = job_data.get('results', [])
    
    if not results:
        return jsonify({'error': 'No results to export'}), 400
    
    try:
        output_path = OutputWriter.generate_output_filename()
        OutputWriter.create_output_spreadsheet(results, output_path)
        return send_file(output_path, as_attachment=True, download_name=output_path)
    except Exception as e:
        app.logger.error(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500

# Cleanup old jobs (runs every hour)
def cleanup_old_jobs():
    """Remove jobs older than 1 hour"""
    while True:
        time.sleep(3600)  # 1 hour
        current_time = time.time()
        with job_lock:
            to_remove = []
            for job_id, job_data in active_jobs.items():
                if current_time - job_data.get('started_at', current_time) > 3600:
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                del active_jobs[job_id]
                app.logger.info(f"Cleaned up old job: {job_id}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_jobs)
cleanup_thread.daemon = True
cleanup_thread.start()

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    Path('templates').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"\n⚠️  Running Reddit Comment Tracker (Multi-User Fixed)")
    print(f"🌐 Server starting on port {port}")
    print(f"🔒 Debug mode: {app.config['DEBUG']}")
    print(f"📍 Access at: http://localhost:{port}\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
