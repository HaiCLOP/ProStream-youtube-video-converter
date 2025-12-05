import os
import time
import uuid
import glob
import logging
import threading
import shutil
import collections
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify, after_this_request
import yt_dlp

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
MAX_FILE_AGE = 300  # 5 Minutes Strict Retention
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB in Bytes
RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW = 300 # 5 Minutes

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("server_activity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(32)

# In-memory Rate Limiter: { 'ip_address': [timestamp1, timestamp2] }
request_buckets = collections.defaultdict(list)

# ==============================================================================
# UTILITIES
# ==============================================================================
def get_ffmpeg_location():
    local_ffmpeg = os.path.join(BASE_DIR, 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg): return BASE_DIR
    
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg: return os.path.dirname(system_ffmpeg)
    return None

def format_duration(seconds):
    if not seconds: return "00:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    return f"{int(m):02d}:{int(s):02d}"

def check_rate_limit(ip_address):
    """
    Returns True if allowed, False if limit exceeded.
    Cleans up old timestamps automatically.
    """
    now = time.time()
    timestamps = request_buckets[ip_address]
    
    # Filter out timestamps older than the window
    valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    request_buckets[ip_address] = valid_timestamps
    
    if len(valid_timestamps) >= RATE_LIMIT_COUNT:
        return False
    
    return True

def record_request(ip_address):
    request_buckets[ip_address].append(time.time())

# ==============================================================================
# LOGIC LAYERS
# ==============================================================================
class FormatParser:
    @staticmethod
    def parse_formats(info_dict):
        formats = info_dict.get('formats', [])
        video_options = {}
        
        for f in formats:
            if f.get('vcodec') == 'none' or not f.get('height'): continue
            
            resolution = f"{f['height']}p"
            if resolution not in video_options:
                video_options[resolution] = {
                    'id': f['format_id'],
                    'resolution': resolution,
                    'ext': f.get('ext', 'mp4'),
                    'filesize': f.get('filesize')
                }

        sorted_res = sorted(video_options.values(), key=lambda x: int(x['resolution'][:-1]), reverse=True)
        
        audio_options = [
            {'id': '320', 'label': 'High Quality (320kbps)', 'bitrate': 320},
            {'id': '192', 'label': 'Standard (192kbps)', 'bitrate': 192},
            {'id': '128', 'label': 'Data Saver (128kbps)', 'bitrate': 128}
        ]
        return {'video': sorted_res, 'audio': audio_options}

class DownloaderService:
    @staticmethod
    def fetch_metadata(url):
        ffmpeg_dir = get_ffmpeg_location()
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ffmpeg_location': ffmpeg_dir
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'duration': format_duration(info.get('duration')),
                'formats': FormatParser.parse_formats(info)
            }

    @staticmethod
    def process_download(url, type_mode, quality_setting, ip_address):
        unique_id = uuid.uuid4().hex
        ffmpeg_dir = get_ffmpeg_location()
        
        if not ffmpeg_dir:
            raise EnvironmentError("FFmpeg not found.")

        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{unique_id}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'ffmpeg_location': ffmpeg_dir,
            'nocheckcertificate': True,
            'max_filesize': MAX_FILE_SIZE, # 2GB Limit
        }

        if type_mode == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': str(quality_setting or '192'),
                }, {'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'}],
            })
            mime_type = 'audio/mpeg'
            ext_check = '.mp3'
        else:
            res_val = quality_setting.replace('p', '')
            ydl_opts.update({
                'format': f'bestvideo[height<={res_val}]+bestaudio/best[height<={res_val}]/best',
                'merge_output_format': 'mp4',
            })
            mime_type = 'video/mp4'
            ext_check = '.mp4'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                final_path = base + ext_check
                
                if not os.path.exists(final_path):
                    if os.path.exists(filename): final_path = filename
                    else:
                        matches = glob.glob(f"{base}*{ext_check}")
                        if matches: final_path = matches[0]
                        else: raise FileNotFoundError("Download missing.")

                # --- LOGGING REQUIREMENT ---
                file_size_mb = os.path.getsize(final_path) / (1024 * 1024)
                logger.info(f"DOWNLOAD SUCCESS | IP: {ip_address} | File: {os.path.basename(final_path)} | Size: {file_size_mb:.2f}MB | Format: {type_mode}")

                return {'path': final_path, 'title': info.get('title'), 'mimetype': mime_type}
        except yt_dlp.utils.DownloadError as e:
            if 'File is larger than' in str(e):
                logger.warning(f"FILE SIZE LIMIT EXCEEDED | IP: {ip_address} | URL: {url}")
                raise ValueError("File exceeds the 2GB download limit.")
            raise e

# ==============================================================================
# BACKGROUND CLEANUP (5 Minute Strict)
# ==============================================================================
def cleanup():
    while True:
        try:
            now = time.time()
            for f in glob.glob(os.path.join(DOWNLOAD_FOLDER, '*')):
                # Delete if older than MAX_FILE_AGE (300s)
                if os.stat(f).st_mtime < now - MAX_FILE_AGE:
                    try: 
                        os.remove(f)
                        logger.info(f"CLEANUP | Deleted: {os.path.basename(f)}")
                    except: pass
        except: pass
        time.sleep(60)

threading.Thread(target=cleanup, daemon=True).start()

# ==============================================================================
# ROUTES
# ==============================================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-info', methods=['POST'])
def get_info():
    try:
        data = DownloaderService.fetch_metadata(request.json['url'])
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    ip = request.remote_addr
    
    # 1. Rate Limiter Check
    if not check_rate_limit(ip):
        logger.warning(f"RATE LIMIT BLOCKED | IP: {ip}")
        return "Rate limit exceeded. You can convert 5 videos every 5 minutes.", 429

    try:
        url = request.form.get('url')
        type_mode = request.form.get('type')
        quality = request.form.get('quality')
        
        result = DownloaderService.process_download(url, type_mode, quality, ip)
        
        # 2. Record successful request for rate limiting
        record_request(ip)

        # 3. Deferred cleanup hook (optional, handled by background thread mainly)
        @after_this_request
        def cleanup_hook(response):
            return response

        return send_file(
            result['path'],
            as_attachment=True,
            download_name=f"{result['title']}.{type_mode == 'audio' and 'mp3' or 'mp4'}",
            mimetype=result['mimetype']
        )
    except Exception as e:
        logger.error(f"Route Error: {e}")
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)