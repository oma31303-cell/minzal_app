# -*- coding: utf-8 -*-
"""مِنزال — أدوات الفيديو والصوت"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("video", __name__)

@bp.route("/api/video-cut", methods=["POST"])
def api_video_cut():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع فيديو"}),400
        start=request.form.get("start","0"); end=request.form.get("end","")
        inp=save_up(f); base=os.path.splitext(f.filename or "video")[0]
        p=opath(f"{base}_مقصوص.mp4"); jid=start_job(p)
        cmd=["-y","-i",inp,"-ss",start]+(["-to",end] if end else [])+["-c","copy",p]
        threading.Thread(target=ffmpeg_job,args=(cmd,jid),daemon=True).start()
        return jsonify({"job_id":jid})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 17. استخراج صوت من فيديو ───────────────────────────────────────────────

@bp.route("/api/extract-audio", methods=["POST"])
def api_extract_audio():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع فيديو"}),400
        fmt=request.form.get("format","mp3")
        inp=save_up(f); base=os.path.splitext(f.filename or "video")[0]
        p=opath(f"{base}_صوت.{fmt}"); jid=start_job(p)
        cmd=["-y","-i",inp,"-vn","-acodec","libmp3lame" if fmt=="mp3" else "copy",p]
        threading.Thread(target=ffmpeg_job,args=(cmd,jid),daemon=True).start()
        return jsonify({"job_id":jid})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 18. تحويل صيغة صوت ────────────────────────────────────────────────────

@bp.route("/api/audio-convert", methods=["POST"])
def api_audio_convert():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع ملف صوت"}),400
        fmt=request.form.get("format","mp3")
        inp=save_up(f); base=os.path.splitext(f.filename or "audio")[0]
        p=opath(f"{base}.{fmt}"); jid=start_job(p)
        amap={"mp3":["libmp3lame","-q:a","2"],"aac":["aac","-b:a","192k"],"wav":["pcm_s16le"],"ogg":["libvorbis"]}
        ac=amap.get(fmt,["libmp3lame","-q:a","2"])
        cmd=["-y","-i",inp,"-vn","-acodec"]+ac+[p]
        threading.Thread(target=ffmpeg_job,args=(cmd,jid),daemon=True).start()
        return jsonify({"job_id":jid})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 19. فيديو → GIF ────────────────────────────────────────────────────────

@bp.route("/api/video-to-gif", methods=["POST"])
def api_video_to_gif():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع فيديو"}),400
        fps=request.form.get("fps","10"); width=request.form.get("width","480")
        start=request.form.get("start","0"); dur=request.form.get("duration","5")
        inp=save_up(f); base=os.path.splitext(f.filename or "video")[0]
        p=opath(f"{base}.gif"); jid=start_job(p)
        cmd=["-y","-ss",start,"-t",dur,"-i",inp,"-vf",f"fps={fps},scale={width}:-1:flags=lanczos","-loop","0",p]
        threading.Thread(target=ffmpeg_job,args=(cmd,jid),daemon=True).start()
        return jsonify({"job_id":jid})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 20. لقطة من فيديو ──────────────────────────────────────────────────────

@bp.route("/api/video-screenshot", methods=["POST"])
def api_video_screenshot():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع فيديو"}),400
        t=request.form.get("time","00:00:02")
        inp=save_up(f); base=os.path.splitext(f.filename or "video")[0]
        p=opath(f"{base}_لقطة.jpg"); jid=start_job(p)
        cmd=["-y","-ss",t,"-i",inp,"-vframes","1","-q:v","2",p]
        threading.Thread(target=ffmpeg_job,args=(cmd,jid),daemon=True).start()
        return jsonify({"job_id":jid})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 21. ضغط فيديو ──────────────────────────────────────────────────────────

@bp.route("/api/video-compress", methods=["POST"])
def api_video_compress():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع فيديو"}),400
        crf=request.form.get("quality","28")
        inp=save_up(f); base=os.path.splitext(f.filename or "video")[0]
        p=opath(f"{base}_مضغوط.mp4"); jid=start_job(p)
        cmd=["-y","-i",inp,"-vcodec","libx264","-crf",crf,"-acodec","aac",p]
        threading.Thread(target=ffmpeg_job,args=(cmd,jid),daemon=True).start()
        return jsonify({"job_id":jid})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 22. باركود ─────────────────────────────────────────────────────────────

