# -*- coding: utf-8 -*-
"""مِنزال — أدوات الأمان"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("security", __name__)

@bp.route("/api/ela", methods=["POST"])
def api_ela():
    try:
        Image=pil(); from PIL import ImageChops, ImageEnhance
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        orig=Image.open(f.stream).convert("RGB")
        tmp=os.path.join(UPLOAD_DIR,"ela_tmp.jpg"); orig.save(tmp,"JPEG",quality=90)
        resaved=Image.open(tmp)
        diff=ImageChops.difference(orig,resaved)
        ex=diff.getextrema(); mx=max([e[1] for e in ex]) or 1
        diff=ImageEnhance.Brightness(diff).enhance(255.0/mx)
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_ELA.png"); diff.save(p); scan_media(p)
        try: os.remove(tmp)
        except: pass
        return jsonify({"ok":True,"file":os.path.basename(p),"hint":"المناطق المضيئة = احتمال تلاعب"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 32. إخفاء نص في صورة (LSB Steganography) ───────────────────────────────

@bp.route("/api/steg-hide", methods=["POST"])
def api_steg_hide():
    try:
        Image=pil(); f=request.files.get("file"); msg=request.form.get("message","")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        if not msg: return jsonify({"error":"أدخل الرسالة السرية"}),400
        img=Image.open(f.stream).convert("RGB"); px=img.load(); w,h=img.size
        data=msg.encode("utf-8"); bits=''.join(format(b,'08b') for b in data)
        bits=format(len(data),'032b')+bits  # 32-bit length header
        if len(bits)>w*h*3: return jsonify({"error":"الصورة صغيرة على هذه الرسالة"}),400
        idx=0
        for y in range(h):
            for x in range(w):
                if idx>=len(bits): break
                r,g,b=px[x,y]; vals=[r,g,b]
                for c in range(3):
                    if idx<len(bits):
                        vals[c]=(vals[c]&~1)|int(bits[idx]); idx+=1
                px[x,y]=tuple(vals)
            if idx>=len(bits): break
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_مخفي.png"); img.save(p,"PNG"); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"hint":"الرسالة مخبأة — احفظ كـ PNG فقط"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 33. كشف نص مخفي من صورة ────────────────────────────────────────────────

@bp.route("/api/steg-reveal", methods=["POST"])
def api_steg_reveal():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        img=Image.open(f.stream).convert("RGB"); px=img.load(); w,h=img.size
        bits=""
        for y in range(h):
            for x in range(w):
                r,g,b=px[x,y]
                for c in (r,g,b): bits+=str(c&1)
        length=int(bits[:32],2)
        if length<=0 or length>w*h*3//8: return jsonify({"error":"ما فيه رسالة مخفية في هذه الصورة"})
        mbits=bits[32:32+length*8]
        data=bytes(int(mbits[i:i+8],2) for i in range(0,len(mbits),8))
        return jsonify({"ok":True,"message":data.decode("utf-8","replace")})
    except Exception as e: return jsonify({"error":"ما فيه رسالة مخفية أو الصورة تالفة"})

# ─── 34. حذف بيانات EXIF (الموقع الجغرافي) ──────────────────────────────────

@bp.route("/api/exif-strip", methods=["POST"])
def api_exif_strip():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        img=Image.open(f.stream)
        clean=Image.new(img.mode,img.size); clean.putdata(list(img.getdata()))
        if clean.mode in("RGBA","P"): clean=clean.convert("RGB")
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_نظيف.jpg"); clean.save(p,"JPEG",quality=95); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"hint":"تم حذف موقعك وكل البيانات المخفية"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 35. قراءة EXIF كامل ────────────────────────────────────────────────────

@bp.route("/api/exif-read", methods=["POST"])
def api_exif_read():
    try:
        Image=pil(); from PIL.ExifTags import TAGS, GPSTAGS
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        img=Image.open(f.stream); exif=img._getexif()
        if not exif: return jsonify({"ok":True,"data":{},"hint":"ما فيها بيانات EXIF"})
        out={}
        for tid,val in exif.items():
            tag=TAGS.get(tid,tid)
            if tag=="GPSInfo":
                gps={}
                for gid,gval in val.items(): gps[GPSTAGS.get(gid,gid)]=str(gval)
                out["GPS"]=gps
            else:
                s=str(val)
                if len(s)<100: out[str(tag)]=s
        return jsonify({"ok":True,"data":out})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 36. مولّد TOTP ─────────────────────────────────────────────────────────

@bp.route("/api/totp", methods=["POST"])
def api_totp():
    try:
        import pyotp; d=request.get_json(force=True); secret=d.get("secret","").strip().replace(" ","")
        if not secret: return jsonify({"error":"أدخل المفتاح السري"}),400
        totp=pyotp.TOTP(secret)
        return jsonify({"ok":True,"code":totp.now(),"remaining":30-(int(__import__('time').time())%30)})
    except ImportError: return jsonify({"error":"pyotp غير مثبّت — شغّل: pip install pyotp"}),500
    except Exception as e: return jsonify({"error":"المفتاح غير صالح (لازم Base32)"}),500

# ─── 37. صورة → ASCII Art ───────────────────────────────────────────────────

