# -*- coding: utf-8 -*-
"""مِنزال — حاسبات متقدمة (دفعة 3ب)"""
from datetime import date, timedelta
from flask import Blueprint, request, jsonify

bp = Blueprint("calc", __name__)

# ─── 1. حاسبة زكاة الذهب ────────────────────────────────────────────────────
@bp.route("/api/zakat-gold", methods=["POST"])
def api_zakat_gold():
    try:
        d=request.get_json(force=True)
        grams=float(d.get("grams",0)); karat=int(d.get("karat",24))
        gram_price=float(d.get("price",0))  # سعر جرام 24
        if grams<=0 or gram_price<=0: return jsonify({"error":"أدخل الوزن وسعر الجرام"}),400
        # تعديل السعر حسب العيار
        adj_price=gram_price*(karat/24)
        value=grams*adj_price
        # نصاب الذهب 85 جرام (عيار 24)
        nisab_grams=85
        pure_grams=grams*(karat/24)
        if pure_grams<nisab_grams:
            return jsonify({"ok":True,"zakat":0,"value":round(value,2),
                            "hint":f"الذهب أقل من النصاب ({nisab_grams} جرام عيار 24) — لا زكاة"})
        zakat=value*0.025
        return jsonify({"ok":True,"zakat":round(zakat,2),"value":round(value,2),
                        "pure_grams":round(pure_grams,1),
                        "hint":"الزكاة 2.5% من قيمة الذهب الحولي"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 2. فرق بين تاريخين ─────────────────────────────────────────────────────
@bp.route("/api/date-diff", methods=["POST"])
def api_date_diff():
    try:
        d=request.get_json(force=True)
        d1=date(int(d.get("y1")),int(d.get("m1")),int(d.get("day1")))
        d2=date(int(d.get("y2")),int(d.get("m2")),int(d.get("day2")))
        if d2<d1: d1,d2=d2,d1
        diff=(d2-d1).days
        years=d2.year-d1.year-((d2.month,d2.day)<(d1.month,d1.day))
        months=(d2.year-d1.year)*12+d2.month-d1.month-(1 if d2.day<d1.day else 0)
        # أيام العمل (تقريبي بدون عطل رسمية)
        workdays=sum(1 for i in range(diff) if (d1+timedelta(days=i)).weekday()<5)
        return jsonify({"ok":True,"days":diff,"weeks":diff//7,"months":months,
                        "years":years,"workdays":workdays})
    except Exception as e: return jsonify({"error":"تأكد من صحة التواريخ"}),400

# ─── 3. إضافة/طرح أيام من تاريخ ─────────────────────────────────────────────
@bp.route("/api/date-add", methods=["POST"])
def api_date_add():
    try:
        d=request.get_json(force=True)
        base=date(int(d.get("year")),int(d.get("month")),int(d.get("day")))
        days=int(d.get("add_days",0))
        result=base+timedelta(days=days)
        weekdays=["الإثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
        return jsonify({"ok":True,"date":result.strftime("%Y-%m-%d"),
                        "weekday":weekdays[result.weekday()]})
    except Exception as e: return jsonify({"error":"تأكد من التاريخ"}),400

# ─── 4. حاسبة نهاية الخدمة (سعودي) ──────────────────────────────────────────
@bp.route("/api/eos-gratuity", methods=["POST"])
def api_eos_gratuity():
    try:
        d=request.get_json(force=True)
        salary=float(d.get("salary",0))      # آخر راتب
        years=float(d.get("years",0))         # سنوات الخدمة
        reason=d.get("reason","end")          # end=انتهاء عقد، resign=استقالة
        if salary<=0 or years<=0: return jsonify({"error":"أدخل الراتب وسنوات الخدمة"}),400
        # القانون السعودي: نصف راتب لأول 5 سنوات، راتب كامل لما بعدها
        first5=min(years,5)
        after5=max(0,years-5)
        full=(first5*0.5+after5*1.0)*salary
        # الاستقالة: تخفيض حسب المدة
        if reason=="resign":
            if years<2: gratuity=0
            elif years<5: gratuity=full*(1/3)
            elif years<10: gratuity=full*(2/3)
            else: gratuity=full
        else:
            gratuity=full
        return jsonify({"ok":True,"gratuity":round(gratuity,2),"full":round(full,2),
                        "hint":"تقديري حسب نظام العمل السعودي — استشر مختص للدقة"})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── 5. حاسبة الوقت المتبقي للتقاعد ─────────────────────────────────────────
@bp.route("/api/retirement", methods=["POST"])
def api_retirement():
    try:
        d=request.get_json(force=True)
        cur_age=float(d.get("age",0)); retire_age=float(d.get("retire_age",60))
        if cur_age<=0: return jsonify({"error":"أدخل عمرك"}),400
        if cur_age>=retire_age: return jsonify({"ok":True,"reached":True,"hint":"وصلت سن التقاعد"})
        years_left=retire_age-cur_age
        months_left=years_left*12
        days_left=int(years_left*365.25)
        return jsonify({"ok":True,"years":round(years_left,1),"months":round(months_left),
                        "days":days_left})
    except Exception as e: return jsonify({"error":str(e)}),500
