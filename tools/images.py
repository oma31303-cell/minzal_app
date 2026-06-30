# -*- coding: utf-8 -*-
"""مِنزال — أدوات الصور"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("images", __name__)

@bp.route("/api/compress-image", methods=["POST"])
def api_compress_image():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        quality=int(request.form.get("quality",60))
        img=Image.open(f.stream)
        if img.mode in("RGBA","P"): img=img.convert("RGB")
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_مضغوط.jpg"); img.save(p,"JPEG",quality=quality,optimize=True)
        scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"size_kb":round(os.path.getsize(p)/1024)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 4. تحويل صورة ──────────────────────────────────────────────────────────

@bp.route("/api/convert-image", methods=["POST"])
def api_convert_image():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        target=(request.form.get("target") or "jpg").lower()
        img=Image.open(f.stream)
        base=os.path.splitext(f.filename or "image")[0]
        if target=="jpg":
            if img.mode in("RGBA","P"): img=img.convert("RGB")
            p=opath(f"{base}.jpg"); img.save(p,"JPEG",quality=92)
        else:
            p=opath(f"{base}.png"); img.save(p,"PNG")
        scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 5. دمج PDF ─────────────────────────────────────────────────────────────

@bp.route("/api/image-resize", methods=["POST"])
def api_image_resize():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        w=int(request.form.get("width",0)); h=int(request.form.get("height",0))
        img=Image.open(f.stream); ow,oh=img.size
        if w and h: new=img.resize((w,h),Image.LANCZOS)
        elif w: new=img.resize((w,int(oh*w/ow)),Image.LANCZOS)
        elif h: new=img.resize((int(ow*h/oh),h),Image.LANCZOS)
        else: return jsonify({"error":"أدخل العرض أو الارتفاع"}),400
        if new.mode in("RGBA","P"): new=new.convert("RGB")
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_معدّل.jpg"); new.save(p,"JPEG",quality=92); scan_media(p)
        nw,nh=new.size
        return jsonify({"ok":True,"file":os.path.basename(p),"size":f"{nw}×{nh}"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 8. تدوير صورة ──────────────────────────────────────────────────────────

@bp.route("/api/image-rotate", methods=["POST"])
def api_image_rotate():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        angle=int(request.form.get("angle",90))
        img=Image.open(f.stream).rotate(-angle,expand=True)
        if img.mode in("RGBA","P"): img=img.convert("RGB")
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_مدوّر.jpg"); img.save(p,"JPEG",quality=92); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 9. أبيض وأسود ──────────────────────────────────────────────────────────

@bp.route("/api/image-grayscale", methods=["POST"])
def api_image_grayscale():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        img=Image.open(f.stream).convert("L").convert("RGB")
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_أبيض_وأسود.jpg"); img.save(p,"JPEG",quality=92); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 10. معلومات صورة ───────────────────────────────────────────────────────

@bp.route("/api/image-info", methods=["POST"])
def api_image_info():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        data=f.read(); img=Image.open(io.BytesIO(data)); w,h=img.size
        return jsonify({"ok":True,"width":w,"height":h,"mode":img.mode,"format":img.format or "?","size_kb":round(len(data)/1024,1)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 11. دمج صور في PDF ─────────────────────────────────────────────────────

@bp.route("/api/images-to-pdf", methods=["POST"])
def api_images_to_pdf():
    try:
        Image=pil(); files=request.files.getlist("files")
        if not files: return jsonify({"error":"ارفع صور"}),400
        imgs=[]
        for f in files:
            img=Image.open(f.stream)
            if img.mode in("RGBA","P"): img=img.convert("RGB")
            imgs.append(img)
        p=opath("صور_مدمجة.pdf")
        imgs[0].save(p,"PDF",save_all=True,append_images=imgs[1:]); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"count":len(imgs)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 12. كولاج صور ──────────────────────────────────────────────────────────

@bp.route("/api/image-collage", methods=["POST"])
def api_image_collage():
    try:
        Image=pil(); files=request.files.getlist("files")
        if len(files)<2: return jsonify({"error":"ارفع صورتين على الأقل"}),400
        imgs=[Image.open(f.stream).convert("RGB") for f in files]
        H=600
        resized=[img.resize((int(img.width*H/img.height),H),Image.LANCZOS) for img in imgs]
        W=sum(img.width for img in resized)
        canvas=Image.new("RGB",(W,H),(30,30,30)); x=0
        for img in resized: canvas.paste(img,(x,0)); x+=img.width
        p=opath("كولاج.jpg"); canvas.save(p,"JPEG",quality=90); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 13. إزالة خلفية ────────────────────────────────────────────────────────

@bp.route("/api/remove-bg", methods=["POST"])
def api_remove_bg():
    try:
        from rembg import remove; f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        result=remove(f.read())
        base=os.path.splitext(f.filename or "image")[0]
        p=opath(f"{base}_بدون_خلفية.png")
        with open(p,"wb") as out: out.write(result); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except ImportError: return jsonify({"error":"rembg غير مثبّت — شغّل: pip install rembg"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 14. تشفير PDF ──────────────────────────────────────────────────────────

@bp.route("/api/images-to-pdf-hq", methods=["POST"])
def api_images_to_pdf_hq():
    try:
        Image=pil(); files=request.files.getlist("files")
        if not files: return jsonify({"error":"ارفع صور"}),400
        imgs=[]; dpi_val=int(request.form.get("dpi",300))
        for f in files:
            img=Image.open(f.stream)
            # حافظ على الدقة الكاملة، حوّل فقط لـ RGB لو فيه شفافية
            if img.mode=="RGBA":
                bg=Image.new("RGB",img.size,(255,255,255)); bg.paste(img,mask=img.split()[3]); img=bg
            elif img.mode in("P","LA","L"): img=img.convert("RGB")
            imgs.append(img)
        p=opath("صور_عالية_الجودة.pdf")
        # quality=100 بدون ضغط + DPI عالي = أعلى جودة ممكنة
        imgs[0].save(p,"PDF",save_all=True,append_images=imgs[1:],
                     resolution=float(dpi_val),quality=100,optimize=False)
        scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"count":len(imgs),
                        "size_mb":round(os.path.getsize(p)/1048576,2),"dpi":dpi_val})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 52. تحسين صورة + تحويل PDF (للواتساب) ──────────────────────────────────

@bp.route("/api/enhance-pdf", methods=["POST"])
def api_enhance_pdf():
    try:
        Image=pil()
        from PIL import ImageEnhance, ImageFilter, ImageOps
        files=request.files.getlist("files")
        if not files: return jsonify({"error":"ارفع صور"}),400
        level=request.form.get("level","auto")
        imgs=[]
        for f in files:
            img=Image.open(f.stream)
            # تصحيح الدوران حسب EXIF
            img=ImageOps.exif_transpose(img)
            if img.mode=="RGBA":
                bg=Image.new("RGB",img.size,(255,255,255)); bg.paste(img,mask=img.split()[3]); img=bg
            elif img.mode!="RGB": img=img.convert("RGB")
            if level=="pure":
                pass  # بدون أي تحسين — تحويل نقي يحافظ على الصورة كما هي
            elif level=="strong":
                img=ImageOps.autocontrast(img,cutoff=1)
                img=ImageEnhance.Color(img).enhance(1.10)
                img=ImageEnhance.Sharpness(img).enhance(1.3)
            else:  # auto — تحسين خفيف جدًا للصور العادية
                img=ImageOps.autocontrast(img,cutoff=0.5)
                img=ImageEnhance.Sharpness(img).enhance(1.15)
            imgs.append(img)
        p=opath("صور_محسّنة.pdf")
        imgs[0].save(p,"PDF",save_all=True,append_images=imgs[1:],
                     resolution=300.0,quality=100,optimize=False)
        scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"count":len(imgs),
                        "size_mb":round(os.path.getsize(p)/1048576,2)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/ascii-art", methods=["POST"])
def api_ascii_art():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        width=int(request.form.get("width",100))
        chars="@%#*+=-:. "
        img=Image.open(f.stream).convert("L")
        w,h=img.size; ratio=h/w*0.55; new_h=int(width*ratio)
        img=img.resize((width,new_h)); px=list(img.getdata())
        art=""
        for i,p in enumerate(px):
            art+=chars[p*len(chars)//256]
            if (i+1)%width==0: art+="\n"
        base=os.path.splitext(f.filename or "image")[0]
        fp=opath(f"{base}_ascii.txt")
        with open(fp,"w") as out: out.write(art); scan_media(fp)
        return jsonify({"ok":True,"art":art,"file":os.path.basename(fp)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 38. استخراج لوحة ألوان ─────────────────────────────────────────────────

@bp.route("/api/color-palette", methods=["POST"])
def api_color_palette():
    try:
        Image=pil(); f=request.files.get("file")
        if not f: return jsonify({"error":"ارفع صورة"}),400
        img=Image.open(f.stream).convert("RGB"); img.thumbnail((150,150))
        result=img.quantize(colors=6,method=Image.FASTOCTREE).convert("RGB")
        colors=result.getcolors(150*150)
        colors=sorted(colors,key=lambda x:-x[0])[:6]
        hexes=['#%02x%02x%02x'%c[1] for c in colors]
        return jsonify({"ok":True,"colors":hexes})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 39. مولّد تدرّج لوني ────────────────────────────────────────────────────

@bp.route("/api/gradient", methods=["POST"])
def api_gradient():
    try:
        Image=pil(); d=request.get_json(force=True)
        c1=d.get("color1","#00e5a0").lstrip("#"); c2=d.get("color2","#0a0e14").lstrip("#")
        w=int(d.get("width",1080)); h=int(d.get("height",1920))
        r1,g1,b1=int(c1[0:2],16),int(c1[2:4],16),int(c1[4:6],16)
        r2,g2,b2=int(c2[0:2],16),int(c2[2:4],16),int(c2[4:6],16)
        img=Image.new("RGB",(w,h)); px=img.load()
        for y in range(h):
            t=y/h; r=int(r1+(r2-r1)*t); g=int(g1+(g2-g1)*t); b=int(b1+(b2-b1)*t)
            for x in range(w): px[x,y]=(r,g,b)
        p=opath("تدرج.png"); img.save(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 40. نص → صورة ──────────────────────────────────────────────────────────

@bp.route("/api/text-to-image", methods=["POST"])
def api_text_to_image():
    try:
        Image=pil(); from PIL import ImageDraw, ImageFont
        d=request.get_json(force=True); text=d.get("text","").strip()
        if not text: return jsonify({"error":"أدخل النص"}),400
        bg=d.get("bg","#0a0e14").lstrip("#"); fg=d.get("fg","#00e5a0").lstrip("#")
        bgc=tuple(int(bg[i:i+2],16) for i in (0,2,4)); fgc=tuple(int(fg[i:i+2],16) for i in (0,2,4))
        W,H=1080,1080; img=Image.new("RGB",(W,H),bgc); draw=ImageDraw.Draw(img)
        try: font=ImageFont.truetype("/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",60)
        except: font=ImageFont.load_default()
        lines=[]; words=text.split(); cur=""
        for word in words:
            test=(cur+" "+word).strip()
            if draw.textlength(test,font=font)<W-120: cur=test
            else: lines.append(cur); cur=word
        if cur: lines.append(cur)
        total_h=len(lines)*75; y=(H-total_h)//2
        for line in lines:
            lw=draw.textlength(line,font=font); draw.text(((W-lw)//2,y),line,fill=fgc,font=font); y+=75
        p=opath("نص_صورة.png"); img.save(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 41. QR واي فاي ─────────────────────────────────────────────────────────

