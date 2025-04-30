#!/usr/bin/env python3
import os, uuid, zipfile, subprocess, shutil, math
from flask import Flask, request, render_template, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename

# ————— CONFIG —————
UPLOAD_FOLDER = "uploads"
ALLOWED_EXT = {"mp4","mp3","m4a","wav","mov","avi"}

app = Flask(
    __name__,
    static_folder=UPLOAD_FOLDER,
    static_url_path="/uploads"
)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ensure upload dir exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        dur  = request.form.get("duration", type=float)
        num  = request.form.get("num_chunks", type=int)

        if not file or not allowed_file(file.filename):
            flash("⚠️ Upload a valid audio/video file.")
            return redirect(request.url)
        if (not dur or dur <= 0) and (not num or num <= 0):
            flash("⚠️ Specify a chunk length OR number of chunks.")
            return redirect(request.url)

        # save upload
        uid      = uuid.uuid4().hex
        origname = secure_filename(file.filename)
        inpath   = os.path.join(UPLOAD_FOLDER, uid + "_" + origname)
        file.save(inpath)

        # get total + decide split
        total    = get_total_duration(inpath)
        base     = os.path.splitext(origname)[0]
        if num and num > 0:
            count, segment = num, total/num
        else:
            segment        = dur * 60
            count          = math.ceil(total/segment)

        # create target folder next to the uploaded file
        parent     = os.path.dirname(inpath)
        folder_name= f"{base}-split-{count}parts"
        outdir     = os.path.join(parent, folder_name)
        if os.path.exists(outdir):
            shutil.rmtree(outdir)
        os.makedirs(outdir, exist_ok=True)

        # split with ffmpeg
        for i in range(count):
            start = segment * i
            seg_d = segment if i < count-1 else (total - start)
            ts_s = format_time(start)
            ts_d = format_time(seg_d)
            outnm = f"{base}-part{i+1:03d}.m4a"
            cmd = [
              "ffmpeg","-hide_banner","-loglevel","error",
              "-i", inpath,
              "-ss", ts_s, "-t", ts_d,
              "-map","0:a","-c","copy",
              os.path.join(outdir, outnm)
            ]
            subprocess.run(cmd, check=True)

        # zip everything into the same folder
        zip_path = os.path.join(outdir, f"{folder_name}.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for fn in sorted(os.listdir(outdir)):
                if fn != os.path.basename(zip_path):
                    zf.write(os.path.join(outdir, fn), arcname=fn)

        # done → confirmation page
        return redirect(url_for("done", folder=folder_name))

    return render_template("index.html")

@app.route("/done/<folder>")
def done(folder):
    upload_root = os.path.abspath(app.config["UPLOAD_FOLDER"])
    outdir      = os.path.join(upload_root, folder)
    all_files   = sorted(os.listdir(outdir))
    parts       = [f for f in all_files if f.endswith(".m4a")]
    zip_name    = f"{folder}.zip"
    abs_path    = outdir  # absolute on disk
    return render_template(
        "done.html",
        folder=folder,
        parts=parts,
        zip_name=zip_name,
        abs_path=abs_path
    )

@app.route("/download/<folder>/<filename>")
def download(folder, filename):
    directory = os.path.join(app.config["UPLOAD_FOLDER"], folder)
    return send_file(
        os.path.join(directory, filename),
        as_attachment=True
    )

if __name__ == "__main__":
    app.run()