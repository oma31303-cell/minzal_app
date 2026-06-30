# -*- coding: utf-8 -*-
"""مِنزال — أدوات الإنتاجية (دفعة 3): ملاحظات ومهام محفوظة على القرص"""
import os, json, uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from core import UPLOAD_DIR

bp = Blueprint("productivity", __name__)

# نحفظ البيانات في مجلد ثابت (مو uploads المؤقت)
DATA_DIR = "/data/data/com.termux/files/home/minzal_app/data"
os.makedirs(DATA_DIR, exist_ok=True)
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")

def _load(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except: return []

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── الملاحظات ──────────────────────────────────────────────────────────────
@bp.route("/api/notes-list")
def notes_list():
    return jsonify({"ok":True,"notes":_load(NOTES_FILE)})

@bp.route("/api/notes-add", methods=["POST"])
def notes_add():
    try:
        d=request.get_json(force=True); text=d.get("text","").strip()
        if not text: return jsonify({"error":"اكتب الملاحظة"}),400
        notes=_load(NOTES_FILE)
        notes.insert(0,{"id":str(uuid.uuid4())[:8],"text":text,
                        "date":datetime.now().strftime("%Y-%m-%d %H:%M")})
        _save(NOTES_FILE,notes)
        return jsonify({"ok":True,"notes":notes})
    except Exception as e: return jsonify({"error":str(e)}),500

@bp.route("/api/notes-delete", methods=["POST"])
def notes_delete():
    try:
        d=request.get_json(force=True); nid=d.get("id","")
        notes=[n for n in _load(NOTES_FILE) if n["id"]!=nid]
        _save(NOTES_FILE,notes)
        return jsonify({"ok":True,"notes":notes})
    except Exception as e: return jsonify({"error":str(e)}),500

# ─── المهام ─────────────────────────────────────────────────────────────────
@bp.route("/api/tasks-list")
def tasks_list():
    return jsonify({"ok":True,"tasks":_load(TASKS_FILE)})

@bp.route("/api/tasks-add", methods=["POST"])
def tasks_add():
    try:
        d=request.get_json(force=True); text=d.get("text","").strip()
        if not text: return jsonify({"error":"اكتب المهمة"}),400
        tasks=_load(TASKS_FILE)
        tasks.append({"id":str(uuid.uuid4())[:8],"text":text,"done":False})
        _save(TASKS_FILE,tasks)
        return jsonify({"ok":True,"tasks":tasks})
    except Exception as e: return jsonify({"error":str(e)}),500

@bp.route("/api/tasks-toggle", methods=["POST"])
def tasks_toggle():
    try:
        d=request.get_json(force=True); tid=d.get("id","")
        tasks=_load(TASKS_FILE)
        for t in tasks:
            if t["id"]==tid: t["done"]=not t["done"]
        _save(TASKS_FILE,tasks)
        return jsonify({"ok":True,"tasks":tasks})
    except Exception as e: return jsonify({"error":str(e)}),500

@bp.route("/api/tasks-delete", methods=["POST"])
def tasks_delete():
    try:
        d=request.get_json(force=True); tid=d.get("id","")
        tasks=[t for t in _load(TASKS_FILE) if t["id"]!=tid]
        _save(TASKS_FILE,tasks)
        return jsonify({"ok":True,"tasks":tasks})
    except Exception as e: return jsonify({"error":str(e)}),500

@bp.route("/api/tasks-clear", methods=["POST"])
def tasks_clear():
    try:
        tasks=[t for t in _load(TASKS_FILE) if not t["done"]]
        _save(TASKS_FILE,tasks)
        return jsonify({"ok":True,"tasks":tasks})
    except Exception as e: return jsonify({"error":str(e)}),500
