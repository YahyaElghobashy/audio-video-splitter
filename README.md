# 🎧 Audio and Video Splitter

Split any audio or video file into fixed-length chunks, evenly into N parts, or by YouTube chapters.  
Supports `.mp4`, `.mp3`, `.m4a`, `.wav`, `.mov`, `.avi`.  
Includes both a **command-line tool** and a clean **web interface**.

---

## 🚀 Features

✅ Split by duration (e.g., 20-minute chunks)  
✅ Split by count (e.g., 5 equal parts)  
✅ YouTube video/audio processing  
✅ Split by YouTube chapters  
✅ Auto-detect duration  
✅ Outputs neatly grouped folders  
✅ Clean ZIP download  
✅ Browser UI with upload, feedback, and file management  
✅ Works offline (except YouTube feature)  
✅ PWA support for iOS and macOS

---

## 🧰 Requirements

- System with:
  - Python 3.8+
  - FFmpeg
- For local development:
  - Python virtual environment
  - Git (optional)

---

## 🛠️ Installation

```bash
# Install ffmpeg (macOS)
brew install ffmpeg

# Install ffmpeg (Ubuntu/Debian)
sudo apt install ffmpeg

# Clone project
git clone https://github.com/YahyaElghobashy/audio-video-splitter.git
cd audio-video-splitter

# Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the web app
python app.py
```

## 💻 CLI Usage

```bash
# Split into 20-minute chunks
python split_audio.py -i /path/to/file.mp4 -d 20

# Split into 5 equal parts
python split_audio.py -i /path/to/file.mp4 -n 5

# Apply fade in/out effect
python split_audio.py -i /path/to/file.mp4 -d 20 -f
```

## 🌐 Web Interface

The web interface offers:

1. **File Upload Splitting**: Upload and split audio/video files
2. **YouTube Processing**: Download and process YouTube videos
   - Extract video information including chapters
   - Download full videos or just the audio
   - Split videos/audio using YouTube chapters as timestamps
3. **History Management**: View and manage previously processed files

## 🐳 Docker Usage

```bash
# Build the Docker image
docker build -t audio-video-splitter .

# Run the container
docker run -p 10000:10000 audio-video-splitter
```

Visit http://localhost:10000 in your browser to access the app.

## 📱 Mobile Usage

The app is designed to be mobile-friendly and can be installed as a PWA on iOS devices.

---

Developed by Yahya Elghobashy
GitHub: https://github.com/YahyaElghobashy/audio-video-splitter