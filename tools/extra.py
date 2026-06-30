# -*- coding: utf-8 -*-
"""مِنزال — أدوات إضافية (دفعة 1): حسابات ومنطق"""
import os, re, json, secrets, string, hashlib
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from core import opath, scan_media

bp = Blueprint("extra", __name__)

# ─── 1. حاسبة عمر دقيقة ──────────────────────────────────────────────────────
@bp.route("/api/age-calc", methods=["POST"])
def api_age_calc():
    try:
        d=request.get_json(force=True)
        y=int(d.get("year",0)); m=int(d.get("month",1)); day=int(d.get("day",1))
        if not (1900<=y<=2100 and 1<=m<=12 and 1<=day<=31):
            return jsonify({"error":"تاريخ غير صالح"}),400
        birth=date(y,m,day); today=date.today()
        if birth>today: return jsonify({"error":"التاريخ في المستقبل"}),400
        days=(today-birth).days
        years=today.year-birth.year-((today.month,today.day)<(birth.month,birth.day))
        months=(today.year-birth.year)*12+today.month-birth.month
        if today.day<birth.day: months-=1
        # العمر القادم
        try: next_bd=birth.replace(year=today.year)
        except: next_bd=birth.replace(year=today.year,day=28)
        if next_bd<today:
            try: next_bd=birth.replace(year=today.year+1)
            except: next_bd=birth.replace(year=today.year+1,day=28)
        days_to_bd=(next_bd-today).days
        return jsonify({"ok":True,"years":years,"total_days":days,"total_months":months,
                        "total_weeks":days//7,"total_hours":days*24,
                        "days_to_birthday":days_to_bd})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 2. مقسّم فاتورة بين أشخاص ───────────────────────────────────────────────
@bp.route("/api/bill-split", methods=["POST"])
def api_bill_split():
    try:
        d=request.get_json(force=True)
        total=float(d.get("total",0)); people=int(d.get("people",1))
        tip=float(d.get("tip",0)); vat=float(d.get("vat",0))
        if total<=0 or people<=0: return jsonify({"error":"أدخل المبلغ وعدد الأشخاص"}),400
        vat_amount=total*vat/100
        tip_amount=total*tip/100
        grand=total+vat_amount+tip_amount
        per_person=grand/people
        return jsonify({"ok":True,"subtotal":round(total,2),"vat_amount":round(vat_amount,2),
                        "tip_amount":round(tip_amount,2),"grand_total":round(grand,2),
                        "per_person":round(per_person,2),"people":people})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 3. مولّد كلمة سر متقدّم ─────────────────────────────────────────────────
@bp.route("/api/password-gen", methods=["POST"])
def api_password_gen():
    try:
        d=request.get_json(force=True)
        length=int(d.get("length",16))
        if length<4 or length>128: return jsonify({"error":"الطول بين 4 و128"}),400
        use_upper=d.get("upper",True); use_lower=d.get("lower",True)
        use_digits=d.get("digits",True); use_symbols=d.get("symbols",True)
        pool=""
        if use_lower: pool+=string.ascii_lowercase
        if use_upper: pool+=string.ascii_uppercase
        if use_digits: pool+=string.digits
        if use_symbols: pool+="!@#$%^&*()-_=+[]{}"
        if not pool: return jsonify({"error":"اختر نوع واحد على الأقل"}),400
        pw="".join(secrets.choice(pool) for _ in range(length))
        # تقييم القوة
        score=0
        if any(c.islower() for c in pw): score+=1
        if any(c.isupper() for c in pw): score+=1
        if any(c.isdigit() for c in pw): score+=1
        if any(c in "!@#$%^&*()-_=+[]{}" for c in pw): score+=1
        if length>=16: score+=1
        strength=["ضعيفة","مقبولة","متوسطة","قوية","قوية جدًا"][min(score,4)]
        return jsonify({"ok":True,"password":pw,"strength":strength})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 4. عدّاد تنازلي لمناسبة ─────────────────────────────────────────────────
@bp.route("/api/countdown", methods=["POST"])
def api_countdown():
    try:
        d=request.get_json(force=True)
        y=int(d.get("year",0)); m=int(d.get("month",1)); day=int(d.get("day",1))
        target=date(y,m,day); today=date.today()
        diff=(target-today).days
        if diff<0: return jsonify({"ok":True,"passed":True,"days":abs(diff),
                                    "msg":f"مرّت {abs(diff)} يوم على هذه المناسبة"})
        return jsonify({"ok":True,"passed":False,"days":diff,"weeks":diff//7,
                        "months":round(diff/30.44,1),"msg":f"باقي {diff} يوم"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 5. محوّل أرقام لكلمات عربية (للشيكات) ───────────────────────────────────
@bp.route("/api/num-to-words", methods=["POST"])
def api_num_to_words():
    try:
        d=request.get_json(force=True)
        num=int(float(d.get("number",0)))
        if num<0 or num>999999999: return jsonify({"error":"الرقم بين 0 و999 مليون"}),400
        ones=["","واحد","اثنان","ثلاثة","أربعة","خمسة","ستة","سبعة","ثمانية","تسعة",
              "عشرة","أحد عشر","اثنا عشر","ثلاثة عشر","أربعة عشر","خمسة عشر",
              "ستة عشر","سبعة عشر","ثمانية عشر","تسعة عشر"]
        tens=["","","عشرون","ثلاثون","أربعون","خمسون","ستون","سبعون","ثمانون","تسعون"]
        hundreds=["","مئة","مئتان","ثلاثمئة","أربعمئة","خمسمئة","ستمئة","سبعمئة","ثمانمئة","تسعمئة"]
        def three(n):
            r=""
            if n>=100: r+=hundreds[n//100]; n%=100
            if n>=20: 
                if r: r+=" و"
                r+=tens[n//10]
                if n%10: r+=" و"+ones[n%10]
            elif n>0:
                if r: r+=" و"
                r+=ones[n]
            return r
        if num==0: return jsonify({"ok":True,"words":"صفر"})
        parts=[]
        millions=num//1000000; thousands=(num%1000000)//1000; rest=num%1000
        if millions: parts.append(("مليون" if millions==1 else three(millions)+" مليون"))
        if thousands: parts.append(("ألف" if thousands==1 else ("ألفان" if thousands==2 else three(thousands)+" ألف")))
        if rest: parts.append(three(rest))
        return jsonify({"ok":True,"words":" و".join(parts)+" ريال"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 6. حاسبة نسبة مئوية شاملة ───────────────────────────────────────────────
@bp.route("/api/percent-calc", methods=["POST"])
def api_percent_calc():
    try:
        d=request.get_json(force=True)
        mode=d.get("mode","of")
        a=float(d.get("a",0)); b=float(d.get("b",0))
        if mode=="of":  # كم نسبة a% من b
            result=a*b/100; label=f"{a}% من {b}"
        elif mode=="is":  # a هو كم % من b
            if b==0: return jsonify({"error":"القسمة على صفر"}),400
            result=a/b*100; label=f"{a} من {b} كنسبة"
        elif mode=="change":  # نسبة التغير من a لـ b
            if a==0: return jsonify({"error":"القيمة الأولى صفر"}),400
            result=(b-a)/a*100; label="نسبة التغيّر"
        else: return jsonify({"error":"وضع غير معروف"}),400
        return jsonify({"ok":True,"result":round(result,2),"label":label})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 7. محوّل وحدات شامل ─────────────────────────────────────────────────────
@bp.route("/api/unit-convert", methods=["POST"])
def api_unit_convert():
    try:
        d=request.get_json(force=True)
        cat=d.get("category","length"); val=float(d.get("value",0))
        frm=d.get("from",""); to=d.get("to","")
        units={
            "length":{"m":1,"km":1000,"cm":0.01,"mm":0.001,"mile":1609.34,"foot":0.3048,"inch":0.0254,"yard":0.9144},
            "weight":{"kg":1,"g":0.001,"ton":1000,"pound":0.453592,"ounce":0.0283495},
            "area":{"m2":1,"km2":1000000,"hectare":10000,"acre":4046.86,"foot2":0.092903},
            "temp":{},  # خاص
            "volume":{"liter":1,"ml":0.001,"m3":1000,"gallon":3.78541,"cup":0.236588},
        }
        if cat=="temp":
            if frm=="c": c=val
            elif frm=="f": c=(val-32)*5/9
            elif frm=="k": c=val-273.15
            else: return jsonify({"error":"وحدة حرارة غير معروفة"}),400
            if to=="c": r=c
            elif to=="f": r=c*9/5+32
            elif to=="k": r=c+273.15
            else: return jsonify({"error":"وحدة حرارة غير معروفة"}),400
            return jsonify({"ok":True,"result":round(r,2)})
        if cat not in units: return jsonify({"error":"تصنيف غير معروف"}),400
        u=units[cat]
        if frm not in u or to not in u: return jsonify({"error":"وحدة غير معروفة"}),400
        result=val*u[frm]/u[to]
        return jsonify({"ok":True,"result":round(result,4)})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 8. حاسبة BMI ───────────────────────────────────────────────────────────
@bp.route("/api/bmi", methods=["POST"])
def api_bmi():
    try:
        d=request.get_json(force=True)
        weight=float(d.get("weight",0)); height=float(d.get("height",0))
        if weight<=0 or height<=0: return jsonify({"error":"أدخل الوزن والطول"}),400
        h_m=height/100 if height>3 else height
        bmi=weight/(h_m*h_m)
        if bmi<18.5: cat="نحافة"
        elif bmi<25: cat="وزن طبيعي"
        elif bmi<30: cat="زيادة وزن"
        else: cat="سمنة"
        # الوزن المثالي
        ideal_min=18.5*h_m*h_m; ideal_max=24.9*h_m*h_m
        return jsonify({"ok":True,"bmi":round(bmi,1),"category":cat,
                        "ideal_min":round(ideal_min,1),"ideal_max":round(ideal_max,1)})
    except Exception as e: return jsonify({"error":str(e)}),500
