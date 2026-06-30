# -*- coding: utf-8 -*-
"""مِنزال — أدوات المطوّر"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("dev", __name__)

@bp.route("/api/regex", methods=["POST"])
def api_regex():
    try:
        d=request.get_json(force=True); pattern=d.get("pattern",""); text=d.get("text","")
        if not pattern: return jsonify({"error":"أدخل النمط"}),400
        try: rx=re.compile(pattern)
        except re.error as e: return jsonify({"error":f"نمط خاطئ: {e}"}),400
        matches=rx.findall(text); found=rx.finditer(text)
        positions=[{"match":m.group(),"start":m.start(),"end":m.end()} for m in found]
        return jsonify({"ok":True,"count":len(positions),"matches":positions[:50]})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 48. فك تشفير JWT ───────────────────────────────────────────────────────

@bp.route("/api/jwt-decode", methods=["POST"])
def api_jwt_decode():
    try:
        d=request.get_json(force=True); token=d.get("token","").strip()
        if not token or token.count(".")<2: return jsonify({"error":"توكن JWT غير صالح"}),400
        import json as _json
        parts=token.split(".")
        def b64d(s):
            s+="="*(-len(s)%4)
            return _json.loads(base64.urlsafe_b64decode(s))
        header=b64d(parts[0]); payload=b64d(parts[1])
        return jsonify({"ok":True,"header":header,"payload":payload})
    except Exception as e: return jsonify({"error":"فشل فك التوكن — تأكد أنه JWT صحيح"})

# ─── 49. مقارنة ملفين (Diff) ────────────────────────────────────────────────

@bp.route("/api/diff", methods=["POST"])
def api_diff():
    try:
        import difflib; f1=request.files.get("file1"); f2=request.files.get("file2")
        if not f1 or not f2: return jsonify({"error":"ارفع ملفين"}),400
        t1=f1.read().decode("utf-8","replace").splitlines()
        t2=f2.read().decode("utf-8","replace").splitlines()
        diff=list(difflib.unified_diff(t1,t2,lineterm="",n=2))
        added=sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        removed=sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        return jsonify({"ok":True,"added":added,"removed":removed,"diff":"\n".join(diff[:200])})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 50. منسّق JSON ─────────────────────────────────────────────────────────

@bp.route("/api/json-format", methods=["POST"])
def api_json_format():
    try:
        import json as _json; d=request.get_json(force=True); raw=d.get("json","")
        if not raw.strip(): return jsonify({"error":"أدخل JSON"}),400
        try: parsed=_json.loads(raw)
        except _json.JSONDecodeError as e:
            return jsonify({"error":f"خطأ في السطر {e.lineno}: {e.msg}"}),400
        pretty=_json.dumps(parsed,indent=2,ensure_ascii=False)
        return jsonify({"ok":True,"result":pretty})
    except Exception as e: return jsonify({"error":str(e)}),500

