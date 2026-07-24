# -*- coding: utf-8 -*-
import os
import sys
import json
import requests
import socket
import time
import threading
import subprocess
import shutil
import base64
import logging
import random
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
import tkinter as tk
from tkinter import messagebox

# ============================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================

os.makedirs("logs", exist_ok=True)

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        level_colors = {
            logging.DEBUG: Colors.CYAN,
            logging.INFO: Colors.GREEN,
            logging.WARNING: Colors.YELLOW,
            logging.ERROR: Colors.RED,
            logging.CRITICAL: Colors.RED + Colors.BOLD,
        }
        color = level_colors.get(record.levelno, Colors.WHITE)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        return super().format(record)

logger = logging.getLogger('NeoBrain')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

file_handler = logging.FileHandler(
    os.path.join("logs", f"neobrain_{datetime.now().strftime('%Y%m%d')}.log"),
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
))
logger.addHandler(console_handler)

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

logger.info("🚀 NeoBrain запущен")
logger.info(f"📁 Логи сохраняются в: logs/neobrain_{datetime.now().strftime('%Y%m%d')}.log")

# ============================================================
# ПАПКИ
# ============================================================
CHARACTERS_DIR = "characters"
ROOMS_DIR = "rooms"
AVATARS_DIR = "avatars"
USER_AVATAR_DIR = os.path.join(AVATARS_DIR, "user")
MAX_ROOM_CHARACTERS = 10

os.makedirs(CHARACTERS_DIR, exist_ok=True)
os.makedirs(ROOMS_DIR, exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(USER_AVATAR_DIR, exist_ok=True)

# ============================================================
# КЛАСС ПЕРСОНАЖА
# ============================================================

class Character:
    def __init__(self, name, system_prompt="", style="", gender="male", avatar_path=None):
        self.name = name
        self.system_prompt = system_prompt
        self.style = style
        self.gender = gender
        self.avatar_path = avatar_path
        self.history = []
        self.created = datetime.now().isoformat()
        self.last_used = datetime.now().isoformat()
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})
        self.last_used = datetime.now().isoformat()
        self.save()
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "style": self.style,
            "gender": self.gender,
            "history": self.history,
            "created": self.created,
            "last_used": self.last_used
        }
    
    def save(self):
        filename = os.path.join(CHARACTERS_DIR, f"{self.id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load(character_id):
        filename = os.path.join(CHARACTERS_DIR, f"{character_id}.json")
        if not os.path.exists(filename):
            return None
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        char = Character(
            name=data["name"],
            system_prompt=data.get("system_prompt", ""),
            style=data.get("style", ""),
            gender=data.get("gender", "male")
        )
        char.id = data["id"]
        char.history = data.get("history", [])
        char.created = data.get("created", datetime.now().isoformat())
        char.last_used = data.get("last_used", datetime.now().isoformat())
        return char
    
    @staticmethod
    def load_all():
        characters = []
        for filename in os.listdir(CHARACTERS_DIR):
            if filename.endswith(".json"):
                char_id = filename.replace(".json", "")
                char = Character.load(char_id)
                if char:
                    characters.append(char)
        return characters

# ============================================================
# КЛАСС КОМНАТЫ
# ============================================================

class Room:
    def __init__(self, name, character_ids, mode="random", order=None, interrupt=False):
        self.name = name
        self.mode = mode
        self.order = order or []
        self.interrupt = interrupt
        self.turn_index = 0
        self.history = []
        self.characters = []
        self.created = datetime.now().isoformat()
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for char_id in character_ids:
            char = Character.load(char_id)
            if char:
                self.characters.append({
                    "id": char.id,
                    "name": char.name,
                    "personality": char.style or "нейтральный",
                    "description": char.system_prompt[:100] if char.system_prompt else ""
                })
        
        if len(self.characters) < 2:
            raise ValueError("Нужно минимум 2 персонажа")
        if len(self.characters) > MAX_ROOM_CHARACTERS:
            raise ValueError(f"Максимум {MAX_ROOM_CHARACTERS} персонажей")
        
        if self.mode == "strict" and not self.order:
            self.order = [c["id"] for c in self.characters]
        
        self.save()
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "characters": self.characters,
            "history": self.history,
            "mode": self.mode,
            "order": self.order,
            "interrupt": self.interrupt,
            "turn_index": self.turn_index,
            "created": self.created
        }
    
    def save(self):
        filename = os.path.join(ROOMS_DIR, f"{self.id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def add_message(self, role, content):
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.save()
    
    def get_next_character(self):
        if self.mode == "strict" and self.order:
            char_id = self.order[self.turn_index % len(self.order)]
            self.turn_index += 1
            self.save()
            for char in self.characters:
                if char["id"] == char_id:
                    return char
            return self.characters[0]
        elif self.mode == "random":
            return random.choice(self.characters)
        elif self.mode == "interrupt":
            if len(self.history) > 0 and self.history[-1].get("role") == "user":
                if random.random() < 0.3:
                    return random.choice(self.characters)
            return random.choice(self.characters)
        return random.choice(self.characters)
    
    @staticmethod
    def load(room_id):
        filename = os.path.join(ROOMS_DIR, f"{room_id}.json")
        if not os.path.exists(filename):
            return None
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        room = Room(
            name=data["name"],
            character_ids=[c["id"] for c in data["characters"]],
            mode=data.get("mode", "random"),
            order=data.get("order", []),
            interrupt=data.get("interrupt", False)
        )
        room.id = data["id"]
        room.history = data.get("history", [])
        room.turn_index = data.get("turn_index", 0)
        room.characters = data.get("characters", [])
        room.created = data.get("created", datetime.now().isoformat())
        return room
    
    @staticmethod
    def load_all():
        rooms = []
        for filename in os.listdir(ROOMS_DIR):
            if filename.endswith(".json"):
                room_id = filename.replace(".json", "")
                room = Room.load(room_id)
                if room:
                    rooms.append(room)
        return rooms
    
    def delete(self):
        filename = os.path.join(ROOMS_DIR, f"{self.id}.json")
        if os.path.exists(filename):
            os.remove(filename)
            return True
        return False

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()

# ============================================================
# API ДЛЯ ПЕРСОНАЖЕЙ
# ============================================================

@app.get("/characters")
async def get_characters():
    chars = Character.load_all()
    return {
        "characters": [
            {
                "id": c.id,
                "name": c.name,
                "gender": c.gender,
                "style": c.style,
                "created": c.created,
                "last_used": c.last_used,
                "history_count": len(c.history)
            }
            for c in chars
        ]
    }

@app.get("/character/{character_id}")
async def get_character(character_id: str):
    char = Character.load(character_id)
    if not char:
        return {"error": "Персонаж не найден"}
    return char.to_dict()

@app.post("/character/new")
async def create_character(request: Request):
    try:
        data = await request.json()
        name = data.get("name", "Новый персонаж")
        system_prompt = data.get("system_prompt", "")
        style = data.get("style", "")
        gender = data.get("gender", "male")
        
        char = Character(name=name, system_prompt=system_prompt, style=style, gender=gender)
        char.save()
        logger.info(f"✅ Создан персонаж: {name} (id: {char.id})")
        return {"id": char.id, "message": f"Персонаж '{name}' создан"}
    except Exception as e:
        logger.error(f"❌ Ошибка создания персонажа: {e}")
        return {"error": str(e)}

@app.delete("/character/{character_id}")
async def delete_character(character_id: str):
    char = Character.load(character_id)
    if not char:
        return {"error": "Персонаж не найден"}
    filename = os.path.join(CHARACTERS_DIR, f"{character_id}.json")
    if os.path.exists(filename):
        os.remove(filename)
        return {"message": "Персонаж удалён"}
    return {"error": "Персонаж не найден"}

# ============================================================
# API ДЛЯ КОМНАТ
# ============================================================

@app.get("/rooms")
async def get_rooms():
    rooms = Room.load_all()
    return {
        "rooms": [
            {
                "id": r.id,
                "name": r.name,
                "characters": r.characters,
                "history_count": len(r.history),
                "mode": r.mode,
                "created": r.created
            }
            for r in rooms
        ]
    }

@app.get("/room/{room_id}")
async def get_room(room_id: str):
    room = Room.load(room_id)
    if not room:
        return {"error": "Комната не найдена"}
    return room.to_dict()

@app.post("/room/new")
async def create_room(request: Request):
    data = await request.json()
    name = data.get("name", "Новая комната")
    character_ids = data.get("character_ids", [])
    mode = data.get("mode", "random")
    order = data.get("order", [])
    interrupt = data.get("interrupt", False)
    
    if len(character_ids) < 2:
        return {"error": "Нужно минимум 2 персонажа"}
    if len(character_ids) > MAX_ROOM_CHARACTERS:
        return {"error": f"Максимум {MAX_ROOM_CHARACTERS} персонажей"}
    
    try:
        room = Room(name, character_ids, mode, order, interrupt)
        return {"id": room.id, "message": f"Комната '{name}' создана"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/room/{room_id}")
async def delete_room(room_id: str):
    room = Room.load(room_id)
    if not room:
        return {"error": "Комната не найдена"}
    room.delete()
    return {"message": "Комната удалена"}

@app.post("/room/{room_id}/message")
async def add_room_message(room_id: str, request: Request):
    data = await request.json()
    text = data.get("text", "")
    role = data.get("role", "user")
    
    room = Room.load(room_id)
    if not room:
        return {"error": "Комната не найдена"}
    
    room.add_message(role, text)
    return {"message": "Сообщение добавлено"}

@app.get("/room/{room_id}/next")
async def get_next_character(room_id: str):
    room = Room.load(room_id)
    if not room:
        return {"error": "Комната не найдена"}
    
    char = room.get_next_character()
    if not char:
        return {"error": "Нет персонажей"}
    
    return {"character": char}

# ============================================================
# ОСТАЛЬНЫЕ API (Ollama и т.д.)
# ============================================================

def get_local_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

def is_ollama_running():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False

def start_ollama():
    logger.info("🔄 Запуск Ollama...")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        logger.info("✅ Ollama запущена")
        return True
    except:
        logger.error("❌ Ollama не найдена")
        return False

def ask_ollama(prompt, model="qwen2.5-coder:1.5b", system_prompt="", temperature=0.7):
    try:
        check = requests.get("http://localhost:11434/api/tags", timeout=3)
        if check.status_code != 200:
            return {"error": "Ollama не отвечает"}
    except:
        return {"error": "Ollama не запущена"}

    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "temperature": temperature
        },
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        return {"response": result.get("response", "Нет ответа")}
    else:
        return {"error": f"Ошибка Ollama: {response.status_code}"}

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    model = data.get("model", "qwen2.5-coder:1.5b")
    character_id = data.get("character_id", None)
    temperature = data.get("temperature", 0.7)
    
    system_prompt = ""
    char = None
    if character_id:
        char = Character.load(character_id)
        if char:
            system_prompt = char.system_prompt or ""
    
    result = ask_ollama(prompt, model, system_prompt, temperature)
    
    if char and "response" in result and not result.get("error"):
        char.add_message("user", prompt)
        char.add_message("assistant", result["response"])
    
    return result

# ============================================================
# HTML ТЕМПЛЕЙТ (С КОМНАТАМИ И 24 ТЕМАМИ, БЕЗ "В ТРЕНДЕ")
# ============================================================

html_template = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🧠 NeoBrain</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; padding: 20px; min-height: 100vh; background: #0a0e1a; color: #e8f0ff; }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid rgba(0,212,255,0.15); padding-bottom: 15px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .header h1 { font-size: 26px; background: linear-gradient(135deg, #00d4ff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
        
        .btn { padding: 8px 16px; border: none; border-radius: 10px; cursor: pointer; background: rgba(255,255,255,0.06); color: #d4e8ff; transition: 0.3s; font-size: 13px; }
        .btn:hover { transform: translateY(-2px); filter: brightness(1.15); }
        .btn-primary { background: #00d4ff; color: #0a0e1a; }
        .btn-success { background: #51cf66; color: #0a0e1a; }
        .btn-danger { background: #ff6b6b; color: #0a0e1a; }
        .btn-purple { background: #a855f7; color: #0a0e1a; }
        .btn-sm { padding: 4px 10px; font-size: 11px; }
        
        .tabs { display: flex; gap: 4px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 10px 24px; border-radius: 12px; cursor: pointer; background: rgba(255,255,255,0.04); color: #8899bb; transition: 0.3s; border: 1px solid transparent; }
        .tab:hover { background: rgba(255,255,255,0.08); }
        .tab.active { background: rgba(0,212,255,0.12); color: #00d4ff; border-color: rgba(0,212,255,0.2); }
        
        .content { display: grid; grid-template-columns: 320px 1fr; gap: 20px; }
        @media (max-width: 768px) { .content { grid-template-columns: 1fr; } }
        
        .sidebar { background: rgba(255,255,255,0.02); border-radius: 16px; padding: 16px; border: 1px solid rgba(255,255,255,0.06); max-height: 600px; overflow-y: auto; }
        .sidebar-title { font-size: 14px; font-weight: bold; color: #8899bb; margin-bottom: 12px; letter-spacing: 1px; }
        .chat-item { padding: 10px 14px; border-radius: 10px; cursor: pointer; transition: 0.3s; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
        .chat-item:hover { background: rgba(255,255,255,0.06); }
        .chat-item.active { background: rgba(0,212,255,0.1); border-left: 3px solid #00d4ff; }
        .chat-item .name { font-size: 13px; color: #d4e8ff; }
        .chat-item .badge { font-size: 11px; color: #8899bb; }
        .chat-item .delete-btn { color: #ff6b6b; background: none; border: none; cursor: pointer; font-size: 14px; padding: 0 4px; }
        
        .chat-area { background: rgba(255,255,255,0.02); border-radius: 16px; border: 1px solid rgba(255,255,255,0.06); display: flex; flex-direction: column; min-height: 500px; }
        .chat-header { padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
        .chat-header .title { font-size: 18px; font-weight: bold; color: #d4e8ff; }
        .chat-header .subtitle { font-size: 12px; color: #8899bb; }
        .chat-messages { flex: 1; padding: 16px 20px; overflow-y: auto; max-height: 450px; }
        .message { margin-bottom: 12px; display: flex; align-items: flex-start; gap: 10px; }
        .message.user { flex-direction: row-reverse; }
        .message .avatar { width: 36px; height: 36px; border-radius: 50%; background: #2a2a4a; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.08); }
        .message .bubble { padding: 10px 16px; border-radius: 12px; max-width: 75%; word-break: break-word; font-size: 14px; line-height: 1.5; color: #d4e8ff; }
        .message.user .bubble { background: rgba(0,212,255,0.12); border: 1px solid rgba(0,212,255,0.1); }
        .message.assistant .bubble { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }
        .message .name-label { font-size: 11px; color: #8899bb; margin-bottom: 2px; }
        
        .chat-input { padding: 16px 20px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; gap: 10px; }
        .chat-input input { flex: 1; padding: 10px 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.04); color: #d4e8ff; font-size: 14px; outline: none; }
        .chat-input input:focus { border-color: rgba(0,212,255,0.3); }
        .chat-input input::placeholder { color: #556688; }
        
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.85); z-index: 9999; justify-content: center; align-items: center; }
        .modal-overlay.active { display: flex; }
        .modal { background: #111827; border: 1px solid rgba(0,212,255,0.15); border-radius: 20px; padding: 30px; max-width: 550px; width: 100%; max-height: 90vh; overflow-y: auto; }
        .modal h2 { color: #d4e8ff; margin-bottom: 16px; font-size: 20px; }
        .modal label { display: block; margin-bottom: 4px; font-size: 13px; color: #8899bb; }
        .modal input, .modal select { width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.04); color: #d4e8ff; margin-bottom: 12px; }
        .modal .checkbox-group { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px; max-height: 150px; overflow-y: auto; }
        .modal .checkbox-group label { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #d4e8ff; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: 0.2s; }
        .modal .checkbox-group label:hover { background: rgba(255,255,255,0.04); }
        .modal .modal-actions { display: flex; gap: 10px; margin-top: 16px; justify-content: flex-end; }
        
        .empty-state { text-align: center; padding: 40px; color: #8899bb; }
        .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
        
        #status { margin-top: 12px; font-size: 13px; color: #8899bb; text-align: center; }
        
        .room-schema { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 6px; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 8px; }
        .schema-block { padding: 2px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; background: #00d4ff22; color: #00d4ff; border: 1px solid #00d4ff33; }
        .schema-arrow { color: #556688; font-size: 12px; }
        .schema-mode { font-size: 11px; color: #8899bb; margin-left: 6px; }
        
        body.theme-neon { background: #0a0e1a; color: #d4e8ff; }
        body.theme-cyber { background: #0d0a1a; color: #ff66ff; }
        body.theme-matrix { background: #0a0f0a; color: #66ff66; }
        body.theme-ocean { background: #0a1a2a; color: #66ddff; }
        body.theme-sunset { background: #1a0a0a; color: #ffaa88; }
        body.theme-forest { background: #0a1a0a; color: #88ff88; }
        body.theme-cosmos { background: #05050f; color: #cc88ff; }
        body.theme-lava { background: #1a0a05; color: #ff8866; }
        body.theme-gold { background: #1a1a0a; color: #ffdd88; }
        body.theme-purple { background: #0a0a1a; color: #dd88ff; }
        body.theme-cherry { background: #1a0a12; color: #ff88bb; }
        body.theme-emerald { background: #0a1a0a; color: #66ffaa; }
        body.theme-sunny { background: #f5ede1; color: #3a2a1a; }
        body.theme-ice { background: #0a1a2a; color: #88ddff; }
        body.theme-wine { background: #1a0508; color: #ff6677; }
        body.theme-moon { background: #1a1a2a; color: #c8d0e0; }
        body.theme-hightech { background: #0a0a1a; color: #88ddff; }
        body.theme-nature { background: #0a1a0a; color: #88dd88; }
        body.theme-noir { background: #0a0a0a; color: #ddccaa; }
        body.theme-chaos { background: #1a0a1a; color: #ff88ff; }
        body.theme-midnight { background: #050510; color: #aabbdd; }
        body.theme-candy { background: #1a0a1a; color: #ff88dd; }
        body.theme-stealth { background: #0a0a0a; color: #888888; }
        body.theme-aurora { background: #0a1a1a; color: #88ddbb; }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1 id="appTitle">🧠 NeoBrain</h1>
            <div class="header-actions">
                <button class="btn btn-success" onclick="showCreateCharacterDialog()">➕ Персонаж</button>
                <button class="btn btn-purple" onclick="showCreateRoom()">🏠 Комната</button>
                <button class="btn" onclick="loadData()">🔄 Обновить</button>
                <button class="btn" onclick="openShareModal()">📤</button>
                <button class="btn" id="toggleBtn">⚙️</button>
            </div>
        </header>

        <div class="panel" id="panel" style="display:none;">
            <div class="panel-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
                <div>
                    <h4 style="color:#d4e8ff;">👤 Персонажи</h4>
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
                        <select id="charSelect" style="flex:1; padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); color:#d4e8ff;"></select>
                        <button class="btn btn-sm btn-danger" onclick="deleteCurrentCharacter()">🗑</button>
                    </div>
                    <div id="charList" style="max-height:160px; overflow-y:auto;"></div>
                </div>
                <div>
                    <h4 style="color:#d4e8ff;">⚙️ Настройки</h4>
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
                        <span style="font-size:13px; color:#8899bb;">🤖</span>
                        <select id="providerSelect" style="flex:1; padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); color:#d4e8ff;">
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI</option>
                            <option value="gemini">Gemini</option>
                            <option value="claude">Claude</option>
                        </select>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
                        <span style="font-size:13px; color:#8899bb;">📦</span>
                        <select id="modelSelect" style="flex:1; padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); color:#d4e8ff;">
                            <option value="qwen2.5-coder:1.5b">1.5b (Быстрая)</option>
                            <option value="llama3.2:3b">3b (Средняя)</option>
                            <option value="mistral:7b">7b (Умная)</option>
                            <option value="llama3.1:8b">8b (Тяжёлая)</option>
                        </select>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
                        <span style="font-size:13px; color:#8899bb;">🎨</span>
                        <select id="themeSelect" style="flex:1; padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); color:#d4e8ff;">
                            <option value="neon">💠 Неон</option><option value="cyber">🌀 Киберпанк</option>
                            <option value="matrix">💚 Матрица</option><option value="ocean">🌊 Океан</option>
                            <option value="sunset">🌅 Закат</option><option value="forest">🌳 Лес</option>
                            <option value="cosmos">🌠 Космос</option><option value="lava">🌋 Лава</option>
                            <option value="gold">✨ Золото</option><option value="purple">🟣 Пурпур</option>
                            <option value="cherry">🌸 Вишня</option><option value="emerald">💎 Изумруд</option>
                            <option value="sunny">☀️ Солнечная</option><option value="ice">❄️ Лёд</option>
                            <option value="wine">🍷 Вино</option><option value="moon">🌙 Лунная</option>
                            <option value="hightech">🧊 Хай-тек</option><option value="nature">🌿 Природа</option>
                            <option value="noir">🕶️ Нуар</option><option value="chaos">🌀 Хаос</option>
                            <option value="midnight">🌙 Полночь</option><option value="candy">🍬 Конфетка</option>
                            <option value="stealth">🥷 Стелс</option><option value="aurora">🌌 Аврора</option>
                        </select>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
                        <span style="font-size:13px; color:#8899bb;">😬 Кринжометр</span>
                        <input type="range" id="cringeSlider" min="0" max="10" value="5" style="width:160px; height:6px; accent-color:#ff44ff; border-radius:10px;">
                        <span id="cringeLabel" style="font-size:13px; color:#8899bb;">5</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                        <span style="font-size:13px; color:#8899bb;">🌡️ Температура</span>
                        <input type="range" id="temperatureSlider" min="0" max="10" value="5" style="width:160px; height:6px; accent-color:#00d4ff; border-radius:10px;">
                        <span id="temperatureLabel" style="font-size:13px; color:#8899bb;">5</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="ai-section" style="padding:24px; border-radius:16px; border:1px solid rgba(255,255,255,0.06); background:rgba(255,255,255,0.02); min-height:500px;">
            <div id="chatContainer" style="max-height:400px; overflow-y:auto; padding:12px; margin-bottom:12px;"></div>
            <div class="ai-input-group" style="display:flex; gap:12px; flex-wrap:wrap; margin-top:10px;">
                <input type="text" id="aiInput" placeholder="Напишите сообщение..." style="flex:1; padding:10px 16px; border-radius:12px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); color:#d4e8ff; outline:none;">
                <button class="btn btn-primary" id="aiSendBtn">Отправить</button>
            </div>
        </div>
        
        <div id="status">Готов к работе...</div>
    </div>

    <!-- Модальное окно: Персонаж -->
    <div class="modal-overlay" id="charModal">
        <div class="modal">
            <h2>✦ Новый персонаж</h2>
            <label>Имя:</label>
            <input type="text" id="charName" placeholder="Введите имя...">
            <label>Описание/характер:</label>
            <input type="text" id="charStyle" placeholder="Весёлый, серьёзный, добрый...">
            <label>System prompt:</label>
            <input type="text" id="charPrompt" placeholder="Ты — полезный AI-помощник...">
            <div class="modal-actions">
                <button class="btn" onclick="closeModal('charModal')">Отмена</button>
                <button class="btn btn-success" onclick="createCharacter()">✅ Создать</button>
            </div>
        </div>
    </div>

    <!-- Модальное окно: Комната -->
    <div class="modal-overlay" id="roomModal">
        <div class="modal">
            <h2>🏠 Создание комнаты</h2>
            <label>Название комнаты:</label>
            <input type="text" id="roomName" placeholder="Введите название...">
            <label>Выберите персонажей (2-10):</label>
            <div class="checkbox-group" id="roomChars"></div>
            <label>Режим ответов:</label>
            <select id="roomMode">
                <option value="random">🎲 Случайный</option>
                <option value="strict">🎯 Строгий</option>
                <option value="interrupt">💬 Перебивание</option>
            </select>
            <label>Схема (для строгого режима, через →):</label>
            <input type="text" id="roomOrder" placeholder="Например: П1→П2→П3">
            <div class="modal-actions">
                <button class="btn" onclick="closeModal('roomModal')">Отмена</button>
                <button class="btn btn-purple" onclick="createRoom()">🏠 Создать</button>
            </div>
        </div>
    </div>

    <!-- Модальное окно: Поделиться -->
    <div class="modal-overlay" id="shareModal" onclick="if(event.target===this) closeShareModal()">
        <div class="modal">
            <h2>📤 Поделиться доступом</h2>
            <p style="color:#8899bb; margin-bottom:10px;">Отправь эту ссылку друзьям в одной сети:</p>
            <div style="display:flex; gap:10px; margin-bottom:16px;">
                <span id="shareLinkText" style="flex:1; padding:8px 12px; border-radius:8px; background:rgba(255,255,255,0.04); color:#d4e8ff; word-break:break-all;">Загрузка...</span>
                <button class="btn btn-primary" onclick="copyShareLink()">Копировать</button>
            </div>
            <div style="display:flex; justify-content:flex-end;">
                <button class="btn" onclick="closeShareModal()">Закрыть</button>
            </div>
        </div>
    </div>

    <script>
        // ========================================
        // ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
        // ========================================
        var currentId = null;
        var currentType = null;
        var characters = [];
        var rooms = [];

        // ========================================
        // МОДАЛЬНЫЕ ОКНА
        // ========================================
        function showModal(id) {
            var el = document.getElementById(id);
            if (el) el.style.display = 'flex';
        }

        function closeModal(id) {
            var el = document.getElementById(id);
            if (el) el.style.display = 'none';
        }

        function closeShareModal() {
            var el = document.getElementById('shareModal');
            if (el) el.style.display = 'none';
        }

        function openShareModal() {
            var el = document.getElementById('shareModal');
            if (el) el.style.display = 'flex';
            fetch('/get_ip')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var linkEl = document.getElementById('shareLinkText');
                    if (linkEl) linkEl.textContent = 'http://' + data.ip + ':8000';
                })
                .catch(function() {
                    var linkEl = document.getElementById('shareLinkText');
                    if (linkEl) linkEl.textContent = 'Не удалось получить IP';
                });
        }

        function copyShareLink() {
            var textEl = document.getElementById('shareLinkText');
            if (!textEl) return;
            var text = textEl.textContent;
            navigator.clipboard.writeText(text)
                .then(function() { alert('Ссылка скопирована!'); })
                .catch(function() { alert('Не удалось скопировать ссылку'); });
        }

        // ========================================
        // ЗАГРУЗКА ДАННЫХ
        // ========================================
        function loadData() {
            var statusEl = document.getElementById('status');
            if (statusEl) statusEl.textContent = '⏳ Загрузка...';
            
            Promise.all([
                fetch('/characters').then(function(r) { 
                    if (!r.ok) throw new Error('Ошибка сервера: ' + r.status);
                    return r.json(); 
                }),
                fetch('/rooms').then(function(r) { 
                    if (!r.ok) throw new Error('Ошибка сервера: ' + r.status);
                    return r.json(); 
                })
            ])
            .then(function(data) {
                var charData = data[0];
                var roomData = data[1];
                characters = charData.characters || [];
                rooms = roomData.rooms || [];
                renderAll();
                if (characters.length > 0 && !currentId) {
                    selectCharacter(characters[0].id);
                }
                if (statusEl) statusEl.textContent = '✅ Данные обновлены';
            })
            .catch(function(error) {
                if (statusEl) statusEl.textContent = '❌ Ошибка: ' + error.message;
                alert('Ошибка загрузки: ' + error.message + '\n\nУбедитесь, что сервер запущен (http://localhost:8000)');
            });
        }

        // ========================================
        // ОСНОВНАЯ ОТРИСОВКА
        // ========================================
        function renderAll() {
            renderSidebar();
            renderCharSelect();
            renderCharList();
        }

        // ========================================
        // БОКОВАЯ ПАНЕЛЬ (СПИСОК СЛЕВА)
        // ========================================
        function renderSidebar() {
            var list = document.getElementById('sidebarList');
            if (!list) return;
            list.innerHTML = '';

            var activeTab = document.querySelector('.tab.active');
            var tab = activeTab ? activeTab.dataset.tab : 'characters';
            var items = tab === 'characters' ? characters : rooms;

            if (!items || items.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div>Нет ' + (tab === 'characters' ? 'персонажей' : 'комнат') + '</div></div>';
                return;
            }

            items.forEach(function(item) {
                var div = document.createElement('div');
                div.className = 'chat-item' + (currentId === item.id ? ' active' : '');

                var nameSpan = document.createElement('span');
                nameSpan.className = 'name';
                if (tab === 'characters') {
                    nameSpan.textContent = '👤 ' + item.name;
                } else {
                    var charNames = (item.characters || []).map(function(c) { return c.name; }).join(', ');
                    nameSpan.textContent = '🏠 ' + item.name + ' (' + charNames + ')';
                }
                div.appendChild(nameSpan);

                var actions = document.createElement('div');
                actions.style.display = 'flex';
                actions.style.alignItems = 'center';
                actions.style.gap = '6px';

                var badge = document.createElement('span');
                badge.className = 'badge';
                badge.textContent = item.history_count || 0;
                actions.appendChild(badge);

                var delBtn = document.createElement('button');
                delBtn.className = 'delete-btn';
                delBtn.textContent = '✕';
                delBtn.onclick = function(e) {
                    e.stopPropagation();
                    if (confirm('Удалить?')) {
                        var url = tab === 'characters' ? '/character/' + item.id : '/room/' + item.id;
                        fetch(url, { method: 'DELETE' })
                            .then(function() {
                                if (currentId === item.id) {
                                    currentId = null;
                                    clearChat();
                                }
                                loadData();
                            });
                    }
                };
                actions.appendChild(delBtn);

                div.appendChild(actions);
                div.onclick = function() {
                    if (tab === 'characters') {
                        openCharacter(item.id);
                    } else {
                        openRoom(item.id);
                    }
                };

                list.appendChild(div);
            });
        }

        // ========================================
        // ВЫБОР ПЕРСОНАЖА (В ПАНЕЛИ НАСТРОЕК)
        // ========================================
        function renderCharSelect() {
            var select = document.getElementById('charSelect');
            if (!select) return;
            select.innerHTML = '';

            if (!characters || characters.length === 0) {
                var opt = document.createElement('option');
                opt.textContent = 'Нет персонажей';
                select.appendChild(opt);
                return;
            }

            characters.forEach(function(char) {
                var opt = document.createElement('option');
                opt.value = char.id;
                opt.textContent = char.name + (char.gender === 'female' ? ' ♀' : ' ♂');
                select.appendChild(opt);
            });

            if (currentId) {
                select.value = currentId;
            } else if (characters.length > 0) {
                select.value = characters[0].id;
            }

            select.onchange = function() {
                if (this.value) {
                    selectCharacter(this.value);
                }
            };
        }

        // ========================================
        // СПИСОК ПЕРСОНАЖЕЙ (В ПАНЕЛИ НАСТРОЕК)
        // ========================================
        function renderCharList() {
            var container = document.getElementById('charList');
            if (!container) return;
            container.innerHTML = '';

            if (!characters || characters.length === 0) {
                container.innerHTML = '<div style="color:#8899bb; padding:10px; text-align:center;">Нет персонажей</div>';
                return;
            }

            characters.forEach(function(char) {
                var div = document.createElement('div');
                div.className = 'char-item';
                div.style.cssText = 'display:flex; justify-content:space-between; padding:8px 14px; border-radius:10px; color:#d4e8ff; cursor:pointer;';
                div.onclick = function() { selectCharacter(char.id); };

                var span = document.createElement('span');
                span.textContent = char.name + ' (' + char.history_count + ' сообщ.)';

                var deleteBtn = document.createElement('button');
                deleteBtn.textContent = '✕';
                deleteBtn.style.cssText = 'background:none; border:none; color:#ff6b6b; cursor:pointer; font-size:14px;';
                deleteBtn.onclick = function(e) {
                    e.stopPropagation();
                    if (confirm('Удалить персонажа "' + char.name + '"?')) {
                        fetch('/character/' + char.id, { method: 'DELETE' })
                            .then(function() {
                                if (currentId === char.id) {
                                    currentId = null;
                                    clearChat();
                                }
                                loadData();
                            });
                    }
                };

                div.appendChild(span);
                div.appendChild(deleteBtn);
                container.appendChild(div);
            });
        }

        // ========================================
        // ПЕРСОНАЖИ
        // ========================================
        function showCreateCharacterDialog() {
            var nameEl = document.getElementById('charName');
            var styleEl = document.getElementById('charStyle');
            var promptEl = document.getElementById('charPrompt');
            if (nameEl) nameEl.value = '';
            if (styleEl) styleEl.value = '';
            if (promptEl) promptEl.value = 'Ты — полезный и дружелюбный AI-помощник.';
            showModal('charModal');
        }

        function createCharacter() {
            var statusEl = document.getElementById('status');
            
            var nameEl = document.getElementById('charName');
            var styleEl = document.getElementById('charStyle');
            var promptEl = document.getElementById('charPrompt');
            
            if (!nameEl || !styleEl || !promptEl) {
                alert('Ошибка: не найдены поля ввода');
                return;
            }
            
            var name = nameEl.value.trim();
            if (!name) {
                alert('Введите имя персонажа!');
                return;
            }

            var style = styleEl.value.trim();
            var system_prompt = promptEl.value.trim();

            if (statusEl) statusEl.textContent = '⏳ Создание персонажа...';

            fetch('/character/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    style: style,
                    system_prompt: system_prompt
                })
            })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Ошибка сервера: ' + response.status);
                }
                return response.json();
            })
            .then(function(data) {
                if (data.error) {
                    if (statusEl) statusEl.textContent = '❌ Ошибка: ' + data.error;
                    alert('Ошибка: ' + data.error);
                    return;
                }
                closeModal('charModal');
                loadData();
                if (statusEl) statusEl.textContent = '✅ Персонаж "' + name + '" создан!';
            })
            .catch(function(error) {
                if (statusEl) statusEl.textContent = '❌ Ошибка: ' + error.message;
                alert('Ошибка при создании персонажа: ' + error.message);
            });
        }

        function selectCharacter(id) {
            if (!id) return;
            currentId = id;
            currentType = 'character';
            renderAll();
            loadCharacterHistory(id);
            document.getElementById('status').textContent = '💬 Загрузка...';
        }

        function loadCharacterHistory(id) {
            fetch('/character/' + id)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var container = document.getElementById('chatContainer');
                    if (!container) return;
                    container.innerHTML = '';
                    if (data.history && data.history.length > 0) {
                        data.history.forEach(function(msg) {
                            addMessageToChat(msg.role, msg.content);
                        });
                    } else {
                        var empty = document.createElement('div');
                        empty.style.cssText = 'text-align:center; padding:20px; color:#8899bb;';
                        empty.textContent = '💬 Начните диалог с персонажем';
                        container.appendChild(empty);
                    }
                    var statusEl = document.getElementById('status');
                    if (statusEl) statusEl.textContent = '💬 ' + data.name;
                    var titleEl = document.getElementById('chatTitle');
                    var subtitleEl = document.getElementById('chatSubtitle');
                    if (titleEl) titleEl.textContent = '👤 ' + data.name;
                    if (subtitleEl) subtitleEl.textContent = data.style || 'Без стиля';
                    var inputEl = document.getElementById('messageInput');
                    var sendEl = document.getElementById('sendBtn');
                    if (inputEl) inputEl.disabled = false;
                    if (sendEl) sendEl.disabled = false;
                })
                .catch(function() {
                    document.getElementById('status').textContent = '❌ Ошибка загрузки истории';
                });
        }

        function deleteCurrentCharacter() {
            if (!currentId) {
                alert('Выберите персонажа');
                return;
            }
            if (!confirm('Удалить персонажа?')) return;
            fetch('/character/' + currentId, { method: 'DELETE' })
                .then(function() {
                    currentId = null;
                    clearChat();
                    loadData();
                });
        }

        // ========================================
        // КОМНАТЫ
        // ========================================
        function showCreateRoom() {
            fetch('/characters')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var container = document.getElementById('roomChars');
                    if (!container) return;
                    container.innerHTML = '';
                    var chars = data.characters || [];
                    if (chars.length === 0) {
                        container.innerHTML = '<div style="color:#8899bb; padding:10px; text-align:center;">Сначала создайте персонажей!</div>';
                        return;
                    }
                    chars.forEach(function(char) {
                        var label = document.createElement('label');
                        var cb = document.createElement('input');
                        cb.type = 'checkbox';
                        cb.value = char.id;
                        label.appendChild(cb);
                        label.appendChild(document.createTextNode(' ' + char.name));
                        container.appendChild(label);
                    });
                    var nameEl = document.getElementById('roomName');
                    var modeEl = document.getElementById('roomMode');
                    var orderEl = document.getElementById('roomOrder');
                    if (nameEl) nameEl.value = 'Комната №' + Date.now().toString().slice(-4);
                    if (modeEl) modeEl.value = 'random';
                    if (orderEl) orderEl.value = '';
                    showModal('roomModal');
                })
                .catch(function(error) {
                    alert('Ошибка загрузки персонажей: ' + error);
                });
        }

        function createRoom() {
            var nameEl = document.getElementById('roomName');
            if (!nameEl) return;
            var name = nameEl.value.trim();
            if (!name) {
                alert('Введите название комнаты!');
                return;
            }

            var checkboxes = document.querySelectorAll('#roomChars input:checked');
            var character_ids = Array.from(checkboxes).map(function(cb) { return cb.value; });

            if (character_ids.length < 2) {
                alert('Выберите минимум 2 персонажа!');
                return;
            }
            if (character_ids.length > 10) {
                alert('Максимум 10 персонажей!');
                return;
            }

            var modeEl = document.getElementById('roomMode');
            var orderEl = document.getElementById('roomOrder');
            var mode = modeEl ? modeEl.value : 'random';
            var orderText = orderEl ? orderEl.value.trim() : '';

            var order = [];
            if (mode === 'strict' && orderText) {
                order = orderText.split('→').map(function(s) { return s.trim(); }).filter(function(s) { return s; });
            }

            fetch('/room/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    character_ids: character_ids,
                    mode: mode,
                    order: order,
                    interrupt: mode === 'interrupt'
                })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                closeModal('roomModal');
                if (data.error) {
                    alert('Ошибка: ' + data.error);
                    return;
                }
                loadData();
                document.getElementById('status').textContent = '✅ Комната "' + name + '" создана!';
                switchTab('rooms');
            })
            .catch(function(error) {
                alert('Ошибка при создании комнаты: ' + error);
            });
        }

        function openRoom(id) {
            currentId = id;
            currentType = 'room';
            renderSidebar();

            fetch('/room/' + id)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var charNames = (data.characters || []).map(function(c) { return c.name; }).join(', ');
                    var titleEl = document.getElementById('chatTitle');
                    var subtitleEl = document.getElementById('chatSubtitle');
                    if (titleEl) titleEl.textContent = '🏠 ' + data.name;
                    if (subtitleEl) subtitleEl.textContent = '👥 ' + charNames + ' | Режим: ' + data.mode;

                    var schemaHtml = '';
                    if (data.mode === 'strict' && data.order && data.order.length > 0) {
                        var chars = data.characters || [];
                        schemaHtml = '<div class="room-schema">';
                        data.order.forEach(function(id, i) {
                            var c = chars.find(function(ch) { return ch.id === id; });
                            schemaHtml += '<span class="schema-block">' + (c ? c.name : '?') + '</span>';
                            if (i < data.order.length - 1) {
                                schemaHtml += '<span class="schema-arrow">→</span>';
                            }
                        });
                        schemaHtml += '<span class="schema-arrow">↻</span>';
                        schemaHtml += '</div>';
                    } else if (data.mode === 'random') {
                        schemaHtml = '<div class="room-schema"><span class="schema-mode">🎲 Случайный порядок</span></div>';
                    } else if (data.mode === 'interrupt') {
                        schemaHtml = '<div class="room-schema"><span class="schema-mode">💬 С возможностью перебивания</span></div>';
                    }
                    if (subtitleEl) subtitleEl.innerHTML += schemaHtml;

                    var inputEl = document.getElementById('messageInput');
                    var sendEl = document.getElementById('sendBtn');
                    if (inputEl) inputEl.disabled = false;
                    if (sendEl) sendEl.disabled = false;

                    var messages = document.getElementById('chatMessages');
                    if (!messages) return;
                    messages.innerHTML = '';
                    if (data.history && data.history.length > 0) {
                        data.history.forEach(function(msg) {
                            var name = msg.role === 'user' ? 'Вы' : (data.characters || []).find(function(c) { return c.id === msg.role; })?.name || msg.role;
                            addMessage(msg.role === 'user' ? 'user' : 'assistant', msg.content, name);
                        });
                    } else {
                        var empty = document.createElement('div');
                        empty.style.cssText = 'text-align:center; padding:20px; color:#8899bb;';
                        empty.textContent = '💬 Начните диалог в комнате';
                        messages.appendChild(empty);
                    }

                    document.getElementById('status').textContent = '💬 Комната: ' + data.name;
                });
        }

        function sendToRoom(text) {
            addMessage('user', text, 'Вы');

            fetch('/room/' + currentId + '/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, role: 'user' })
            }).then(function() {
                fetch('/room/' + currentId + '/next')
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.character) {
                            var char = data.character;
                            document.getElementById('status').textContent = '⏳ ' + char.name + ' думает...';

                            fetch('/ask', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    prompt: 'Ты — ' + char.name + '. Твой характер: ' + (char.personality || 'нейтральный') + '. Ответь на сообщение пользователя, учитывая историю чата. Будь кратким.',
                                    character_id: char.id
                                })
                            })
                            .then(function(r) { return r.json(); })
                            .then(function(res) {
                                if (res.response) {
                                    fetch('/room/' + currentId + '/message', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ text: res.response, role: char.id })
                                    }).then(function() {
                                        addMessage('assistant', res.response, char.name);
                                        document.getElementById('status').textContent = '💬 ' + char.name + ' ответил';
                                        loadData();
                                    });
                                }
                            });
                        }
                    });
            });
        }

        // ========================================
        // ВКЛАДКИ
        // ========================================
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
            var target = document.querySelector('.tab[data-tab="' + tab + '"]');
            if (target) target.classList.add('active');

            var title = document.getElementById('sidebarTitle');
            if (title) {
                title.textContent = tab === 'characters' ? '📋 Список персонажей' : '🏠 Список комнат';
            }

            renderSidebar();
            clearChat();
            document.getElementById('status').textContent = '✅ Переключено на ' + (tab === 'characters' ? 'персонажей' : 'комнаты');
        }

        // ========================================
        // ЧАТ
        // ========================================
        function initChat() {
            var container = document.getElementById('chatContainer');
            if (!container) return;
            var welcome = document.createElement('div');
            welcome.style.cssText = 'text-align:center; padding:40px; color:#8899bb;';
            welcome.innerHTML = '<div style="font-size:48px; margin-bottom:12px;">💬</div><div>Выберите персонажа или комнату</div>';
            container.appendChild(welcome);
        }

        function addMessageToChat(role, content) {
            var container = document.getElementById('chatContainer');
            if (!container) return;
            var empty = container.querySelector('.empty-state');
            if (empty) empty.remove();

            var wrapper = document.createElement('div');
            wrapper.className = 'message ' + role;
            wrapper.style.cssText = 'display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;' + (role === 'user' ? ' flex-direction:row-reverse;' : '');

            var avatarDiv = document.createElement('div');
            avatarDiv.className = 'avatar';
            avatarDiv.style.cssText = 'width:36px;height:36px;border-radius:50%;background:#2a2a4a;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;border:1px solid rgba(255,255,255,0.08);';
            avatarDiv.textContent = role === 'user' ? '👤' : '🤖';

            var bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'bubble';
            bubbleDiv.style.cssText = 'padding:10px 16px;border-radius:12px;max-width:75%;word-break:break-word;font-size:14px;line-height:1.5;color:#d4e8ff;' + 
                (role === 'user' ? 'background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.1);' : 'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);');
            bubbleDiv.textContent = content;

            wrapper.appendChild(avatarDiv);
            wrapper.appendChild(bubbleDiv);
            container.appendChild(wrapper);
            container.scrollTop = container.scrollHeight;
        }

        function addMessage(role, content, name) {
            var container = document.getElementById('chatMessages');
            if (!container) return;
            var empty = container.querySelector('.empty-state');
            if (empty) empty.remove();

            var wrapper = document.createElement('div');
            wrapper.className = 'message ' + role;
            wrapper.style.cssText = 'display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;' + (role === 'user' ? ' flex-direction:row-reverse;' : '');

            var avatarDiv = document.createElement('div');
            avatarDiv.className = 'avatar';
            avatarDiv.style.cssText = 'width:36px;height:36px;border-radius:50%;background:#2a2a4a;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;border:1px solid rgba(255,255,255,0.08);';
            avatarDiv.textContent = role === 'user' ? '👤' : '🤖';

            var bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'bubble';
            bubbleDiv.style.cssText = 'padding:10px 16px;border-radius:12px;max-width:75%;word-break:break-word;font-size:14px;line-height:1.5;color:#d4e8ff;' + 
                (role === 'user' ? 'background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.1);' : 'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);');

            var nameLabel = document.createElement('div');
            nameLabel.style.cssText = 'font-size:11px;color:#8899bb;margin-bottom:2px;';
            nameLabel.textContent = name || (role === 'user' ? 'Вы' : 'AI');

            var textSpan = document.createElement('div');
            textSpan.textContent = content;

            bubbleDiv.appendChild(nameLabel);
            bubbleDiv.appendChild(textSpan);
            wrapper.appendChild(avatarDiv);
            wrapper.appendChild(bubbleDiv);
            container.appendChild(wrapper);
            container.scrollTop = container.scrollHeight;
        }

        function clearChat() {
            var container = document.getElementById('chatContainer');
            if (!container) return;
            container.innerHTML = '';
            var empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.style.cssText = 'text-align:center; padding:40px; color:#8899bb;';
            empty.innerHTML = '<div style="font-size:48px; margin-bottom:12px;">💬</div><div>Выберите персонажа или комнату</div>';
            container.appendChild(empty);

            var inputEl = document.getElementById('messageInput');
            var sendEl = document.getElementById('sendBtn');
            var titleEl = document.getElementById('chatTitle');
            var subtitleEl = document.getElementById('chatSubtitle');
            if (inputEl) inputEl.disabled = true;
            if (sendEl) sendEl.disabled = true;
            if (titleEl) titleEl.textContent = 'Выберите чат';
            if (subtitleEl) subtitleEl.textContent = 'Нажмите на элемент слева';
        }

        // ========================================
        // ОТПРАВКА СООБЩЕНИЙ
        // ========================================
        function initMessageSend() {
            var input = document.getElementById('aiInput');
            var sendBtn = document.getElementById('aiSendBtn');

            function sendMessage() {
                if (!input) return;
                var text = input.value.trim();
                if (!text) return;
                if (!currentId) {
                    alert('Сначала создайте или выберите персонажа!');
                    return;
                }

                if (currentType === 'character') {
                    sendToCharacter(text);
                    input.value = '';
                } else if (currentType === 'room') {
                    sendToRoom(text);
                    input.value = '';
                }
            }

            function sendToCharacter(text) {
                addMessageToChat('user', text);

                var providerEl = document.getElementById('providerSelect');
                var modelEl = document.getElementById('modelSelect');
                var cringeEl = document.getElementById('cringeSlider');
                var tempEl = document.getElementById('temperatureSlider');
                
                var provider = providerEl ? providerEl.value : 'ollama';
                var model = modelEl ? modelEl.value : 'qwen2.5-coder:1.5b';
                var cringe = cringeEl ? parseInt(cringeEl.value) : 5;
                var temperature = tempEl ? parseInt(tempEl.value) : 5;

                var thinkingWrapper = document.createElement('div');
                thinkingWrapper.className = 'message assistant';
                thinkingWrapper.style.cssText = 'display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;';

                var thinkingAvatar = document.createElement('div');
                thinkingAvatar.className = 'avatar';
                thinkingAvatar.style.cssText = 'width:36px;height:36px;border-radius:50%;background:#2a2a4a;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;border:1px solid rgba(255,255,255,0.08);';
                thinkingAvatar.textContent = '🤖';

                var thinkingMsg = document.createElement('div');
                thinkingMsg.className = 'bubble';
                thinkingMsg.style.cssText = 'padding:10px 16px;border-radius:12px;max-width:75%;word-break:break-word;font-size:14px;line-height:1.5;color:#d4e8ff;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);';
                thinkingMsg.textContent = 'Думаю...';

                thinkingWrapper.appendChild(thinkingAvatar);
                thinkingWrapper.appendChild(thinkingMsg);
                var container = document.getElementById('chatContainer');
                if (container) container.appendChild(thinkingWrapper);

                fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: text,
                        provider: provider,
                        model: model,
                        cringe_level: cringe,
                        temperature: temperature,
                        character_id: currentId
                    })
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    thinkingWrapper.remove();
                    if (data.response) {
                        addMessageToChat('ai', data.response);
                    } else {
                        addMessageToChat('ai', 'Ошибка: ' + (data.error || 'Неизвестная ошибка'));
                    }
                    loadData();
                })
                .catch(function() {
                    thinkingWrapper.remove();
                    addMessageToChat('ai', 'Ошибка соединения с сервером');
                });
            }

            if (sendBtn) sendBtn.addEventListener('click', sendMessage);
            if (input) input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });
        }

        // ========================================
        // ПАНЕЛЬ НАСТРОЕК
        // ========================================
        function initPanel() {
            var toggleBtn = document.getElementById('toggleBtn');
            var panel = document.getElementById('panel');
            if (!toggleBtn || !panel) return;
            toggleBtn.addEventListener('click', function() {
                if (panel.style.display === 'block') {
                    panel.style.display = 'none';
                    toggleBtn.textContent = '⚙️';
                } else {
                    panel.style.display = 'block';
                    toggleBtn.textContent = '▲';
                }
            });
        }

        // ========================================
        // СЛАЙДЕРЫ
        // ========================================
        function initSliders() {
            var cringeSlider = document.getElementById('cringeSlider');
            var cringeLabel = document.getElementById('cringeLabel');
            if (cringeSlider && cringeLabel) {
                cringeSlider.addEventListener('input', function() {
                    cringeLabel.textContent = this.value;
                });
            }

            var tempSlider = document.getElementById('temperatureSlider');
            var tempLabel = document.getElementById('temperatureLabel');
            if (tempSlider && tempLabel) {
                tempSlider.addEventListener('input', function() {
                    tempLabel.textContent = this.value;
                });
            }
        }

        // ========================================
        // ТЕМЫ
        // ========================================
        function initThemes() {
            var themeSelect = document.getElementById('themeSelect');
            if (!themeSelect) return;
            var savedTheme = localStorage.getItem('neobrain_theme');
            if (savedTheme) {
                themeSelect.value = savedTheme;
                document.body.className = 'theme-' + savedTheme;
            }
            themeSelect.addEventListener('change', function() {
                document.body.className = 'theme-' + this.value;
                localStorage.setItem('neobrain_theme', this.value);
            });
        }

        // ========================================
        // ИНИЦИАЛИЗАЦИЯ
        // ========================================
        document.addEventListener('DOMContentLoaded', function() {
            // Настройка вкладок
            document.querySelectorAll('.tab').forEach(function(tab) {
                tab.addEventListener('click', function() {
                    switchTab(this.dataset.tab);
                });
            });

            // Инициализация
            initPanel();
            initChat();
            initThemes();
            initSliders();
            initMessageSend();
            loadData();
        });
    </script>
</body>
</html>
"""

# ============================================================
# ЗАПУСК
# ============================================================

app.get("/")(lambda: HTMLResponse(html_template))

def run_app():
    logger.info("🔄 Запуск NeoBrain...")
    try:
        is_exe = getattr(sys, 'frozen', False)
        
        if not is_ollama_running():
            logger.info("🔄 Ollama не запущена, запускаем...")
            try:
                if sys.platform == "win32":
                    subprocess.Popen(
                        ["ollama", "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    subprocess.Popen(
                        ["ollama", "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                time.sleep(3)
                logger.info("✅ Ollama запущена")
            except Exception as e:
                logger.error(f"❌ Ошибка запуска Ollama: {e}")
        else:
            logger.info("✅ Ollama уже запущена")
        
        if is_exe:
            import webview
            logger.info("🌐 Запуск WebView на http://127.0.0.1:8000")
            webview.create_window('NeoBrain', 'http://127.0.0.1:8000', width=1200, height=800)
            webview.start()
            return
        
        def run_server():
            try:
                uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
            except Exception as e:
                logger.error(f"❌ Ошибка сервера: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)
        
        try:
            requests.get("http://localhost:8000", timeout=2)
            logger.info("✅ Сервер запущен на http://localhost:8000")
        except:
            logger.error("❌ Сервер не запустился!")
            input("Press Enter to exit...")
            return
        
        try:
            import webview
        except ImportError:
            logger.error("❌ pywebview не установлен")
            input("Press Enter to exit...")
            return
        
        logger.info(f"🌐 Запуск WebView на http://{LOCAL_IP}:8000")
        webview.create_window('NeoBrain', 'http://localhost:8000', width=1200, height=800)
        webview.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 NeoBrain остановлен")
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
        import traceback
        logger.critical(traceback.format_exc())

if __name__ == "__main__":
    run_app()