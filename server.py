#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
مِنزال — السيرفر الرئيسي
معمارية احترافية: كل تصنيف أدوات في ملف منفصل داخل tools/
لو خربت أداة في ملف، باقي الملفات تشتغل عادي.
"""
import os, re, uuid, threading, subprocess
from flask import Flask, request, jsonify, send_from_directory, Response
from core import (scan_media, JOBS, DOWNLOAD_DIR, TOOLS_DIR)

app = Flask(__name__, static_folder="static", static_url_path="")

# ─── تسجيل كل وحدات الأدوات (Blueprints) ────────────────────────────────────
# كل وحدة محاطة بـ try مستقل: لو فشل استيراد وحدة، الباقي يكمل
LOADED = []
FAILED = []
for mod_name in ["images","video","pdf","security","business","dev","utility","extra","productivity","calc","files"]:
    try:
        mod = __import__(f"tools.{mod_name}", fromlist=["bp"])
        app.register_blueprint(mod.bp)
        LOADED.append(mod_name)
    except Exception as e:
        FAILED.append((mod_name, str(e)))
        print(f"⚠️  فشل تحميل وحدة {mod_name}: {e}")

# ─── الملفات الثابتة ────────────────────────────────────────────────────────
@app.route("/")
def index(): return send_from_directory("static","index.html")
@app.route("/manifest.json")
def manifest(): return send_from_directory("static","manifest.json",mimetype="application/manifest+json")
@app.route("/sw.js")
def sw(): return send_from_directory("static","sw.js",mimetype="application/javascript")
@app.route("/icon.png")
def icon(): return send_from_directory("static","icon.png")
@app.route("/tools/<path:fn>")
def tools_file(fn): return send_from_directory(TOOLS_DIR,fn)

@app.route("/share-target", methods=["GET","POST"])
def share_target():
    su = request.form.get("url") or request.form.get("text") or request.args.get("url") or request.args.get("text") or ""
    m = re.search(r"https?://\S+", su); url = m.group(0) if m else su
    html = open(os.path.join("static","index.html"), encoding="utf-8").read().replace("__PREFILL_URL__", url)
    return Response(html, mimetype="text/html")

@app.route("/api/status/<jid>")
def api_status(jid):
    j = JOBS.get(jid)
    return (jsonify(j) if j else jsonify({"error":"غير موجود"}), 200 if j else 404)

# ─── أداة التحميل (تبقى هنا لأنها أساسية ومعقّدة) ────────────────────────────
def run_dl(jid, url, mode, quality):
    JOBS[jid]["status"] = "downloading"; JOBS[jid]["percent"] = 0
    out_tpl = os.path.join(DOWNLOAD_DIR,"%(title)s.%(ext)s")
    if mode == "image":
        cmd = ["gallery-dl","--dest",DOWNLOAD_DIR,"-o","directory=[]",url]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            cnt=0
            for line in proc.stdout:
                JOBS[jid]["log"]=line.strip(); cnt+=1; JOBS[jid]["percent"]=min(95,cnt*12)
            proc.wait()
            JOBS[jid]["status"]="done" if proc.returncode==0 else "error"
            if proc.returncode!=0: JOBS[jid]["error"]=JOBS[jid].get("log","فشل")
        except FileNotFoundError: JOBS[jid]["status"]="error"; JOBS[jid]["error"]="gallery-dl غير مثبّت"
        except Exception as e: JOBS[jid]["status"]="error"; JOBS[jid]["error"]=str(e)
        finally: JOBS[jid]["percent"]=100; scan_media()
        return
    cmd = ["yt-dlp","--no-mtime","-o",out_tpl,"--newline"]
    if mode == "audio":
        cmd += ["-x","--audio-format","mp3","--audio-quality","0"]
    else:
        qmap={"best":"bv*+ba/b","1080":"bv*[height<=1080]+ba/b[height<=1080]","720":"bv*[height<=720]+ba/b[height<=720]","480":"bv*[height<=480]+ba/b[height<=480]"}
        cmd += ["-f",qmap.get(quality,"bv*+ba/b"),"--merge-output-format","mp4"]
    cmd.append(url)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            JOBS[jid]["log"]=line.strip()
            m=re.search(r"(\d+(?:\.\d+)?)%",line)
            if m: JOBS[jid]["percent"]=float(m.group(1))
        proc.wait()
        if proc.returncode==0: JOBS[jid]["status"]="done"; JOBS[jid]["percent"]=100; scan_media()
        else: JOBS[jid]["status"]="error"; JOBS[jid]["error"]=JOBS[jid].get("log","فشل")
    except Exception as e: JOBS[jid]["status"]="error"; JOBS[jid]["error"]=str(e)

@app.route("/api/download", methods=["POST"])
def api_download():
    d=request.get_json(force=True); url=d.get("url","").strip()
    if not url: return jsonify({"error":"ما فيه رابط"}),400
    jid=str(uuid.uuid4()); JOBS[jid]={"status":"queued","percent":0,"log":""}
    threading.Thread(target=run_dl,args=(jid,url,d.get("mode","video"),d.get("quality","best")),daemon=True).start()
    return jsonify({"job_id":jid})

# ─── روابط المواقع الخارجية ─────────────────────────────────────────────────
@app.route("/api/link-removebg")
def api_link_removebg(): return jsonify({"url":"https://remove-bg.io"})
@app.route("/api/link-vocal")
def api_link_vocal(): return jsonify({"url":"https://vocalremover.org"})

# ─── فحص صحة النظام ─────────────────────────────────────────────────────────
@app.route("/api/health")
def api_health():
    return jsonify({"loaded":LOADED,"failed":[f[0] for f in FAILED],
                    "total_modules":len(LOADED)})

if __name__ == "__main__":
    print(f"✅ مِنزال — تم تحميل {len(LOADED)} وحدة: {', '.join(LOADED)}")
    if FAILED:
        print(f"⚠️  فشلت {len(FAILED)} وحدة: {', '.join(f[0] for f in FAILED)}")
    print("السيرفر شغال على http://localhost:8080")
    app.run(host="0.0.0.0", port=8080)
