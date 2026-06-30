# -*- coding: utf-8 -*-
"""مِنزال — أدوات PDF"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("pdf", __name__)

@bp.route("/api/pdf-merge", methods=["POST"])
def api_pdf_merge():
    try:
        from pypdf import PdfWriter
        files=request.files.getlist("files")
        if len(files)<2: return jsonify({"error":"ارفع ملفين على الأقل"}),400
        w=PdfWriter()
        for f in files: w.append(f.stream)
        p=opath("مدموج.pdf")
        with open(p,"wb") as out: w.write(out)
        scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except ImportError: return jsonify({"error":"pypdf غير مثبّت"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 6. تقسيم PDF ───────────────────────────────────────────────────────────

@bp.route("/api/pdf-split", methods=["POST"])
def api_pdf_split():
    try:
        from pypdf import PdfReader, PdfWriter
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع ملف PDF"}),400
        reader=PdfReader(f.stream)
        base=os.path.splitext(f.filename or "pdf")[0]; cnt=0
        for i,page in enumerate(reader.pages,1):
            w=PdfWriter(); w.add_page(page)
            p=opath(f"{base}_صفحة{i}.pdf")
            with open(p,"wb") as out: w.write(out)
            cnt+=1
        scan_media()
        return jsonify({"ok":True,"count":cnt})
    except ImportError: return jsonify({"error":"pypdf غير مثبّت"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 7. تغيير أبعاد صورة ────────────────────────────────────────────────────

@bp.route("/api/pdf-encrypt", methods=["POST"])
def api_pdf_encrypt():
    try:
        from pypdf import PdfReader, PdfWriter
        f=request.files.get("file"); pw=request.form.get("password","")
        if not f: return jsonify({"error":"ارفع ملف PDF"}),400
        if not pw: return jsonify({"error":"أدخل كلمة السر"}),400
        reader=PdfReader(f.stream); writer=PdfWriter()
        for page in reader.pages: writer.add_page(page)
        writer.encrypt(pw)
        base=os.path.splitext(f.filename or "pdf")[0]
        p=opath(f"{base}_مشفّر.pdf")
        with open(p,"wb") as out: writer.write(out); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 15. استخراج نص من PDF ──────────────────────────────────────────────────

@bp.route("/api/pdf-text", methods=["POST"])
def api_pdf_text():
    try:
        from pypdf import PdfReader; f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع ملف PDF"}),400
        reader=PdfReader(f.stream)
        text="".join(page.extract_text() or "" for page in reader.pages)
        base=os.path.splitext(f.filename or "pdf")[0]
        p=opath(f"{base}_نص.txt")
        with open(p,"w",encoding="utf-8") as out: out.write(text); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"chars":len(text),"preview":text[:300]})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 16. قص فيديو ───────────────────────────────────────────────────────────

