#!/usr/bin/env python3
import argparse, os, sys, subprocess, shutil, math

def get_total_duration(input_file):
    """Return total duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())

def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS.mmm for ffmpeg."""
    ms = int((seconds - int(seconds)) * 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def split_manual(input_file, output_dir, total_duration, segment_sec, count, base_name):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(count):
        start = segment_sec * i
        dur = segment_sec if i < count - 1 else (total_duration - start)
        ts_start = format_timestamp(start)
        ts_dur   = format_timestamp(dur)
        out_name = f"{base_name}-part{i+1:03d}.m4a"
        out_path = os.path.join(output_dir, out_name)
        print(f"→ Writing {out_name} (start={ts_start}, dur={ts_dur})")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", input_file,
            "-ss", ts_start,
            "-t", ts_dur,
            "-map", "0:a",
            "-c", "copy",
            out_path
        ], check=True)
    print("\n✅ Done! Chunks saved to:", output_dir)

def main():
    # check ffmpeg/ffprobe
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: ffmpeg/ffprobe not found. Install with `brew install ffmpeg`.", file=sys.stderr)
        sys.exit(1)

    p = argparse.ArgumentParser(
        description="Split an audio/video file into fixed-length or N equal chunks."
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("-d", "--duration", type=float,
                     help="chunk length in minutes")
    grp.add_argument("-n", "--num-chunks", type=int,
                     help="number of equal chunks")
    p.add_argument("-i", "--input", required=True,
                   help="path to input file (mp4/mp3/…)")
    p.add_argument("-o", "--output",
                   help="optional override: output directory (default: sibling folder named <base>-split-<N>parts>)")
    args = p.parse_args()

    total = get_total_duration(args.input)
    base = os.path.splitext(os.path.basename(args.input))[0]

    if args.duration:
        segment = args.duration * 60
        count   = math.ceil(total / segment)
    else:
        count   = args.num_chunks
        segment = total / count

    # decide output folder
    if args.output:
        output_dir = args.output
    else:
        parent     = os.path.dirname(os.path.abspath(args.input)) or "."
        folder_name= f"{base}-split-{count}parts"
        output_dir = os.path.join(parent, folder_name)

    print(f"Total duration: {total:.1f}s → {count} chunks of ≈{segment:.1f}s each")
    split_manual(args.input, output_dir, total, segment, count, base)

if __name__ == "__main__":
    main()