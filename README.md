# 🎧 Audio/Video Splitter Tool

A simple and efficient tool to split any **audio** or **video** file into:

- ⏱ Fixed-length chunks (e.g. 20 min each), or
- 🔢 A fixed number of equal-sized chunks

This tool is ideal for splitting audiobooks, podcasts, YouTube lectures, or long recordings.  
It includes both:

- A powerful **Command-Line Interface (CLI)** (`split_audio.py`)
- A user-friendly **Web UI** (`app.py` with Flask)

---

## ✅ Features

- Split by **duration** (e.g. every 20 minutes)
- Split by **number of parts** (e.g. 5 equal parts)
- Automatically extracts and splits **audio only**
- Chunks are saved into a **named folder** next to the original
- Built-in **ZIP archive** for easy downloads (Web UI)
- Beautiful **confirmation UI** with direct **Finder link** (Mac)
- Supports `.mp4`, `.mp3`, `.m4a`, `.wav`, `.mov`, `.avi`

---

## 🛠 Prerequisites

- **macOS** (tested)
- **Python 3.8+**
- **FFmpeg & FFprobe**

Install FFmpeg via [Homebrew](https://brew.sh):

```bash
brew install ffmpeg