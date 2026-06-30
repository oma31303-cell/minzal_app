# -*- coding: utf-8 -*-
"""مِنزال — القلب المشترك (helpers) يستخدمه كل الأدوات"""
import os, re, uuid, subprocess, threading

DOWNLOAD_DIR = "/storage/emulated/0/Download/YTApp"
TOOLS_DIR    = os.path.join(DOWNLOAD_DIR, "tools")
UPLOAD_DIR   = "/data/data/com.termux/files/home/minzal_app/uploads"
for d in [DOWNLOAD_DIR, TOOLS_DIR, UPLOAD_DIR]:
    os.makedirs(d, exist_ok=True)

# مخزن حالة المهام (للتحميل والفيديو)
JOBS = {}

def scan_media(path=None):
    """تحديث معرض أندرويد ليظهر الملف الجديد"""
    target = path or DOWNLOAD_DIR
    try:
        subprocess.run(["termux-media-scan","-r",target],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except:
        try:
            subprocess.run(["am","broadcast","-a",
                            "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                            "-d","file://"+target],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except: pass

def sname(n):
    """تنظيف اسم ملف من الرموز الممنوعة"""
    return re.sub(r'[\\/:*?"<>|]', "_", n)[:80]

def opath(n):
    """مسار ملف الإخراج في مجلد tools"""
    return os.path.join(TOOLS_DIR, n)

def save_up(f):
    """حفظ ملف مرفوع مؤقتًا"""
    p = os.path.join(UPLOAD_DIR, str(uuid.uuid4())+"_"+sname(f.filename or "file"))
    f.save(p)
    return p

def pil():
    """استيراد PIL عند الحاجة فقط"""
    from PIL import Image
    return Image

def ffmpeg_job(cmd, job_id):
    """تشغيل أمر ffmpeg في خيط منفصل مع تتبع الحالة"""
    JOBS[job_id]["status"] = "processing"
    try:
        r = subprocess.run(["ffmpeg"]+cmd, capture_output=True, text=True, timeout=600)
        if r.returncode == 0:
            JOBS[job_id]["status"] = "done"; JOBS[job_id]["percent"] = 100; scan_media()
        else:
            JOBS[job_id]["status"] = "error"; JOBS[job_id]["error"] = (r.stderr or "خطأ")[-400:]
    except subprocess.TimeoutExpired:
        JOBS[job_id]["status"] = "error"; JOBS[job_id]["error"] = "انتهت المهلة"
    except FileNotFoundError:
        JOBS[job_id]["status"] = "error"; JOBS[job_id]["error"] = "ffmpeg غير مثبّت — شغّل: pkg install ffmpeg"
    except Exception as e:
        JOBS[job_id]["status"] = "error"; JOBS[job_id]["error"] = str(e)

def start_job(out_file):
    """إنشاء مهمة جديدة وإرجاع معرّفها"""
    jid = str(uuid.uuid4())
    JOBS[jid] = {"status":"queued","percent":0,"file":os.path.basename(out_file)}
    return jid
