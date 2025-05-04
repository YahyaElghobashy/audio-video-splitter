# YouTube processing functions will go here
import yt_dlp
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_youtube_info(url):
    """Fetches metadata for a given YouTube URL."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,  # We only want metadata
        'forcejson': True,      # Force metadata extraction
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            # Simplify the dictionary to return only needed fields
            chapters = [{
                'title': ch.get('title'),
                'start_time': ch.get('start_time'),
                'end_time': ch.get('end_time')
            } for ch in info_dict.get('chapters', []) or []] # Handle None or empty list

            relevant_info = {
                'title': info_dict.get('title'),
                'thumbnail': info_dict.get('thumbnail'),
                'duration': info_dict.get('duration'),
                'duration_string': info_dict.get('duration_string'),
                'chapters': chapters,
                'original_url': info_dict.get('original_url') or info_dict.get('webpage_url') # Fallback
            }
            return relevant_info
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error fetching info for {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching info for {url}: {e}")
        return None


def download_video(url, output_path):
    """Downloads the best quality video for a given YouTube URL."""
    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Prefer mp4
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': False, # Show download progress
        'progress_hooks': [lambda d: print(f"Download status: {d['status']}, progress: {d.get('_percent_str', 'N/A')}")],
        'merge_output_format': 'mp4', # Ensure merged output is mp4
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Return the path to the downloaded file
            downloaded_file = ydl.prepare_filename(info)
            # Sometimes the extension is added by ytdlp after prepare_filename, ensure it exists
            if not os.path.exists(downloaded_file) and os.path.exists(downloaded_file + '.' + info.get('ext')):
                 downloaded_file += '.' + info.get('ext')
            elif not os.path.exists(downloaded_file) and os.path.exists(os.path.splitext(downloaded_file)[0] + '.mp4'): # Check common merged format
                downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp4'

            logging.info(f"Video downloaded successfully to {downloaded_file}")
            return downloaded_file
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading video {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred downloading video {url}: {e}")
        return None


def download_audio(url, output_path):
    """Downloads the best quality audio as mp3 for a given YouTube URL."""
    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192', # Standard quality
        }],
        'quiet': False, # Show download progress
        'progress_hooks': [lambda d: print(f"Download status: {d['status']}, progress: {d.get('_percent_str', 'N/A')}")],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # yt-dlp handles the conversion and naming
            base_filename = ydl.prepare_filename(info).rsplit('.', 1)[0]
            downloaded_file = base_filename + '.mp3'
            if not os.path.exists(downloaded_file):
                 # Fallback in case file naming is unexpected
                 possible_files = [f for f in os.listdir(output_path) if f.startswith(info.get('title')) and f.endswith('.mp3')]
                 if possible_files:
                    downloaded_file = os.path.join(output_path, possible_files[0])
                 else: # If still not found, return None
                    logging.error(f"Could not locate downloaded MP3 file for {url}")
                    return None

            logging.info(f"Audio downloaded and converted successfully to {downloaded_file}")
            return downloaded_file
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Error downloading audio {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred downloading audio {url}: {e}")
        return None

# Example usage (optional, for testing)
if __name__ == '__main__':
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Example URL
    download_dir = "youtube_downloads_test"

    print("--- Fetching Info ---")
    info = get_youtube_info(test_url)
    if info:
        print(f"Title: {info.get('title')}")
        print(f"Thumbnail: {info.get('thumbnail')}")
        print(f"Duration: {info.get('duration_string')}")
        print(f"Chapters ({len(info.get('chapters', []))}):")
        for i, chap in enumerate(info.get('chapters', [])):
            print(f"  {i+1}. {chap.get('title')} ({chap.get('start_time')}s - {chap.get('end_time')}s)")
    else:
        print("Failed to fetch info.")

    # print("\n--- Downloading Video ---")
    # video_path = download_video(test_url, download_dir)
    # if video_path:
    #     print(f"Video saved to: {video_path}")
    # else:
    #     print("Failed to download video.")

    # print("\n--- Downloading Audio (MP3) ---")
    # audio_path = download_audio(test_url, download_dir)
    # if audio_path:
    #     print(f"Audio saved to: {audio_path}")
    # else:
    #     print("Failed to download audio.") 