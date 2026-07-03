# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import requests
import socket
import time
import threading
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

# ============================================================
# ОТКЛЮЧАЕМ ВЫВОД В КОНСОЛЬ (чтобы избежать ошибок кодировки)
# ============================================================
if sys.platform == "win32":
    try:
        os.system("chcp 65001 > nul")
    except:
        pass
    try:
        if sys.stdout is not None:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    except:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

app = FastAPI()

# ============================================================
# ФАЙЛЫ ДЛЯ ХРАНЕНИЯ
# ============================================================
HISTORY_FILE = "history.json"
CONFIG_FILE = "neobrain_config.json"

def load_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ============================================================
# ПРОВЕРКА OLLAMA
# ============================================================
def check_ollama():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=3)
        return True
    except:
        return False

# ============================================================
# ПОЛУЧЕНИЕ ЛОКАЛЬНОГО IP
# ============================================================
def get_local_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ============================================================
# НАСТРОЙКИ
# ============================================================
def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "api_keys": {"openai": "", "gemini": "", "claude": ""},
            "default_provider": "ollama",
            "server_name": "NeoBrain Server",
            "access_code": ""
        }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

CONFIG = load_config()

# ============================================================
# AI ПРОВАЙДЕРЫ
# ============================================================
def ask_ollama(prompt, model):
    try:
        check = requests.get("http://localhost:11434/api/tags", timeout=3)
        if check.status_code != 200:
            return {"error": "Ollama не отвечает"}
    except:
        return {"error": "Ollama не запущена"}

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7
        },
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        return {"response": result.get("response", "Нет ответа")}
    else:
        return {"error": f"Ошибка Ollama: {response.status_code}"}

def ask_openai(prompt, api_key, model="gpt-3.5-turbo"):
    if not api_key:
        return {"error": "API ключ OpenAI не указан"}
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {"response": result["choices"][0]["message"]["content"]}
        else:
            return {"error": f"Ошибка OpenAI: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка OpenAI: {str(e)}"}

def ask_gemini(prompt, api_key, model="gemini-pro"):
    if not api_key:
        return {"error": "API ключ Google Gemini не указан"}
    
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}]
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {"response": result["candidates"][0]["content"]["parts"][0]["text"]}
        else:
            return {"error": f"Ошибка Gemini: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка Gemini: {str(e)}"}

def ask_claude(prompt, api_key, model="claude-3-haiku-20240307"):
    if not api_key:
        return {"error": "API ключ Anthropic Claude не указан"}
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {"response": result["content"][0]["text"]}
        else:
            return {"error": f"Ошибка Claude: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка Claude: {str(e)}"}

# ============================================================
# HTML ТЕМПЛЕЙТ
# ============================================================
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeoBrain</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            padding: 20px;
            min-height: 100vh;
            line-height: 1.5;
            transition: all 1.5s cubic-bezier(0.4, 0, 0.2, 1);
            background: #0a0e1a;
            color: #e8f0ff;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            position: relative;
            z-index: 2;
        }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            padding: 16px 0 20px 0;
            border-bottom: 2px solid rgba(0, 212, 255, 0.15);
            margin-bottom: 24px;
        }

        .header h1 {
            font-size: 26px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #00d4ff, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .btn {
            padding: 8px 20px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            backdrop-filter: blur(4px);
        }

        .btn:hover {
            transform: translateY(-2px);
            filter: brightness(1.1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }

        .btn-primary {
            background: #00d4ff;
            color: #0a0e1a;
        }

        .btn-primary:hover {
            background: #33ddff;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3);
        }

        .btn-ghost {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            color: #d4e8ff;
        }

        .btn-ghost:hover {
            background: rgba(255, 255, 255, 0.08);
        }

        .btn-success {
            background: #51cf66;
            color: #0a0e1a;
        }

        .btn-danger {
            background: #ff6b6b;
            color: #0a0e1a;
        }

        .btn-sm {
            padding: 6px 14px;
            font-size: 13px;
            border-radius: 10px;
        }

        #panel {
            display: none;
            padding: 24px;
            margin-bottom: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(8px);
            background: rgba(0, 212, 255, 0.02);
        }

        .panel-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 28px;
        }

        @media (max-width: 700px) {
            .panel-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
        }

        .panel-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .panel-section-title {
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.4;
            padding-bottom: 4px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .panel-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
        }

        .panel-row select, .panel-row input {
            flex: 1;
            min-width: 120px;
            padding: 10px 16px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 14px;
            background: rgba(255, 255, 255, 0.04);
            color: #d4e8ff;
            outline: none;
            transition: all 0.3s ease;
        }

        .panel-row select:focus, .panel-row input:focus {
            border-color: #00d4ff;
            box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.08);
        }

        .panel-row select option {
            background: #1a1a2e;
            color: #eef5ff;
        }

        #charList {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-height: 160px;
            overflow-y: auto;
            padding-right: 6px;
            margin-top: 4px;
        }

        #charList::-webkit-scrollbar {
            width: 4px;
        }
        #charList::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 10px;
        }
        #charList::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.12);
            border-radius: 10px;
        }

        .char-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        .char-item:hover {
            background: rgba(255, 255, 255, 0.06);
            transform: translateX(4px);
        }

        .char-name {
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .char-actions {
            display: flex;
            gap: 6px;
        }

        .char-actions button {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 8px;
            transition: all 0.3s ease;
            opacity: 0.5;
        }

        .char-actions button:hover {
            opacity: 1;
            background: rgba(255, 255, 255, 0.06);
        }

        .char-delete {
            color: #ff6b6b;
        }

        .char-share {
            color: #00d4ff;
        }

        .ai-section {
            padding: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(8px);
            background: rgba(255, 255, 255, 0.02);
        }

        .ai-section h3 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #e0f0ff;
        }

        .ai-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 12px 24px;
            margin-bottom: 16px;
            font-size: 14px;
            padding: 12px 16px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.02);
        }

        .ai-controls .label {
            opacity: 0.5;
            font-weight: 500;
        }

        .ai-controls .badge {
            font-size: 12px;
            opacity: 0.6;
            padding: 2px 14px;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.05);
            font-weight: 600;
        }

        .ai-input-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        .ai-input-group input {
            flex: 1;
            min-width: 180px;
            padding: 10px 16px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 14px;
            background: rgba(255, 255, 255, 0.04);
            color: #d4e8ff;
            outline: none;
            transition: all 0.3s ease;
        }

        .ai-input-group input:focus {
            border-color: #00d4ff;
            box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.08);
        }

        .ai-input-group input::placeholder {
            opacity: 0.4;
        }

        #chatContainer {
            margin-top: 16px;
            max-height: 400px;
            overflow-y: auto;
            padding: 12px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.02);
        }

        #chatContainer::-webkit-scrollbar {
            width: 4px;
        }
        #chatContainer::-webkit-scrollbar-thumb {
            background: rgba(0, 212, 255, 0.3);
            border-radius: 10px;
        }

        .chat-message {
            padding: 10px 16px;
            margin-bottom: 8px;
            border-radius: 12px;
            max-width: 85%;
            word-break: break-word;
        }

        .chat-message.user {
            background: rgba(0, 212, 255, 0.08);
            border: 1px solid rgba(0, 212, 255, 0.1);
            margin-left: auto;
            text-align: right;
        }

        .chat-message.ai {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            margin-right: auto;
        }

        .chat-message .role {
            font-size: 12px;
            opacity: 0.5;
            margin-bottom: 4px;
        }

        #aiOutput {
            display: none;
        }

        #status {
            margin-top: 16px;
            font-size: 13px;
            opacity: 0.5;
            padding: 8px 0;
            font-weight: 500;
            letter-spacing: 0.3px;
        }

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(12px);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .modal-overlay.active {
            display: flex;
        }

        .modal {
            background: #111827;
            border: 1px solid rgba(0, 212, 255, 0.15);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            animation: modalIn 0.4s ease;
        }

        @keyframes modalIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }

        .modal h2 {
            font-size: 24px;
            font-weight: 700;
            color: #e0f0ff;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #00d4ff, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .modal p {
            color: #88bbdd;
            margin-bottom: 16px;
        }

        .modal .share-link {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 12px 16px;
            font-family: 'Consolas', monospace;
            font-size: 14px;
            color: #00d4ff;
            word-break: break-all;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal .share-link button {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 8px;
            color: #00d4ff;
            padding: 6px 14px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s ease;
        }

        .modal .share-link button:hover {
            background: rgba(0, 212, 255, 0.2);
        }

        .modal .btn-close-modal {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.04);
            color: #88bbdd;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .modal .btn-close-modal:hover {
            background: rgba(255, 255, 255, 0.08);
        }

        body.theme-neon { background: #0a0e1a; color: #d4e8ff; }
        body.theme-neon .btn-primary { background: #00d4ff; color: #0a0e1a; }
        body.theme-neon select:focus, body.theme-neon input:focus { border-color: #00d4ff; box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.15); }
        body.theme-neon #panel { background: rgba(0, 212, 255, 0.04); border-color: rgba(0, 212, 255, 0.08); }
        body.theme-neon .ai-section { background: rgba(0, 212, 255, 0.02); border-color: rgba(0, 212, 255, 0.06); }
        body.theme-neon .header { border-bottom-color: rgba(0, 212, 255, 0.08); }

        body.theme-cyber { background: #0d0a1a; color: #ff66ff; }
        body.theme-cyber .btn-primary { background: #ff44ff; color: #0d0a1a; }
        body.theme-cyber select:focus, body.theme-cyber input:focus { border-color: #ff44ff; box-shadow: 0 0 0 4px rgba(255, 68, 255, 0.15); }
        body.theme-cyber #panel { background: rgba(255, 68, 255, 0.04); border-color: rgba(255, 68, 255, 0.08); }
        body.theme-cyber .ai-section { background: rgba(255, 68, 255, 0.02); border-color: rgba(255, 68, 255, 0.06); }
        body.theme-cyber .header { border-bottom-color: rgba(255, 68, 255, 0.08); }

        body.theme-matrix { background: #0a0f0a; color: #66ff66; }
        body.theme-matrix .btn-primary { background: #44ff44; color: #0a0f0a; }
        body.theme-matrix select:focus, body.theme-matrix input:focus { border-color: #44ff44; box-shadow: 0 0 0 4px rgba(68, 255, 68, 0.15); }
        body.theme-matrix #panel { background: rgba(68, 255, 68, 0.04); border-color: rgba(68, 255, 68, 0.08); }
        body.theme-matrix .ai-section { background: rgba(68, 255, 68, 0.02); border-color: rgba(68, 255, 68, 0.06); }
        body.theme-matrix .header { border-bottom-color: rgba(68, 255, 68, 0.08); }

        body.theme-ocean { background: #0a1a2a; color: #66ddff; }
        body.theme-ocean .btn-primary { background: #44ccff; color: #0a1a2a; }
        body.theme-ocean select:focus, body.theme-ocean input:focus { border-color: #44ccff; box-shadow: 0 0 0 4px rgba(68, 204, 255, 0.15); }
        body.theme-ocean #panel { background: rgba(68, 204, 255, 0.04); border-color: rgba(68, 204, 255, 0.08); }
        body.theme-ocean .ai-section { background: rgba(68, 204, 255, 0.02); border-color: rgba(68, 204, 255, 0.06); }
        body.theme-ocean .header { border-bottom-color: rgba(68, 204, 255, 0.08); }

        body.theme-sunset { background: #1a0a0a; color: #ffaa88; }
        body.theme-sunset .btn-primary { background: #ff7744; color: #1a0a0a; }
        body.theme-sunset select:focus, body.theme-sunset input:focus { border-color: #ff7744; box-shadow: 0 0 0 4px rgba(255, 119, 68, 0.15); }
        body.theme-sunset #panel { background: rgba(255, 119, 68, 0.04); border-color: rgba(255, 119, 68, 0.08); }
        body.theme-sunset .ai-section { background: rgba(255, 119, 68, 0.02); border-color: rgba(255, 119, 68, 0.06); }
        body.theme-sunset .header { border-bottom-color: rgba(255, 119, 68, 0.08); }

        body.theme-forest { background: #0a1a0a; color: #88ff88; }
        body.theme-forest .btn-primary { background: #55ff55; color: #0a1a0a; }
        body.theme-forest select:focus, body.theme-forest input:focus { border-color: #55ff55; box-shadow: 0 0 0 4px rgba(85, 255, 85, 0.15); }
        body.theme-forest #panel { background: rgba(85, 255, 85, 0.04); border-color: rgba(85, 255, 85, 0.08); }
        body.theme-forest .ai-section { background: rgba(85, 255, 85, 0.02); border-color: rgba(85, 255, 85, 0.06); }
        body.theme-forest .header { border-bottom-color: rgba(85, 255, 85, 0.08); }

        body.theme-cosmos { background: #05050f; color: #cc88ff; }
        body.theme-cosmos .btn-primary { background: #aa44ff; color: #05050f; }
        body.theme-cosmos select:focus, body.theme-cosmos input:focus { border-color: #aa44ff; box-shadow: 0 0 0 4px rgba(170, 68, 255, 0.15); }
        body.theme-cosmos #panel { background: rgba(170, 68, 255, 0.04); border-color: rgba(170, 68, 255, 0.08); }
        body.theme-cosmos .ai-section { background: rgba(170, 68, 255, 0.02); border-color: rgba(170, 68, 255, 0.06); }
        body.theme-cosmos .header { border-bottom-color: rgba(170, 68, 255, 0.08); }

        body.theme-lava { background: #1a0a05; color: #ff8866; }
        body.theme-lava .btn-primary { background: #ff5533; color: #1a0a05; }
        body.theme-lava select:focus, body.theme-lava input:focus { border-color: #ff5533; box-shadow: 0 0 0 4px rgba(255, 85, 51, 0.15); }
        body.theme-lava #panel { background: rgba(255, 85, 51, 0.04); border-color: rgba(255, 85, 51, 0.08); }
        body.theme-lava .ai-section { background: rgba(255, 85, 51, 0.02); border-color: rgba(255, 85, 51, 0.06); }
        body.theme-lava .header { border-bottom-color: rgba(255, 85, 51, 0.08); }

        body.theme-gold { background: #1a1a0a; color: #ffdd88; }
        body.theme-gold .btn-primary { background: #ffcc44; color: #1a1a0a; }
        body.theme-gold select:focus, body.theme-gold input:focus { border-color: #ffcc44; box-shadow: 0 0 0 4px rgba(255, 204, 68, 0.15); }
        body.theme-gold #panel { background: rgba(255, 204, 68, 0.04); border-color: rgba(255, 204, 68, 0.08); }
        body.theme-gold .ai-section { background: rgba(255, 204, 68, 0.02); border-color: rgba(255, 204, 68, 0.06); }
        body.theme-gold .header { border-bottom-color: rgba(255, 204, 68, 0.08); }

        body.theme-purple { background: #0a0a1a; color: #dd88ff; }
        body.theme-purple .btn-primary { background: #cc44ff; color: #0a0a1a; }
        body.theme-purple select:focus, body.theme-purple input:focus { border-color: #cc44ff; box-shadow: 0 0 0 4px rgba(204, 68, 255, 0.15); }
        body.theme-purple #panel { background: rgba(204, 68, 255, 0.04); border-color: rgba(204, 68, 255, 0.08); }
        body.theme-purple .ai-section { background: rgba(204, 68, 255, 0.02); border-color: rgba(204, 68, 255, 0.06); }
        body.theme-purple .header { border-bottom-color: rgba(204, 68, 255, 0.08); }

        body.theme-cherry { background: #1a0a12; color: #ff88bb; }
        body.theme-cherry .btn-primary { background: #ff44aa; color: #1a0a12; }
        body.theme-cherry select:focus, body.theme-cherry input:focus { border-color: #ff44aa; box-shadow: 0 0 0 4px rgba(255, 68, 170, 0.15); }
        body.theme-cherry #panel { background: rgba(255, 68, 170, 0.04); border-color: rgba(255, 68, 170, 0.08); }
        body.theme-cherry .ai-section { background: rgba(255, 68, 170, 0.02); border-color: rgba(255, 68, 170, 0.06); }
        body.theme-cherry .header { border-bottom-color: rgba(255, 68, 170, 0.08); }

        body.theme-emerald { background: #0a1a0a; color: #66ffaa; }
        body.theme-emerald .btn-primary { background: #44ff88; color: #0a1a0a; }
        body.theme-emerald select:focus, body.theme-emerald input:focus { border-color: #44ff88; box-shadow: 0 0 0 4px rgba(68, 255, 136, 0.15); }
        body.theme-emerald #panel { background: rgba(68, 255, 136, 0.04); border-color: rgba(68, 255, 136, 0.08); }
        body.theme-emerald .ai-section { background: rgba(68, 255, 136, 0.02); border-color: rgba(68, 255, 136, 0.06); }
        body.theme-emerald .header { border-bottom-color: rgba(68, 255, 136, 0.08); }

        body.theme-sunny { background: #f5ede1; color: #3a2a1a; }
        body.theme-sunny .btn-primary { background: #d4a040; color: #f5ede1; }
        body.theme-sunny select:focus, body.theme-sunny input:focus { border-color: #d4a040; box-shadow: 0 0 0 4px rgba(212, 160, 64, 0.15); }
        body.theme-sunny #panel { background: rgba(212, 160, 64, 0.05); border-color: rgba(212, 160, 64, 0.1); }
        body.theme-sunny .ai-section { background: rgba(212, 160, 64, 0.03); border-color: rgba(212, 160, 64, 0.06); }
        body.theme-sunny .header { border-bottom-color: rgba(212, 160, 64, 0.1); }

        body.theme-ice { background: #0a1a2a; color: #88ddff; }
        body.theme-ice .btn-primary { background: #44bbff; color: #0a1a2a; }
        body.theme-ice select:focus, body.theme-ice input:focus { border-color: #44bbff; box-shadow: 0 0 0 4px rgba(68, 187, 255, 0.15); }
        body.theme-ice #panel { background: rgba(68, 187, 255, 0.04); border-color: rgba(68, 187, 255, 0.08); }
        body.theme-ice .ai-section { background: rgba(68, 187, 255, 0.02); border-color: rgba(68, 187, 255, 0.06); }
        body.theme-ice .header { border-bottom-color: rgba(68, 187, 255, 0.08); }

        body.theme-wine { background: #1a0508; color: #ff6677; }
        body.theme-wine .btn-primary { background: #ee3355; color: #1a0508; }
        body.theme-wine select:focus, body.theme-wine input:focus { border-color: #ee3355; box-shadow: 0 0 0 4px rgba(238, 51, 85, 0.15); }
        body.theme-wine #panel { background: rgba(238, 51, 85, 0.04); border-color: rgba(238, 51, 85, 0.08); }
        body.theme-wine .ai-section { background: rgba(238, 51, 85, 0.02); border-color: rgba(238, 51, 85, 0.06); }
        body.theme-wine .header { border-bottom-color: rgba(238, 51, 85, 0.08); }

        @media (max-width: 600px) {
            body { padding: 14px; }
            .header h1 { font-size: 20px; }
            .header h1 span.icon { font-size: 22px; }
            .btn { padding: 6px 16px; font-size: 13px; }
            .ai-section { padding: 16px; }
            #panel { padding: 16px; }
            .panel-grid { grid-template-columns: 1fr; }
            .modal { padding: 24px; }
            .chat-message { max-width: 95%; }
        }
    </style>
</head>
<body class="theme-neon">
    <div class="container">
        <header class="header">
            <h1>NeoBrain</h1>
            <div class="header-actions">
                <button class="btn btn-ghost" onclick="openShareModal()">Поделиться</button>
                <button class="btn btn-ghost" id="toggleBtn">Панель</button>
            </div>
        </header>

        <div id="panel">
            <div class="panel-grid">
                <div class="panel-section">
                    <div class="panel-section-title">Персонажи</div>
                    <div class="panel-row">
                        <select id="charSelect"></select>
                        <button class="btn btn-sm" id="addCharBtn">+</button>
                        <button class="btn btn-sm" id="randomCharBtn">🎲</button>
                        <button class="btn btn-sm btn-danger" id="deleteCharBtn">🗑</button>
                    </div>
                    <div class="panel-row">
                        <button class="btn btn-sm btn-success" id="exportCharsBtn">Экспорт</button>
                        <button class="btn btn-sm" id="importCharsBtn">Импорт</button>
                    </div>
                    <div id="charList"></div>
                </div>
                <div class="panel-section">
                    <div class="panel-section-title">Настройки</div>
                    <div class="panel-row">
                        <span style="opacity:0.5; font-size:13px;">🤖</span>
                        <select id="providerSelect">
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI</option>
                            <option value="gemini">Gemini</option>
                            <option value="claude">Claude</option>
                        </select>
                    </div>
                    <div class="panel-row" id="modelRow">
                        <span style="opacity:0.5; font-size:13px;">📦</span>
                        <select id="modelSelect">
                            <option value="qwen2.5-coder:1.5b">Быстрая</option>
                            <option value="llama3.2:3b">Средняя</option>
                            <option value="mistral:7b">Умная</option>
                            <option value="llama3.1:8b">Тяжёлая</option>
                        </select>
                        <span class="badge" id="modelStatus">✅</span>
                    </div>
                    <div class="panel-row" id="apiKeyRow" style="display:none;">
                        <span style="opacity:0.5; font-size:13px;">🔑</span>
                        <input type="password" id="apiKeyInput" placeholder="Введите API ключ...">
                        <button class="btn btn-sm btn-success" id="saveApiKeyBtn">Сохранить</button>
                        <span class="badge" id="apiKeyStatus">❌</span>
                    </div>
                    <div class="panel-row">
                        <span style="opacity:0.5; font-size:13px;">🎨</span>
                        <select id="themeSelect">
                            <option value="neon">Неон</option>
                            <option value="cyber">Киберпанк</option>
                            <option value="matrix">Матрица</option>
                            <option value="ocean">Океан</option>
                            <option value="sunset">Закат</option>
                            <option value="forest">Лес</option>
                            <option value="cosmos">Космос</option>
                            <option value="lava">Лава</option>
                            <option value="gold">Золото</option>
                            <option value="purple">Пурпур</option>
                            <option value="cherry">Вишня</option>
                            <option value="emerald">Изумруд</option>
                            <option value="sunny">Солнечная</option>
                            <option value="ice">Лёд</option>
                            <option value="wine">Вино</option>
                        </select>
                        <span class="badge" id="themeStatus">✅</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="ai-section">
            <h3>Общение с AI</h3>
            <div class="ai-controls">
                <span><span class="label">Провайдер:</span> <span id="providerDisplay">Ollama</span></span>
                <span><span class="label">Модель:</span> <span id="modelDisplay">qwen2.5-coder:1.5b</span></span>
            </div>
            <div class="ai-input-group">
                <input type="text" id="aiInput" placeholder="Напиши что-нибудь...">
                <button class="btn btn-primary" id="aiSendBtn">Отправить</button>
            </div>
            <div id="chatContainer"></div>
            <div id="aiOutput"></div>
        </div>

        <div id="status">Готов к работе...</div>
    </div>

    <div class="modal-overlay" id="shareModal" onclick="closeModalOutside(event)">
        <div class="modal">
            <h2>Поделиться доступом</h2>
            <p>Отправь эту ссылку друзьям в одной сети:</p>
            <div class="share-link">
                <span id="shareLinkText">Загрузка...</span>
                <button onclick="copyShareLink()">Копировать</button>
            </div>
            <p style="font-size:13px; opacity:0.6;">
                Друзья должны быть в одной Wi-Fi сети.<br>
                Если доступ не работает — проверь брандмауэр.
            </p>
            <button class="btn-close-modal" onclick="closeShareModal()">Закрыть</button>
        </div>
    </div>

    <script>
        // ============================================================
        // 1. ПАНЕЛЬ
        // ============================================================
        var toggleBtn = document.getElementById('toggleBtn');
        var panel = document.getElementById('panel');
        var panelOpen = false;
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function() {
                panelOpen = !panelOpen;
                panel.style.display = panelOpen ? 'block' : 'none';
                toggleBtn.textContent = panelOpen ? '▲' : '▼';
            });
        }

        // ============================================================
        // 2. ЧАТ (ИСТОРИЯ)
        // ============================================================
        var chatContainer = document.getElementById('chatContainer');
        var historyLoaded = false;

        function addMessageToChat(role, content) {
            var div = document.createElement('div');
            div.className = 'chat-message ' + role;
            var roleLabel = role === 'user' ? '👤 Вы' : '🧠 AI';
            div.innerHTML = '<div class="role">' + roleLabel + '</div>' + content;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Сохраняем историю
            if (historyLoaded) {
                saveMessageToHistory(role, content);
            }
        }

        function saveMessageToHistory(role, content) {
            var history = JSON.parse(localStorage.getItem('chat_history') || '[]');
            history.push({ role: role, content: content, timestamp: Date.now() });
            // Ограничиваем историю 100 сообщениями
            if (history.length > 100) {
                history = history.slice(-100);
            }
            localStorage.setItem('chat_history', JSON.stringify(history));
        }

        function loadHistoryFromLocal() {
            var history = JSON.parse(localStorage.getItem('chat_history') || '[]');
            if (history.length > 0) {
                chatContainer.innerHTML = '';
                history.forEach(function(msg) {
                    var div = document.createElement('div');
                    div.className = 'chat-message ' + msg.role;
                    var roleLabel = msg.role === 'user' ? '👤 Вы' : '🧠 AI';
                    div.innerHTML = '<div class="role">' + roleLabel + '</div>' + msg.content;
                    chatContainer.appendChild(div);
                });
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            historyLoaded = true;
        }

        // ============================================================
        // 3. ПОДЕЛИТЬСЯ
        // ============================================================
        function openShareModal() {
            document.getElementById('shareModal').classList.add('active');
            document.body.style.overflow = 'hidden';
            
            fetch('/get_ip')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('shareLinkText').textContent = 'http://' + data.ip + ':8000';
                })
                .catch(() => {
                    document.getElementById('shareLinkText').textContent = 'http://localhost:8000';
                });
        }

        function closeShareModal() {
            document.getElementById('shareModal').classList.remove('active');
            document.body.style.overflow = 'auto';
        }

        function closeModalOutside(e) {
            if (e.target === e.currentTarget) closeShareModal();
        }

        function copyShareLink() {
            var text = document.getElementById('shareLinkText').textContent;
            navigator.clipboard.writeText(text).then(() => {
                var status = document.getElementById('status');
                if (status) status.textContent = 'Ссылка скопирована!';
            }).catch(() => {
                var status = document.getElementById('status');
                if (status) status.textContent = 'Не удалось скопировать';
            });
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeShareModal();
        });

        // ============================================================
        // 4. ПРОВАЙДЕР И МОДЕЛЬ
        // ============================================================
        var currentProvider = 'ollama';
        var currentModel = 'qwen2.5-coder:1.5b';

        var providerSelect = document.getElementById('providerSelect');
        var modelSelect = document.getElementById('modelSelect');
        var modelStatus = document.getElementById('modelStatus');
        var modelDisplay = document.getElementById('modelDisplay');
        var providerDisplay = document.getElementById('providerDisplay');
        var apiKeyRow = document.getElementById('apiKeyRow');
        var apiKeyInput = document.getElementById('apiKeyInput');
        var saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
        var apiKeyStatus = document.getElementById('apiKeyStatus');

        var PROVIDER_NAMES = {
            'ollama': 'Ollama',
            'openai': 'OpenAI',
            'gemini': 'Google Gemini',
            'claude': 'Anthropic Claude'
        };

        var PROVIDER_MODELS = {
            'ollama': ['qwen2.5-coder:1.5b', 'llama3.2:3b', 'mistral:7b', 'llama3.1:8b'],
            'openai': ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4-turbo'],
            'gemini': ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash'],
            'claude': ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229']
        };

        function updateModelSelect(provider) {
            var models = PROVIDER_MODELS[provider] || ['qwen2.5-coder:1.5b'];
            modelSelect.innerHTML = '';
            models.forEach(function(model) {
                var option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
            var found = false;
            for (var i = 0; i < modelSelect.options.length; i++) {
                if (modelSelect.options[i].value === currentModel) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                modelSelect.value = models[0];
                currentModel = models[0];
            }
            updateDisplay();
        }

        function updateDisplay() {
            if (providerDisplay) providerDisplay.textContent = PROVIDER_NAMES[currentProvider] || currentProvider;
            if (modelDisplay) modelDisplay.textContent = currentModel;
            if (modelStatus) modelStatus.textContent = '✅ ' + currentModel;
            
            if (currentProvider === 'ollama') {
                apiKeyRow.style.display = 'none';
            } else {
                apiKeyRow.style.display = 'flex';
                checkApiKeyStatus();
            }
        }

        function checkApiKeyStatus() {
            var key = localStorage.getItem('api_key_' + currentProvider);
            if (key && key.length > 0) {
                apiKeyStatus.textContent = '✅ Указан';
                apiKeyStatus.style.color = '#51cf66';
            } else {
                apiKeyStatus.textContent = '❌ Не указан';
                apiKeyStatus.style.color = '#ff6b6b';
            }
        }

        if (providerSelect) {
            providerSelect.addEventListener('change', function() {
                currentProvider = this.value;
                updateModelSelect(currentProvider);
                updateDisplay();
            });
        }

        if (modelSelect) {
            modelSelect.addEventListener('change', function() {
                currentModel = this.value;
                updateDisplay();
            });
        }

        if (saveApiKeyBtn) {
            saveApiKeyBtn.addEventListener('click', function() {
                var key = apiKeyInput.value.trim();
                if (key) {
                    localStorage.setItem('api_key_' + currentProvider, key);
                    apiKeyInput.value = '';
                    checkApiKeyStatus();
                    var status = document.getElementById('status');
                    if (status) status.textContent = 'API ключ сохранён!';
                } else {
                    alert('Введите API ключ!');
                }
            });
        }

        // ============================================================
        // 5. ТЕМЫ
        // ============================================================
        var themeSelect = document.getElementById('themeSelect');
        var themeStatus = document.getElementById('themeStatus');
        var body = document.body;

        function switchTheme(theme) {
            body.className = 'theme-' + theme;
            localStorage.setItem('neobrain_theme', theme);
            if (themeStatus) themeStatus.textContent = '✅ ' + theme;
        }

        if (themeSelect) {
            var savedTheme = localStorage.getItem('neobrain_theme');
            if (savedTheme) {
                var found = false;
                for (var i = 0; i < themeSelect.options.length; i++) {
                    if (themeSelect.options[i].value === savedTheme) {
                        found = true;
                        break;
                    }
                }
                if (found) {
                    themeSelect.value = savedTheme;
                    body.className = 'theme-' + savedTheme;
                    if (themeStatus) themeStatus.textContent = '✅ ' + savedTheme;
                }
            }

            themeSelect.addEventListener('change', function() {
                switchTheme(this.value);
            });
        }

        // ============================================================
        // 6. ПЕРСОНАЖИ
        // ============================================================
        var characters = [];
        var STORAGE_CHARS = 'ai_chat_characters';

        var NAMES = {
            male: ['Алексей', 'Дмитрий', 'Максим', 'Артём', 'Иван', 'Сергей', 'Андрей', 'Егор', 'Никита', 'Михаил',
                'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles'
            ],
            female: ['Анна', 'Мария', 'Екатерина', 'Ольга', 'Татьяна', 'Наталья', 'Ирина', 'Светлана', 'Анастасия', 'Дарья',
                'Mary', 'Patricia', 'Jennifer', 'Linda', 'Barbara', 'Elizabeth', 'Susan', 'Jessica', 'Sarah', 'Karen'
            ]
        };

        function loadCharacters() {
            var saved = localStorage.getItem(STORAGE_CHARS);
            if (saved) {
                try {
                    characters = JSON.parse(saved);
                } catch(e) {
                    characters = [{ id: 'default', name: 'Помощник' }];
                }
            } else {
                characters = [{ id: 'default', name: 'Помощник' }];
            }
            saveCharacters();
            renderCharacterSelect();
            renderCharList();
        }

        function saveCharacters() {
            localStorage.setItem(STORAGE_CHARS, JSON.stringify(characters));
        }

        function renderCharacterSelect() {
            var select = document.getElementById('charSelect');
            if (!select) return;
            select.innerHTML = '';
            for (var i = 0; i < characters.length; i++) {
                var char = characters[i];
                var option = document.createElement('option');
                option.value = char.id;
                option.textContent = char.name;
                select.appendChild(option);
            }
            var status = document.getElementById('status');
            if (status) status.textContent = 'Загружено: ' + characters.length;
        }

        function renderCharList() {
            var container = document.getElementById('charList');
            if (!container) return;
            container.innerHTML = '';
            for (var i = 0; i < characters.length; i++) {
                var char = characters[i];
                var div = document.createElement('div');
                div.className = 'char-item';
                
                var nameSpan = document.createElement('span');
                nameSpan.className = 'char-name';
                nameSpan.textContent = char.name;
                div.appendChild(nameSpan);

                var actionsDiv = document.createElement('div');
                actionsDiv.className = 'char-actions';

                if (char.id !== 'default') {
                    var shareBtn = document.createElement('button');
                    shareBtn.className = 'char-share';
                    shareBtn.textContent = '📤';
                    shareBtn.title = 'Поделиться персонажем';
                    shareBtn.onclick = (function(id) {
                        return function(e) {
                            e.stopPropagation();
                            shareCharacter(id);
                        };
                    })(char.id);
                    actionsDiv.appendChild(shareBtn);

                    var delBtn = document.createElement('button');
                    delBtn.className = 'char-delete';
                    delBtn.textContent = '✖';
                    delBtn.title = 'Удалить';
                    delBtn.onclick = (function(id) {
                        return function(e) {
                            e.stopPropagation();
                            deleteCharacter(id);
                        };
                    })(char.id);
                    actionsDiv.appendChild(delBtn);
                }

                div.appendChild(actionsDiv);
                container.appendChild(div);
            }
        }

        function deleteCharacter(charId) {
            if (charId === 'default') {
                alert('Главный ИИ не может быть удалён!');
                return;
            }
            if (confirm('Удалить персонажа?')) {
                for (var i = 0; i < characters.length; i++) {
                    if (characters[i].id === charId) {
                        characters.splice(i, 1);
                        break;
                    }
                }
                saveCharacters();
                renderCharacterSelect();
                renderCharList();
                var status = document.getElementById('status');
                if (status) status.textContent = 'Персонаж удалён';
            }
        }

        function addCharacter(name) {
            var id = Date.now().toString();
            characters.push({ id: id, name: name });
            saveCharacters();
            renderCharacterSelect();
            renderCharList();
        }

        function shareCharacter(charId) {
            var char = characters.find(function(c) { return c.id === charId; });
            if (!char) return;
            
            var data = JSON.stringify(char, null, 2);
            var blob = new Blob([data], {type: 'application/json'});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = char.name.replace(/[^a-zA-Zа-яА-Я0-9]/g, '_') + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            var status = document.getElementById('status');
            if (status) status.textContent = 'Персонаж экспортирован!';
        }

        function exportCharacters() {
            var data = JSON.stringify(characters, null, 2);
            var blob = new Blob([data], {type: 'application/json'});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'neobrain_characters_' + new Date().toISOString().slice(0,10) + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            var status = document.getElementById('status');
            if (status) status.textContent = 'Экспортировано: ' + characters.length;
        }

        function importCharacters() {
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = function(e) {
                var file = e.target.files[0];
                if (!file) return;
                var reader = new FileReader();
                reader.onload = function(ev) {
                    try {
                        var imported = JSON.parse(ev.target.result);
                        if (!Array.isArray(imported)) {
                            alert('Неверный формат!');
                            return;
                        }
                        var hasDefault = imported.some(function(c) { return c.id === 'default'; });
                        if (!hasDefault) {
                            imported.unshift({ id: 'default', name: 'Помощник' });
                        }
                        characters = imported;
                        saveCharacters();
                        renderCharacterSelect();
                        renderCharList();
                        var status = document.getElementById('status');
                        if (status) status.textContent = 'Импортировано: ' + characters.length;
                        alert('Импортировано ' + characters.length + ' персонажей!');
                    } catch(err) {
                        alert('Ошибка: ' + err.message);
                    }
                };
                reader.readAsText(file);
            };
            input.click();
        }

        function generateRandomCharacter() {
            var existingNames = characters.map(function(char) {
                return char.name.replace(/[👨👩👤🤖]/g, '').trim();
            });
            var allNames = NAMES.male.concat(NAMES.female);
            var availableNames = allNames.filter(function(name) {
                return existingNames.indexOf(name) === -1;
            });
            if (availableNames.length === 0) {
                var status = document.getElementById('status');
                if (status) status.textContent = 'Все имена использованы!';
                return;
            }
            var randomIndex = Math.floor(Math.random() * availableNames.length);
            var selectedName = availableNames[randomIndex];
            var isMale = NAMES.male.indexOf(selectedName) !== -1;
            var isFemale = NAMES.female.indexOf(selectedName) !== -1;
            var genderIcon = isMale ? '👨' : isFemale ? '👩' : '👤';
            var fullName = genderIcon + ' ' + selectedName;
            addCharacter(fullName);
            var status = document.getElementById('status');
            if (status) status.textContent = 'Создан персонаж: ' + fullName;
        }

        var addCharBtn = document.getElementById('addCharBtn');
        if (addCharBtn) {
            addCharBtn.addEventListener('click', function() {
                var name = prompt('Введите имя персонажа:');
                if (name && name.trim()) {
                    var existing = characters.some(function(char) {
                        return char.name.replace(/[👨👩👤🤖]/g, '').trim().toLowerCase() === name.trim().toLowerCase();
                    });
                    if (existing) {
                        alert('Персонаж уже существует!');
                        return;
                    }
                    addCharacter('👤 ' + name.trim());
                    var status = document.getElementById('status');
                    if (status) status.textContent = 'Создан персонаж: ' + name.trim();
                }
            });
        }

        var randomCharBtn = document.getElementById('randomCharBtn');
        if (randomCharBtn) {
            randomCharBtn.addEventListener('click', function() {
                generateRandomCharacter();
            });
        }

        var deleteCharBtn = document.getElementById('deleteCharBtn');
        if (deleteCharBtn) {
            deleteCharBtn.addEventListener('click', function() {
                var select = document.getElementById('charSelect');
                if (select) {
                    deleteCharacter(select.value);
                }
            });
        }

        var exportCharsBtn = document.getElementById('exportCharsBtn');
        if (exportCharsBtn) {
            exportCharsBtn.addEventListener('click', exportCharacters);
        }

        var importCharsBtn = document.getElementById('importCharsBtn');
        if (importCharsBtn) {
            importCharsBtn.addEventListener('click', importCharacters);
        }

        // ============================================================
        // 7. ОТПРАВКА СООБЩЕНИЯ В AI
        // ============================================================
        var aiSendBtn = document.getElementById('aiSendBtn');
        if (aiSendBtn) {
            aiSendBtn.addEventListener('click', function() {
                var input = document.getElementById('aiInput');
                var output = document.getElementById('aiOutput');
                if (!input || !output) return;
                var text = input.value.trim();
                if (!text) return;

                var provider = currentProvider;
                var model = currentModel;

                // Показываем сообщение пользователя сразу
                addMessageToChat('user', text);
                input.value = '';

                // Показываем статус "печатает"
                var thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'chat-message ai';
                thinkingDiv.id = 'thinkingMessage';
                thinkingDiv.innerHTML = '<div class="role">🧠 AI</div>Думаю...';
                chatContainer.appendChild(thinkingDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;

                var apiKey = null;
                if (provider !== 'ollama') {
                    apiKey = localStorage.getItem('api_key_' + provider);
                    if (!apiKey || apiKey.length === 0) {
                        thinkingDiv.remove();
                        var errorDiv = document.createElement('div');
                        errorDiv.className = 'chat-message ai';
                        errorDiv.innerHTML = '<div class="role">🧠 AI</div>❌ API ключ не указан!';
                        chatContainer.appendChild(errorDiv);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                        return;
                    }
                }

                fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: text,
                        provider: provider,
                        model: model,
                        api_key: apiKey || ''
                    })
                })
                .then(function(response) {
                    if (!response.ok) throw new Error('Ошибка сети: ' + response.status);
                    return response.json();
                })
                .then(function(data) {
                    thinkingDiv.remove();
                    if (data.error) {
                        var errorDiv = document.createElement('div');
                        errorDiv.className = 'chat-message ai';
                        errorDiv.innerHTML = '<div class="role">🧠 AI</div>❌ ' + data.error;
                        chatContainer.appendChild(errorDiv);
                    } else {
                        addMessageToChat('ai', data.response || '⚠️ Ответ не получен');
                    }
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                })
                .catch(function(error) {
                    thinkingDiv.remove();
                    var errorDiv = document.createElement('div');
                    errorDiv.className = 'chat-message ai';
                    errorDiv.innerHTML = '<div class="role">🧠 AI</div>❌ Ошибка: ' + error.message;
                    chatContainer.appendChild(errorDiv);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                });
            });
        }

        var aiInput = document.getElementById('aiInput');
        if (aiInput) {
            aiInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    var btn = document.getElementById('aiSendBtn');
                    if (btn) btn.click();
                }
            });
        }

        // ============================================================
        // 8. ИНИЦИАЛИЗАЦИЯ
        // ============================================================
        document.addEventListener('DOMContentLoaded', function() {
            var savedProvider = localStorage.getItem('neobrain_provider');
            if (savedProvider && providerSelect) {
                var found = false;
                for (var i = 0; i < providerSelect.options.length; i++) {
                    if (providerSelect.options[i].value === savedProvider) {
                        found = true;
                        break;
                    }
                }
                if (found) {
                    providerSelect.value = savedProvider;
                    currentProvider = savedProvider;
                }
            }
            updateModelSelect(currentProvider);
            updateDisplay();
            loadCharacters();
            checkApiKeyStatus();
            loadHistoryFromLocal();
        });
    </script>
</body>
</html>
"""

# ============================================================
# API ЭНДПОИНТЫ
# ============================================================
@app.get("/")
async def home():
    return HTMLResponse(html_template)

@app.get("/get_ip")
async def get_ip():
    return {"ip": LOCAL_IP}

@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        prompt = data.get("prompt", "")
        provider = data.get("provider", "ollama")
        model = data.get("model", "qwen2.5-coder:1.5b")
        api_key = data.get("api_key", "")

        if provider == "ollama":
            return ask_ollama(prompt, model)
        elif provider == "openai":
            return ask_openai(prompt, api_key, model)
        elif provider == "gemini":
            return ask_gemini(prompt, api_key, model)
        elif provider == "claude":
            return ask_claude(prompt, api_key, model)
        else:
            return {"error": f"Неизвестный провайдер: {provider}"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    try:
        import webview
    except ImportError:
        print("Установи pywebview: python -m pip install pywebview")
        sys.exit(1)

    if not check_ollama():
        print("\n" + "=" * 55)
        print("Ollama не обнаружена!")
        print("Для работы с локальными моделями установите Ollama.")
        print("Скачайте: https://ollama.com")
        print("Или используйте облачные провайдеры в настройках.")
        print("=" * 55)
        print("\nЗапуск NeoBrain без Ollama... (доступны только облачные AI)")

    def run_server():
        uvicorn.run(app, host="0.0.0.0", port=8000)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(2)

    print("\n" + "=" * 55)
    print("NeoBrain запущен!")
    print("Открывается окно приложения...")
    print(f"Локальный адрес: http://{LOCAL_IP}:8000")
    print("Закрой окно приложения для остановки")
    print("=" * 55 + "\n")

    webview.create_window(
        'NeoBrain',
        'http://localhost:8000',
        width=1200,
        height=800,
        resizable=True,
        fullscreen=False,
        min_size=(800, 600)
    )
    webview.start()