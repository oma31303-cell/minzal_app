# -*- coding: utf-8 -*-
"""مِنزال — أدوات الملفات (دفعة 3أ)"""
import os, hashlib
from flask import Blueprint, request, jsonify
from core import DOWNLOAD_DIR

bp = Blueprint("files", __name__)

# مجلدات يُسمح بفحصها (أمان)
SCAN_ROOTS = ["/storage/emulated/0/Download","/storage/emulated/0/DCIM",
              "/storage/emulated/0/Pictures","/storage/emulated/0/Documents",
              "/storage/emulated/0"]

def safe_root(p):
    """يتأكد أن المسار ضمن المسموح"""
    p=os.path.abspath(p)
    return any(p.startswith(r) for r in SCAN_ROOTS)

# ─── 1. أكبر الملفات ────────────────────────────────────────────────────────
@bp.route("/api/largest-files", methods=["POST"])
def api_largest_files():
    try:
        d=request.get_json(force=True)
        root=d.get("path","/storage/emulated/0/Download")
        limit=int(d.get("limit",20))
        if not safe_root(root): return jsonify({"error":"مسار غير مسموح"}),400
        if not os.path.isdir(root): return jsonify({"error":"المجلد غير موجود"}),400
        files=[]
        for dp,dn,fn in os.walk(root):
            # تجاهل المجلدات المخفية
            dn[:]=[x for x in dn if not x.startswith(".")]
            for name in fn:
                try:
                    fp=os.path.join(dp,name); sz=os.path.getsize(fp)
                    files.append((sz,fp))
                except: pass
        files.sort(reverse=True)
        top=[{"name":os.path.basename(f),"path":f,
              "size_mb":round(s/1048576,2),"folder":os.path.dirname(f).replace("/storage/emulated/0","")}
             for s,f in files[:limit]]
        return jsonify({"ok":True,"files":top,"scanned":len(files)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 2. إيجاد الملفات المكررة ───────────────────────────────────────────────
@bp.route("/api/duplicate-files", methods=["POST"])
def api_duplicate_files():
    try:
        d=request.get_json(force=True)
        root=d.get("path","/storage/emulated/0/Download")
        if not safe_root(root): return jsonify({"error":"مسار غير مسموح"}),400
        if not os.path.isdir(root): return jsonify({"error":"المجلد غير موجود"}),400
        # نجمع حسب الحجم أولاً (سريع)، ثم hash للمتشابهة
        by_size={}
        for dp,dn,fn in os.walk(root):
            dn[:]=[x for x in dn if not x.startswith(".")]
            for name in fn:
                try:
                    fp=os.path.join(dp,name); sz=os.path.getsize(fp)
                    if sz>0: by_size.setdefault(sz,[]).append(fp)
                except: pass
        dups=[]
        for sz,paths in by_size.items():
            if len(paths)<2: continue
            by_hash={}
            for fp in paths:
                try:
                    h=hashlib.md5()
                    with open(fp,"rb") as f:
                        h.update(f.read(65536))  # أول 64KB يكفي للكشف السريع
                    by_hash.setdefault(h.hexdigest(),[]).append(fp)
                except: pass
            for hsh,group in by_hash.items():
                if len(group)>1:
                    dups.append({"size_mb":round(sz/1048576,2),"count":len(group),
                                 "files":[{"name":os.path.basename(p),
                                           "folder":os.path.dirname(p).replace("/storage/emulated/0","")} for p in group]})
        dups.sort(key=lambda x:-x["size_mb"])
        wasted=sum(g["size_mb"]*(g["count"]-1) for g in dups)
        return jsonify({"ok":True,"groups":dups[:30],"total_groups":len(dups),
                        "wasted_mb":round(wasted,2)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 3. تحليل مجلد ──────────────────────────────────────────────────────────
@bp.route("/api/folder-stats", methods=["POST"])
def api_folder_stats():
    try:
        d=request.get_json(force=True)
        root=d.get("path","/storage/emulated/0/Download")
        if not safe_root(root): return jsonify({"error":"مسار غير مسموح"}),400
        if not os.path.isdir(root): return jsonify({"error":"المجلد غير موجود"}),400
        total_size=0; total_files=0; by_ext={}
        for dp,dn,fn in os.walk(root):
            dn[:]=[x for x in dn if not x.startswith(".")]
            for name in fn:
                try:
                    fp=os.path.join(dp,name); sz=os.path.getsize(fp)
                    total_size+=sz; total_files+=1
                    ext=os.path.splitext(name)[1].lower() or "بدون امتداد"
                    if ext not in by_ext: by_ext[ext]={"count":0,"size":0}
                    by_ext[ext]["count"]+=1; by_ext[ext]["size"]+=sz
                except: pass
        types=sorted([{"ext":k,"count":v["count"],"size_mb":round(v["size"]/1048576,2)}
                      for k,v in by_ext.items()],key=lambda x:-x["size_mb"])[:15]
        return jsonify({"ok":True,"total_files":total_files,
                        "total_size_mb":round(total_size/1048576,2),
                        "total_size_gb":round(total_size/1073741824,2),"types":types})
    except Exception as e: return jsonify({"error":str(e)}),500
