# -*- coding: utf-8 -*-
"""مِنزال — أدوات الأعمال"""
import os, re, io, csv, uuid, zipfile, base64, hashlib, threading, subprocess
from flask import Blueprint, request, jsonify
from core import (scan_media, sname, opath, save_up, pil,
                  ffmpeg_job, start_job, JOBS, TOOLS_DIR, UPLOAD_DIR, DOWNLOAD_DIR)

bp = Blueprint("business", __name__)

@bp.route("/api/qr-wifi", methods=["POST"])
def api_qr_wifi():
    try:
        import qrcode; d=request.get_json(force=True)
        ssid=d.get("ssid","").strip(); pw=d.get("password","")
        enc=d.get("encryption","WPA")
        if not ssid: return jsonify({"error":"أدخل اسم الشبكة"}),400
        def esc(s): return re.sub(r'([\\;,:"])', r'\\\1', s)
        if enc=="nopass":
            payload=f"WIFI:T:nopass;S:{esc(ssid)};;"
        else:
            payload=f"WIFI:T:WPA;S:{esc(ssid)};P:{esc(pw)};H:false;;"
        qr=qrcode.QRCode(box_size=12,border=2); qr.add_data(payload); qr.make(fit=True)
        img=qr.make_image(fill_color="black",back_color="white")
        safe=re.sub(r'[^\w]+','_',ssid)[:30]
        p=opath(f"WiFi_{safe}.png"); img.save(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except ImportError: return jsonify({"error":"qrcode غير مثبّت"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 42. QR بطاقة أعمال vCard ───────────────────────────────────────────────

@bp.route("/api/qr-vcard", methods=["POST"])
def api_qr_vcard():
    try:
        import qrcode; d=request.get_json(force=True)
        name=d.get("name","").strip(); phone=d.get("phone","")
        org=d.get("org",""); email=d.get("email",""); url=d.get("url","")
        if not name: return jsonify({"error":"أدخل الاسم"}),400
        vcard=f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nORG:{org}\nEMAIL:{email}\nURL:{url}\nEND:VCARD"
        qr=qrcode.QRCode(box_size=11,border=2); qr.add_data(vcard); qr.make(fit=True)
        img=qr.make_image(fill_color="black",back_color="white")
        safe=re.sub(r'[^\w]+','_',name)[:30]
        p=opath(f"vCard_{safe}.png"); img.save(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p)})
    except ImportError: return jsonify({"error":"qrcode غير مثبّت"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 43. فاتورة PDF ─────────────────────────────────────────────────────────

@bp.route("/api/invoice", methods=["POST"])
def api_invoice():
    try:
        from fpdf import FPDF; d=request.get_json(force=True)
        client=d.get("client","عميل"); items=d.get("items",[])
        vat_rate=float(d.get("vat",15)); inv_no=d.get("number","001")
        if not items: return jsonify({"error":"أضف بنود الفاتورة"}),400
        def rv(t): 
            import unicodedata
            try: return t.encode('latin-1') and t
            except: return ''.join(c for c in t if ord(c)<256)
        pdf=FPDF(); pdf.add_page(); pdf.set_font("Helvetica","B",20)
        pdf.cell(0,15,f"INVOICE #{inv_no}",ln=True,align="C")
        pdf.set_font("Helvetica","",11); pdf.cell(0,8,f"Client: {rv(client)}",ln=True)
        from datetime import datetime
        pdf.cell(0,8,f"Date: {datetime.now().strftime('%Y-%m-%d')}",ln=True); pdf.ln(5)
        pdf.set_font("Helvetica","B",11); pdf.set_fill_color(0,180,128)
        pdf.cell(110,9,"Item",border=1,fill=True); pdf.cell(30,9,"Qty",border=1,fill=True,align="C")
        pdf.cell(45,9,"Price",border=1,fill=True,align="C",ln=True)
        pdf.set_font("Helvetica","",10); subtotal=0
        for it in items:
            name=rv(str(it.get("name","")))[:40]; qty=float(it.get("qty",1)); price=float(it.get("price",0))
            line=qty*price; subtotal+=line
            pdf.cell(110,8,name,border=1); pdf.cell(30,8,str(int(qty)),border=1,align="C")
            pdf.cell(45,8,f"{line:.2f}",border=1,align="C",ln=True)
        vat=subtotal*vat_rate/100; total=subtotal+vat
        pdf.ln(3); pdf.set_font("Helvetica","",11)
        pdf.cell(140,8,"Subtotal",align="R"); pdf.cell(45,8,f"{subtotal:.2f} SAR",align="C",ln=True)
        pdf.cell(140,8,f"VAT {vat_rate:.0f}%",align="R"); pdf.cell(45,8,f"{vat:.2f} SAR",align="C",ln=True)
        pdf.set_font("Helvetica","B",13)
        pdf.cell(140,10,"TOTAL",align="R"); pdf.cell(45,10,f"{total:.2f} SAR",align="C",ln=True)
        p=opath(f"فاتورة_{inv_no}.pdf"); pdf.output(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"total":round(total,2)})
    except ImportError: return jsonify({"error":"fpdf2 غير مثبّت — شغّل: pip install fpdf2"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 44. حاسبة كميات بناء ───────────────────────────────────────────────────

@bp.route("/api/construction", methods=["POST"])
def api_construction():
    try:
        d=request.get_json(force=True)
        length=float(d.get("length",0)); width=float(d.get("width",0)); height=float(d.get("height",0))
        if length<=0 or width<=0: return jsonify({"error":"أدخل الأبعاد"}),400
        # خرسانة (متر مكعب)
        volume=length*width*height if height>0 else length*width*0.15
        cement_bags=round(volume*7)  # ~7 شيكارة/م³
        sand=round(volume*0.5,2)     # م³
        gravel=round(volume*0.8,2)   # م³
        # طوب (للجدران لو height>0)
        bricks=round(length*height*50) if height>0 else 0  # ~50 طوبة/م²
        return jsonify({"ok":True,"volume":round(volume,2),"cement_bags":cement_bags,
                        "sand":sand,"gravel":gravel,"bricks":bricks})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 45. حاسبة قروض + جدول PDF ──────────────────────────────────────────────

@bp.route("/api/loan", methods=["POST"])
def api_loan():
    try:
        from fpdf import FPDF; d=request.get_json(force=True)
        principal=float(d.get("amount",0)); annual=float(d.get("rate",0)); years=float(d.get("years",0))
        if principal<=0 or years<=0: return jsonify({"error":"أدخل المبلغ والمدة"}),400
        months=int(years*12); mr=annual/100/12
        if mr>0: payment=principal*mr*(1+mr)**months/((1+mr)**months-1)
        else: payment=principal/months
        total=payment*months; interest=total-principal
        pdf=FPDF(); pdf.add_page(); pdf.set_font("Helvetica","B",18)
        pdf.cell(0,12,"Loan Schedule",ln=True,align="C"); pdf.set_font("Helvetica","",10)
        pdf.cell(0,7,f"Amount: {principal:.0f} | Rate: {annual}% | Years: {years}",ln=True)
        pdf.cell(0,7,f"Monthly Payment: {payment:.2f}",ln=True); pdf.ln(3)
        pdf.set_font("Helvetica","B",9); pdf.set_fill_color(0,180,128)
        for hdr,wd in [("Month",20),("Payment",35),("Principal",35),("Interest",35),("Balance",40)]:
            pdf.cell(wd,8,hdr,border=1,fill=True,align="C")
        pdf.ln(); pdf.set_font("Helvetica","",8); bal=principal
        for m in range(1,months+1):
            ip=bal*mr; pp=payment-ip; bal-=pp
            if bal<0: bal=0
            pdf.cell(20,6,str(m),border=1,align="C"); pdf.cell(35,6,f"{payment:.2f}",border=1,align="C")
            pdf.cell(35,6,f"{pp:.2f}",border=1,align="C"); pdf.cell(35,6,f"{ip:.2f}",border=1,align="C")
            pdf.cell(40,6,f"{bal:.2f}",border=1,align="C"); pdf.ln()
            if m>=120: break
        p=opath("جدول_قرض.pdf"); pdf.output(p); scan_media(p)
        return jsonify({"ok":True,"file":os.path.basename(p),"monthly":round(payment,2),
                        "total":round(total,2),"interest":round(interest,2)})
    except ImportError: return jsonify({"error":"fpdf2 غير مثبّت — شغّل: pip install fpdf2"}),500
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 46. حاسبة زكاة ─────────────────────────────────────────────────────────

@bp.route("/api/zakat", methods=["POST"])
def api_zakat():
    try:
        d=request.get_json(force=True)
        cash=float(d.get("cash",0)); gold=float(d.get("gold",0))
        invest=float(d.get("invest",0)); debts=float(d.get("debts",0))
        total=cash+gold+invest-debts
        nisab=float(d.get("nisab",20000))  # تقريبي بالريال
        if total<nisab:
            return jsonify({"ok":True,"zakat":0,"total":round(total,2),
                            "hint":f"المال أقل من النصاب ({nisab:.0f} ريال) — لا زكاة"})
        zakat=total*0.025
        return jsonify({"ok":True,"zakat":round(zakat,2),"total":round(total,2),
                        "hint":"الزكاة 2.5% من صافي المال الحولي"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 47. مُجرّب Regex ───────────────────────────────────────────────────────

