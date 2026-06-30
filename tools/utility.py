# -*- coding: utf-8 -*-
"""مِنزال — أدوات متنوعة"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("utility", __name__)

@bp.route("/api/qr", methods=["POST"])
def api_qr():
    try:
        import qrcode; d=request.get_json(force=True); text=d.get("text","").strip()
        if not text: return jsonify({"error":"أدخل نص أو رابط"}),400
        safe=re.sub(r'[^\w\u0600-\u06FF]+','_',text)[:40] or "qr"
        qr=qrcode.QRCode(box_size=12,border=2); qr.add_data(text); qr.make(fit=True)
        img=qr.make_image(fill_color="black",back_color="white")
        p=opath(f"QR_{safe}.png"); img.save(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except ImportError: return jsonify({"error":"qrcode غير مثبّت"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 3. ضغط صورة ────────────────────────────────────────────────────────────

@bp.route("/api/barcode", methods=["POST"])
def api_barcode():
    try:
        import barcode; from barcode.writer import ImageWriter
        d=request.get_json(force=True); text=d.get("text","").strip()
        if not text: return jsonify({"error":"أدخل نصًا أو رقمًا"}),400
        safe=re.sub(r'[^\w]+','_',text)[:30]
        p=opath(f"barcode_{safe}")
        bc=barcode.get("code128",text,writer=ImageWriter())
        bc.save(p); final=p+".png"; scan_media(final)
        return jsonify({"ok":True,"file":os.path.basename(final)})
    except ImportError: return jsonify({"error":"python-barcode غير مثبّت — شغّل: pip install python-barcode pillow"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 23. ضغط ملفات ZIP ──────────────────────────────────────────────────────

@bp.route("/api/qr-scan", methods=["POST"])
def api_qr_scan():
    try:
        from pyzbar.pyzbar import decode; Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة فيها QR"}),400
        img=Image.open(f.stream)
        codes=decode(img)
        if not codes: return jsonify({"error":"ما لقيت QR في الصورة"})
        results=[c.data.decode("utf-8","replace") for c in codes]
        return jsonify({"ok":True,"results":results,"count":len(results)})
    except ImportError: return jsonify({"error":"pyzbar غير مثبّت — شغّل: pkg install zbar && pip install pyzbar"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

@bp.route("/api/zip-create", methods=["POST"])
def api_zip_create():
    try:
        files=request.files.getlist("files")
        if not files: return jsonify({"error":"ارفع ملفات"}),400
        p=opath("ملفات_مضغوطة.zip")
        with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as zf:
            for f in files: zf.writestr(f.filename,f.read())
        scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"size_kb":round(os.path.getsize(p)/1024)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 24. فك ضغط ZIP ─────────────────────────────────────────────────────────

@bp.route("/api/zip-extract", methods=["POST"])
def api_zip_extract():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع ملف ZIP"}),400
        out_dir=opath(os.path.splitext(f.filename or "archive")[0])
        os.makedirs(out_dir,exist_ok=True)
        data=f.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            cnt=len(zf.namelist()); zf.extractall(out_dir)
        scan_media(out_dir)
        return jsonify({"ok":True,"count":cnt,"folder":os.path.basename(out_dir)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 25. CSV → Excel ────────────────────────────────────────────────────────

@bp.route("/api/csv-excel", methods=["POST"])
def api_csv_excel():
    try:
        import openpyxl; f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع ملف CSV"}),400
        content=f.read().decode("utf-8-sig",errors="replace")
        reader=csv.reader(content.splitlines())
        wb=openpyxl.Workbook(); ws=wb.active; cnt=0
        for row in reader: ws.append(row); cnt+=1
        base=os.path.splitext(f.filename or "data")[0]
        p=opath(f"{base}.xlsx"); wb.save(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"rows":cnt})
    except ImportError: return jsonify({"error":"openpyxl غير مثبّت — شغّل: pip install openpyxl"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 26. معلومات ملف ────────────────────────────────────────────────────────

@bp.route("/api/file-info", methods=["POST"])
def api_file_info():
    try:
        f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع ملف"}),400
        data=f.read(); sz=len(data); ext=os.path.splitext(f.filename or "")[-1].lower()
        return jsonify({"ok":True,"name":f.filename,"size_kb":round(sz/1024,1),"size_mb":round(sz/1048576,2),"extension":ext or "؟","type":f.content_type or "؟"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 27. تشفير نص ───────────────────────────────────────────────────────────

@bp.route("/api/text-encrypt", methods=["POST"])
def api_text_encrypt():
    try:
        d=request.get_json(force=True)
        text=d.get("text",""); pw=d.get("password",""); action=d.get("action","encrypt")
        if not text: return jsonify({"error":"أدخل نصًا"}),400
        key=hashlib.sha256(pw.encode()).digest()[:16]
        if action=="encrypt":
            tb=text.encode("utf-8"); res=bytes([b^key[i%16] for i,b in enumerate(tb)])
            return jsonify({"ok":True,"result":base64.b64encode(res).decode()})
        else:
            db=base64.b64decode(text); res=bytes([b^key[i%16] for i,b in enumerate(db)])
            return jsonify({"ok":True,"result":res.decode("utf-8")})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 28. OCR - استخراج نص من صورة ──────────────────────────────────────────

@bp.route("/api/ocr", methods=["POST"])
def api_ocr():
    try:
        import pytesseract; Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        lang=request.form.get("lang","ara+eng")
        img=Image.open(f.stream)
        text=pytesseract.image_to_string(img,lang=lang)
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_نص.txt")
        with open(p,"w",encoding="utf-8") as out: out.write(text); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"preview":text[:300],"chars":len(text)})
    except ImportError: return jsonify({"error":"pytesseract غير مثبّت — شغّل: pkg install tesseract && pip install pytesseract"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 29. مسح QR من صورة ─────────────────────────────────────────────────────

