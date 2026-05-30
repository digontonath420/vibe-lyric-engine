import os
import re
import uuid
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import syncedlyrics

app = Flask(__name__)

UPLOAD_FOLDER = 'downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

COOKIES_FILE = 'cookies.txt'

def get_ydl_opts(extra_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    if extra_opts:
        opts.update(extra_opts)
    return opts

def lrc_to_srt(lrc_text):
    if not lrc_text:
        return ""
    lines = lrc_text.split('\n')
    srt_lines = []
    index = 1
    parsed_lines = []

    for line in lines:
        match = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', line.strip())
        if match:
            m, s, ms, text = match.groups()
            total_sec = int(m)*60 + int(s) + int(ms)/100
            parsed_lines.append((total_sec, text.strip()))

    parsed_lines.sort(key=lambda x: x[0])

    for i, (start, text) in enumerate(parsed_lines):
        end = parsed_lines[i+1][0] if i+1 < len(parsed_lines) else start + 4
        def fmt(t):
            h = int(t//3600)
            m = int((t%3600)//60)
            s = int(t%60)
            ms = int((t%1)*1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
        srt_lines.extend([str(index), f"{fmt(start)} --> {fmt(end)}", text or "♪", ""])
        index += 1

    return "\n".join(srt_lines)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_song():
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query empty'}), 400

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
            res = ydl.extract_info(f"ytsearch5:{query}", download=False)
        
        results = [{
            'id': entry['id'],
            'title': entry['title'],
            'duration': entry.get('duration'),
            'url': f"https://youtu.be/{entry['id']}"
        } for entry in res.get('entries', []) if entry.get('id')]
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_video():
    data = request.json
    video_id = data.get('id')
    title = data.get('title', 'Unknown Song')
    font_style = data.get('font_style', 'default')
    bg_style = data.get('bg_style', 'cosmic')

    if not video_id:
        return jsonify({'error': 'Video ID missing'}), 400

    session_id = str(uuid.uuid4())
    audio_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.mp3")
    srt_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.srt")
    video_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.mp4")

    try:
        ydl_opts = get_ydl_opts({
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(UPLOAD_FOLDER, f"{session_id}.%(ext)s"),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtu.be/{video_id}"])

        try:
            lrc = syncedlyrics.search(title, allow_plain_format=True)
            srt_content = lrc_to_srt(lrc)
        except:
            srt_content = "1\n00:00:01,000 --> 00:00:10,000\n[♪ Instrumental]"

        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        bg_colors = {'cosmic': '0x1a0933', 'cyberpunk': '0x0d0d1a', 'emerald': '0x051a14', 'sunset': '0x2b1010'}
        font_styles = {
            'default': "Fontname=Liberation Sans,Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2",
            'glowing_neon': "Fontname=Liberation Sans,Fontsize=26,PrimaryColour=&H00FFFF00,OutlineColour=&H00FF00FF,BorderStyle=1,Outline=3,Alignment=2",
            'minimal': "Fontname=Liberation Sans,Fontsize=22,PrimaryColour=&H00E6E6E6,OutlineColour=&H00222222,BorderStyle=3,Outline=1,Alignment=2",
            'aesthetic_bold': "Fontname=Liberation Sans,Fontsize=28,PrimaryColour=&H0080FF80,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Alignment=2"
        }

        chosen_style = font_styles.get(font_style, font_styles['default'])
        bg_color = bg_colors.get(bg_style, '0x1a0933')

        ffmpeg_cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c={bg_color}:s=854x480:r=30',
            '-i', audio_path, '-vf', f"subtitles={srt_path}:force_style='{chosen_style}'",
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-tune', 'stillimage',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', video_path
        ]

        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        return jsonify({'success': True, 'download_url': f'/download/{session_id}.mp4', 'title': title})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
