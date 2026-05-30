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

def lrc_to_srt(lrc_text):
    if not lrc_text:
        return ""
    lines = lrc_text.split('\n')
    srt_lines = []
    index = 1
    
    parsed_lines = []
    for line in lines:
        match = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)', line)
        if match:
            minutes, seconds, hundredths, text = match.groups()
            total_seconds = int(minutes) * 60 + int(seconds) + int(hundredths) / 100.0
            parsed_lines.append((total_seconds, text.strip()))
            
    parsed_lines.sort(key=lambda x: x[0])
    
    for i in range(len(parsed_lines)):
        start_time = parsed_lines[i][0]
        end_time = parsed_lines[i+1][0] if i + 1 < len(parsed_lines) else start_time + 4.0
        
        def format_time(t):
            hrs = int(t // 3600)
            mins = int((t % 3600) // 60)
            secs = int(t % 60)
            msecs = int((t % 1) * 1000)
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"
            
        srt_lines.append(f"{index}")
        srt_lines.append(f"{format_time(start_time)} --> {format_time(end_time)}")
        srt_lines.append(parsed_lines[i][1])
        srt_lines.append("")
        index += 1
        
    return "\n".join(srt_lines)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_song():
    data = request.json
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'Query is empty'}), 400
        
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'extract_flat': True,
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch5:{query} lyrics", download=False)
            results = []
            if 'entries' in search_results:
                for entry in search_results['entries']:
                    results.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'duration': entry.get('duration'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id')}"
                    })
            return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_video():
    data = request.json
    video_id = data.get('id')
    title = data.get('title', 'Song')
    font_style = data.get('font_style', 'default')
    bg_style = data.get('bg_style', 'cosmic')
    
    if not video_id:
        return jsonify({'error': 'Missing Video ID'}), 400
        
    session_id = str(uuid.uuid4())
    audio_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.mp3")
    srt_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.srt")
    output_video_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.mp4")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(UPLOAD_FOLDER, f"{session_id}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            
        try:
            lrc_text = syncedlyrics.search(title)
            srt_content = lrc_to_srt(lrc_text)
        except Exception:
            srt_content = ""
            
        if not srt_content:
            srt_content = "1\n00:00:01,000 --> 00:00:10,000\n[Aesthetic Instrumental / Lyrics Not Found]"
            
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
            
        bg_colors = {
            'cosmic': '0x1a0933',
            'cyberpunk': '0x0d0d1a',
            'emerald': '0x051a14',
            'sunset': '0x2b1010'
        }
        bg_color = bg_colors.get(bg_style, '0x1a0933')
        
        font_styles = {
            'default': "Fontname=Liberation Sans,Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2",
            'glowing_neon': "Fontname=Liberation Sans,Fontsize=26,PrimaryColour=&H00FFFF00,OutlineColour=&H00FF00FF,BorderStyle=1,Outline=3,Alignment=2",
            'minimal': "Fontname=Liberation Sans,Fontsize=22,PrimaryColour=&H00E6E6E6,OutlineColour=&H00222222,BorderStyle=3,Outline=1,Alignment=2",
            'aesthetic_bold': "Fontname=Liberation Sans,Fontsize=28,PrimaryColour=&H0080FF80,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Alignment=2"
        }
        chosen_style = font_styles.get(font_style, font_styles['default'])
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c={bg_color}:s=854x480:r=24', 
            '-i', audio_path, 
            '-vf', f"subtitles={srt_path}:force_style='{chosen_style}'", 
            '-c:v', 'libx264', '-tune', 'stillimage', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-shortest',
            output_video_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True)
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{session_id}.mp4',
            'title': title
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
