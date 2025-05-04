#!/usr/bin/env python3
import os, uuid, zipfile, subprocess, shutil, math, json
from flask import Flask, request, render_template, flash, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
from datetime import datetime
import youtube_processor  # Import our YouTube module

# ————— CONFIG —————
UPLOAD_FOLDER = "uploads"
ALLOWED_EXT = {"mp4","mp3","m4a","wav","mov","avi"}
HISTORY_FILE = os.path.join(UPLOAD_FOLDER, "history.json")
# Add new config for YouTube downloads
YOUTUBE_FOLDER = os.path.join(UPLOAD_FOLDER, "youtube")

app = Flask(
    __name__,
    static_folder=UPLOAD_FOLDER,
    static_url_path="/uploads"
)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max upload size

# ensure upload dirs exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(YOUTUBE_FOLDER, exist_ok=True)  # Create YouTube downloads folder

# Custom Jinja2 filter to format timestamps
@app.template_filter('timestamp_format')
def timestamp_format(timestamp):
    """Format a Unix timestamp as a readable date/time"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def allowed_file(fn):
    return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXT

def get_total_duration(path):
    cmd = [
      "ffprobe","-v","error",
      "-select_streams","a:0",
      "-show_entries","format=duration",
      "-of","default=noprint_wrappers=1:nokey=1",
      path
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(p.stdout.strip())

def format_time(s):
    ms = int((s - int(s))*1000)
    h = int(s//3600); m = int((s%3600)//60); sec = int(s%60)
    return f"{h:02d}:{m:02d}:{sec:02d}.{ms:03d}"

def load_history():
    """Load processing history from file"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history):
    """Save processing history to file"""
    # Keep only the last 20 entries
    if len(history) > 20:
        history = history[-20:]
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except Exception:
        pass

def add_to_history(file_info):
    """Add a processed file to history"""
    history = load_history()
    
    # Check if the entry already exists (by folder name)
    for i, entry in enumerate(history):
        if entry.get('folder') == file_info.get('folder'):
            # Update the existing entry and move it to the end (most recent)
            history.pop(i)
            history.append(file_info)
            save_history(history)
            return
    
    # Add new entry
    history.append(file_info)
    save_history(history)

def split_audio_file(inpath, outdir, total, segment, count, base, fade=False):
    """Split a single audio file with FFmpeg"""
    for i in range(count):
        start = segment * i
        seg_d = segment if i < count-1 else (total - start)
        ts_s = format_time(start)
        ts_d = format_time(seg_d)
        outnm = f"{base}-part{i+1:03d}.m4a"
        
        # Build the ffmpeg command
        cmd = [
          "ffmpeg","-hide_banner","-loglevel","error",
          "-i", inpath,
          "-ss", ts_s, "-t", ts_d,
        ]
        
        # Add fade in/out if requested
        if fade:
            fade_duration = min(2, seg_d/4)  # 2 seconds or 25% of segment (whichever is shorter)
            fade_filter = f"afade=t=in:st=0:d={fade_duration},afade=t=out:st={seg_d-fade_duration}:d={fade_duration}"
            cmd.extend(["-af", fade_filter])
            # Can't use copy codec with filters
            cmd.extend(["-map", "0:a", "-c:a", "aac", "-b:a", "192k"])
        else:
            # No fade, just copy audio
            cmd.extend(["-map", "0:a", "-c", "copy"])
            
        cmd.append(os.path.join(outdir, outnm))
        subprocess.run(cmd, check=True)

def split_with_chapters(inpath, outdir, chapters, base, fade=False):
    """Split a file based on provided chapter timestamps"""
    # Ensure chapters are sorted by start time
    chapters = sorted(chapters, key=lambda x: x.get('start_time', 0))
    
    for i, chapter in enumerate(chapters):
        # Get chapter details
        start = chapter.get('start_time', 0)
        end = chapter.get('end_time', 0)
        title = chapter.get('title', f"Chapter {i+1}")
        
        # Calculate duration and format timestamps
        seg_d = end - start
        ts_s = format_time(start)
        ts_d = format_time(seg_d)
        
        # Use chapter title as part of filename (sanitized)
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
        safe_title = safe_title.replace(" ", "_")[:40]  # Limit length
        outnm = f"{base}-{i+1:02d}-{safe_title}.m4a"
        
        # Build the ffmpeg command
        cmd = [
          "ffmpeg","-hide_banner","-loglevel","error",
          "-i", inpath,
          "-ss", ts_s, "-t", ts_d,
        ]
        
        # Add fade in/out if requested
        if fade:
            fade_duration = min(2, seg_d/4)  # 2 seconds or 25% of segment (whichever is shorter)
            fade_filter = f"afade=t=in:st=0:d={fade_duration},afade=t=out:st={seg_d-fade_duration}:d={fade_duration}"
            cmd.extend(["-af", fade_filter])
            # Can't use copy codec with filters
            cmd.extend(["-map", "0:a", "-c:a", "aac", "-b:a", "192k"])
        else:
            # No fade, just copy audio
            cmd.extend(["-map", "0:a", "-c", "copy"])
            
        cmd.append(os.path.join(outdir, outnm))
        subprocess.run(cmd, check=True)

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("⚠️ No file part")
            return redirect(request.url)
        
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash("⚠️ No file selected")
            return redirect(request.url)
            
        # Process the splitting strategy - EITHER by duration OR by number of chunks
        dur = request.form.get("duration", type=float)
        num = request.form.get("num_chunks", type=int)
        
        # Validate that one and only one of the splitting methods is specified
        if num and num > 0:
            if dur and dur > 0:
                flash("⚠️ Please use either duration or number of chunks, not both.")
                return redirect(request.url)
            split_mode = "chunks"
        elif dur and dur > 0:
            split_mode = "duration"
        else:
            flash("⚠️ Please specify either minutes per chunk OR number of chunks.")
            return redirect(request.url)
            
        fade = request.form.get("fade") == "on"

        # Process each file in batch
        processed_folders = []
        
        for file in files:
            if not allowed_file(file.filename):
                flash(f"⚠️ Skipping {file.filename}: not a valid audio/video file")
                continue
                
            # save upload
            uid      = uuid.uuid4().hex
            origname = secure_filename(file.filename)
            inpath   = os.path.join(UPLOAD_FOLDER, uid + "_" + origname)
            file.save(inpath)

            try:
                # get total + decide split
                total = get_total_duration(inpath)
                base = os.path.splitext(origname)[0]
                
                if split_mode == "chunks":
                    count, segment = num, total/num
                else:  # split_mode == "duration"
                    segment = dur * 60
                    count = math.ceil(total / segment)

                # create target folder next to the uploaded file
                parent     = os.path.dirname(inpath)
                folder_name= f"{base}-split-{count}parts"
                outdir     = os.path.join(parent, folder_name)
                if os.path.exists(outdir):
                    shutil.rmtree(outdir)
                os.makedirs(outdir, exist_ok=True)

                # split the file
                split_audio_file(inpath, outdir, total, segment, count, base, fade)

                # zip everything into the same folder
                zip_path = os.path.join(outdir, f"{folder_name}.zip")
                with zipfile.ZipFile(zip_path, "w") as zf:
                    for fn in sorted(os.listdir(outdir)):
                        if fn != os.path.basename(zip_path):
                            zf.write(os.path.join(outdir, fn), arcname=fn)

                # Save to history
                file_info = {
                    "original_name": origname,
                    "folder": folder_name,
                    "parts": count,
                    "timestamp": os.path.getmtime(outdir),
                    "fade_applied": fade,
                    "split_mode": split_mode,
                    "duration_min": dur if split_mode == "duration" else None,
                    "num_chunks": num if split_mode == "chunks" else None
                }
                add_to_history(file_info)
                
                processed_folders.append(folder_name)
            except Exception as e:
                flash(f"⚠️ Error processing {origname}: {str(e)}")

        # Redirect based on number of processed files
        if len(processed_folders) == 0:
            flash("⚠️ No files were successfully processed")
            return redirect(request.url)
        elif len(processed_folders) == 1:
            return redirect(url_for("done", folder=processed_folders[0]))
        else:
            return redirect(url_for("batch_result", folders=",".join(processed_folders)))

    # Load history for display
    history = load_history()
    
    return render_template("index.html", history=history)

@app.route("/batch_result/<folders>")
def batch_result(folders):
    folder_list = folders.split(",")
    batch_results = []
    
    for folder in folder_list:
        upload_root = os.path.abspath(app.config["UPLOAD_FOLDER"])
        outdir = os.path.join(upload_root, folder)
        
        if os.path.exists(outdir):
            all_files = sorted(os.listdir(outdir))
            parts = [f for f in all_files if f.endswith(".m4a")]
            zip_name = f"{folder}.zip"
            
            batch_results.append({
                "folder": folder,
                "parts": parts,
                "zip_name": zip_name,
                "abs_path": outdir
            })
    
    return render_template("batch_result.html", batch_results=batch_results)

@app.route("/done/<folder>")
def done(folder):
    upload_root = os.path.abspath(app.config["UPLOAD_FOLDER"])
    outdir      = os.path.join(upload_root, folder)
    all_files   = sorted(os.listdir(outdir))
    parts       = [f for f in all_files if f.endswith(".m4a")]
    zip_name    = f"{folder}.zip"
    abs_path    = outdir  # absolute on disk
    
    # Load history for display
    history = load_history()
    
    # Find this file's details in history
    file_details = None
    for item in history:
        if item.get('folder') == folder:
            file_details = item
            break
    
    return render_template(
        "done.html",
        folder=folder,
        parts=parts,
        zip_name=zip_name,
        abs_path=abs_path,
        history=history,
        file_details=file_details
    )

@app.route("/download/<folder>/<filename>")
def download(folder, filename):
    directory = os.path.join(app.config["UPLOAD_FOLDER"], folder)
    return send_file(
        os.path.join(directory, filename),
        as_attachment=True
    )

@app.route("/history")
def view_history():
    history = load_history()
    return render_template("history.html", history=history)

@app.route("/youtube", methods=["GET"])
def youtube():
    """Route to show the YouTube processing page"""
    return render_template("youtube.html")

@app.route("/youtube/process", methods=["POST"])
def youtube_process():
    """Process YouTube URLs and actions"""
    # Get the action and YouTube URL from the form
    action = request.form.get("action")
    youtube_url = request.form.get("youtube_url")
    
    if not youtube_url:
        flash("⚠️ No YouTube URL provided", "danger")
        return redirect(url_for("youtube"))
    
    if action == "fetch_info":
        # Fetch video info and render the page with the data
        video_info = youtube_processor.get_youtube_info(youtube_url)
        if not video_info:
            flash("⚠️ Could not fetch information for this YouTube URL. Please check if it's valid.", "danger")
            return redirect(url_for("youtube"))
        
        return render_template("youtube.html", video_info=video_info)
    
    elif action == "download_video":
        # Download the video
        video_info = youtube_processor.get_youtube_info(youtube_url)
        if not video_info:
            flash("⚠️ Could not fetch information for this YouTube URL", "danger")
            return redirect(url_for("youtube"))
        
        # Create a unique folder for this download
        uid = uuid.uuid4().hex[:8]
        title = video_info.get('title', 'unknown')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
        folder_name = f"{safe_title}-{uid}"
        download_dir = os.path.join(YOUTUBE_FOLDER, folder_name)
        
        # Download the video
        downloaded_file = youtube_processor.download_video(youtube_url, download_dir)
        if not downloaded_file:
            flash("⚠️ Failed to download video", "danger")
            return redirect(url_for("youtube"))
        
        # Add to history
        file_info = {
            "original_name": os.path.basename(downloaded_file),
            "folder": folder_name,
            "youtube": True,
            "is_video": True,
            "timestamp": datetime.now().timestamp(),
            "youtube_url": youtube_url,
            "title": video_info.get('title'),
            "has_chapters": bool(video_info.get('chapters', []))
        }
        add_to_history(file_info)
        
        flash(f"✅ Video downloaded successfully!", "success")
        return render_template("youtube.html", video_info=video_info, 
                              download_success=True, download_path=downloaded_file)
    
    elif action == "download_audio":
        # Download the audio
        video_info = youtube_processor.get_youtube_info(youtube_url)
        if not video_info:
            flash("⚠️ Could not fetch information for this YouTube URL", "danger")
            return redirect(url_for("youtube"))
        
        # Create a unique folder for this download
        uid = uuid.uuid4().hex[:8]
        title = video_info.get('title', 'unknown')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
        folder_name = f"{safe_title}-{uid}"
        download_dir = os.path.join(YOUTUBE_FOLDER, folder_name)
        
        # Download the audio
        downloaded_file = youtube_processor.download_audio(youtube_url, download_dir)
        if not downloaded_file:
            flash("⚠️ Failed to download audio", "danger")
            return redirect(url_for("youtube"))
        
        # Add to history
        file_info = {
            "original_name": os.path.basename(downloaded_file),
            "folder": folder_name,
            "youtube": True,
            "is_video": False,
            "timestamp": datetime.now().timestamp(),
            "youtube_url": youtube_url,
            "title": video_info.get('title'),
            "has_chapters": bool(video_info.get('chapters', []))
        }
        add_to_history(file_info)
        
        flash(f"✅ Audio downloaded successfully!", "success")
        return render_template("youtube.html", video_info=video_info, 
                              download_success=True, download_path=downloaded_file)
    
    elif action == "chunk_video" or action == "chunk_audio":
        # Get video info to get chapters
        video_info = youtube_processor.get_youtube_info(youtube_url)
        if not video_info:
            flash("⚠️ Could not fetch information for this YouTube URL", "danger")
            return redirect(url_for("youtube"))
        
        chapters = video_info.get('chapters', [])
        if not chapters:
            flash("⚠️ No chapters found in this video", "warning")
            return redirect(url_for("youtube"))
        
        # Create a unique folder for this download
        uid = uuid.uuid4().hex[:8]
        title = video_info.get('title', 'unknown')
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
        folder_name = f"{safe_title}-chapters-{uid}"
        download_dir = os.path.join(YOUTUBE_FOLDER, folder_name)
        
        try:
            # Download the media (either video or audio)
            if action == "chunk_video":
                downloaded_file = youtube_processor.download_video(youtube_url, download_dir)
                media_type = "video"
            else:  # chunk_audio
                downloaded_file = youtube_processor.download_audio(youtube_url, download_dir)
                media_type = "audio"
                
            if not downloaded_file:
                flash(f"⚠️ Failed to download {media_type}", "danger")
                return redirect(url_for("youtube"))
            
            # Create target folder for split files
            base = os.path.splitext(os.path.basename(downloaded_file))[0]
            outdir = os.path.join(download_dir, f"{base}-split-chapters")
            os.makedirs(outdir, exist_ok=True)
            
            # Split the file based on chapters
            fade = request.form.get("fade") == "on"
            split_with_chapters(downloaded_file, outdir, chapters, base, fade)
            
            # zip everything into the same folder
            zip_file_name = f"{base}-chapters.zip"
            zip_path = os.path.join(outdir, zip_file_name)
            with zipfile.ZipFile(zip_path, "w") as zf:
                for fn in sorted(os.listdir(outdir)):
                    if fn != os.path.basename(zip_path):
                        zf.write(os.path.join(outdir, fn), arcname=fn)
            
            # Add to history
            file_info = {
                "original_name": os.path.basename(downloaded_file),
                "folder": os.path.basename(outdir),
                "youtube": True,
                "is_video": action == "chunk_video",
                "timestamp": datetime.now().timestamp(),
                "youtube_url": youtube_url,
                "title": video_info.get('title'),
                "has_chapters": True,
                "chapter_count": len(chapters),
                "fade_applied": fade
            }
            add_to_history(file_info)
            
            # Redirect to done page
            flash(f"✅ {media_type.capitalize()} successfully split into {len(chapters)} chapters!", "success")
            return redirect(url_for("done", folder=os.path.basename(outdir)))
            
        except Exception as e:
            flash(f"⚠️ Error processing YouTube {media_type}: {str(e)}", "danger")
            return redirect(url_for("youtube"))
    
    # If we got here, the action wasn't recognized
    flash("⚠️ Invalid action", "danger")
    return redirect(url_for("youtube"))

if __name__ == "__main__":
    app.run(debug=True)  # Added debug=True for development