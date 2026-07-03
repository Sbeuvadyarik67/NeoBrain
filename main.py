import os
import sys
import json
import requests
import socket
import webbrowser
import threading
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

# ============================================================
# ПРОВЕРКА OLLAMA
# ============================================================
def check_ollama():
    """Проверяет, запущена ли Ollama"""
    try:
        requests.get("http://localhost:11434/api/tags", timeout=3)
        return True
    except:
        return False

# ============================================================
# НАСТРОЙКИ
# ============================================================
CONFIG_FILE = "neobrain_config.json"

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "api_keys": {
                "openai": "",
                "gemini": "",
                "claude": ""
            },
            "default_provider": "ollama"
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
            return {"error": "Ollama не отвечает. Запустите 'ollama serve'"}
    except:
        return {"error": "Ollama не запущена. Запустите 'ollama serve'"}

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
        return {"response": result.get("response", "⚠️ Нет ответа от модели")}
    else:
        return {"error": f"Ошибка Ollama: {response.status_code}"}

def ask_openai(prompt, api_key, model="gpt-3.5-turbo"):
    if not api_key:
        return {"error": "❌ API ключ OpenAI не указан"}
    
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
            return {"error": f"Ошибка OpenAI: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка OpenAI: {str(e)}"}

def ask_gemini(prompt, api_key, model="gemini-pro"):
    if not api_key:
        return {"error": "❌ API ключ Google Gemini не указан"}
    
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
            return {"error": f"Ошибка Gemini: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка Gemini: {str(e)}"}

def ask_claude(prompt, api_key, model="claude-3-haiku-20240307"):
    if not api_key:
        return {"error": "❌ API ключ Anthropic Claude не указан"}
    
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
            return {"error": f"Ошибка Claude: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Ошибка Claude: {str(e)}"}

# ============================================================
# HTML ТЕМПЛЕЙТ (полный код из твоего файла)
# ============================================================
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeoBrain</title>
    <style>
        /* ============================================================
           БАЗА
           ============================================================ */
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

        /* ============================================================
           ОВЕРЛЕЙ
           ============================================================ */
        #fadeOverlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #000;
            z-index: 9999;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }

        #fadeOverlay.active {
            opacity: 0.5;
        }

        /* ============================================================
           ВСЕ ЭЛЕМЕНТЫ
           ============================================================ */
        .header, .header h1, .header-actions, .btn, select, input,
        #panel, .panel-section, .panel-row, #charList, .char-item,
        .ai-section, .ai-controls, #aiOutput, #status,
        .panel-section-title, .badge, .label {
            transition: all 1.5s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* ============================================================
           ШАПКА
           ============================================================ */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            padding: 16px 0 20px 0;
            border-bottom: 2px solid rgba(255, 255, 255, 0.06);
            margin-bottom: 24px;
            border-radius: 0 0 4px 4px;
        }

        .header h1 {
            font-size: 26px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -0.5px;
        }

        .header h1 span.icon {
            font-size: 28px;
        }

        .header-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        /* ============================================================
           КНОПКИ
           ============================================================ */
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
            transition: all 0.3s ease, 
                        background 1.5s cubic-bezier(0.4, 0, 0.2, 1),
                        color 1.5s cubic-bezier(0.4, 0, 0.2, 1),
                        border-color 1.5s cubic-bezier(0.4, 0, 0.2, 1),
                        box-shadow 1.5s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(4px);
        }

        .btn:hover {
            transform: translateY(-2px);
            filter: brightness(1.1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }

        .btn:active {
            transform: translateY(0px) scale(0.97);
        }

        .btn-primary {
            background: #00d4ff;
            color: #000;
        }

        .btn-primary:hover {
            filter: brightness(0.9);
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3);
        }

        .btn-danger {
            background: #ff6b6b;
            color: #000;
        }

        .btn-danger:hover {
            background: #ff5555;
            box-shadow: 0 4px 20px rgba(255, 107, 107, 0.25);
        }

        .btn-success {
            background: #51cf66;
            color: #000;
        }

        .btn-success:hover {
            background: #40c057;
            box-shadow: 0 4px 20px rgba(81, 207, 102, 0.25);
        }

        .btn-warning {
            background: #fcc419;
            color: #000;
        }

        .btn-warning:hover {
            background: #fab005;
            box-shadow: 0 4px 20px rgba(252, 196, 25, 0.25);
        }

        .btn-sm {
            padding: 6px 14px;
            font-size: 13px;
            border-radius: 10px;
        }

        .btn-ghost {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .btn-ghost:hover {
            background: rgba(255, 255, 255, 0.08);
        }

        /* ============================================================
           ПАНЕЛЬ
           ============================================================ */
        #panel {
            display: none;
            padding: 24px;
            margin-bottom: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(8px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
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

        .panel-row select {
            flex: 1;
            min-width: 120px;
        }

        .panel-row input[type="password"],
        .panel-row input[type="text"] {
            flex: 1;
            min-width: 150px;
        }

        /* ============================================================
           ПОЛЯ ВВОДА
           ============================================================ */
        select,
        input[type="text"],
        input[type="password"] {
            padding: 10px 16px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 14px;
            font-family: inherit;
            outline: none;
            transition: all 0.3s ease,
                        background 1.5s cubic-bezier(0.4, 0, 0.2, 1),
                        color 1.5s cubic-bezier(0.4, 0, 0.2, 1),
                        border-color 1.5s cubic-bezier(0.4, 0, 0.2, 1),
                        box-shadow 0.3s ease;
            backdrop-filter: blur(4px);
            background: rgba(255, 255, 255, 0.04);
            color: #d4e8ff;
        }

        select:focus,
        input[type="text"]:focus,
        input[type="password"]:focus {
            border-color: #00d4ff;
            box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.08);
            transform: scale(1.01);
        }

        select option {
            background: #1a1a2e;
            color: #eef5ff;
        }

        /* ============================================================
           СПИСОК ПЕРСОНАЖЕЙ
           ============================================================ */
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

        .char-name .emoji {
            font-size: 16px;
        }

        .char-delete {
            background: none;
            border: none;
            color: #ff6b6b;
            cursor: pointer;
            font-size: 15px;
            padding: 4px 8px;
            border-radius: 8px;
            opacity: 0.4;
            transition: all 0.3s ease;
        }

        .char-delete:hover {
            opacity: 1;
            background: rgba(255, 107, 107, 0.1);
            transform: scale(1.1);
        }

        /* ============================================================
           AI СЕКЦИЯ
           ============================================================ */
        .ai-section {
            padding: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(8px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
        }

        .ai-section h3 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
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
        }

        .ai-input-group input::placeholder {
            opacity: 0.4;
        }

        #aiOutput {
            margin-top: 16px;
            padding: 16px 20px;
            border-radius: 12px;
            min-height: 64px;
            border-left: 4px solid #00d4ff;
            font-size: 14px;
            white-space: pre-wrap;
            word-break: break-word;
            background: rgba(255, 255, 255, 0.02);
            transition: all 0.5s ease;
        }

        #aiOutput:empty::before {
            content: "Здесь будет ответ AI...";
            opacity: 0.3;
        }

        /* ============================================================
           СТАТУС
           ============================================================ */
        #status {
            margin-top: 16px;
            font-size: 13px;
            opacity: 0.5;
            padding: 8px 0;
            font-weight: 500;
            letter-spacing: 0.3px;
        }

        /* ============================================================
           ================ ЯРКИЕ ТЕМЫ ================
           ============================================================ */
        body.theme-neon { background: #0a0e1a; color: #d4e8ff; }
        body.theme-neon .btn-primary { background: #00d4ff; color: #0a0e1a; }
        body.theme-neon select:focus, body.theme-neon input:focus { border-color: #00d4ff; box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.15); }
        body.theme-neon #aiOutput { border-left-color: #00d4ff; }
        body.theme-neon #panel { background: rgba(0, 212, 255, 0.04); border-color: rgba(0, 212, 255, 0.08); }
        body.theme-neon .ai-section { background: rgba(0, 212, 255, 0.02); border-color: rgba(0, 212, 255, 0.06); }
        body.theme-neon .header { border-bottom-color: rgba(0, 212, 255, 0.08); }
        body.theme-neon .char-item { background: rgba(0, 212, 255, 0.03); }
        body.theme-neon .char-item:hover { background: rgba(0, 212, 255, 0.07); }
        body.theme-neon select, body.theme-neon input { background: rgba(255, 255, 255, 0.04); color: #d4e8ff; border-color: rgba(255, 255, 255, 0.08); }
        body.theme-neon select option { background: #0a0e1a; color: #d4e8ff; }
        body.theme-neon .ai-controls { background: rgba(0, 212, 255, 0.03); }

        body.theme-cyber { background: #0d0a1a; color: #ff66ff; }
        body.theme-cyber .btn-primary { background: #ff44ff; color: #0d0a1a; }
        body.theme-cyber select:focus, body.theme-cyber input:focus { border-color: #ff44ff; box-shadow: 0 0 0 4px rgba(255, 68, 255, 0.15); }
        body.theme-cyber #aiOutput { border-left-color: #ff44ff; }
        body.theme-cyber #panel { background: rgba(255, 68, 255, 0.04); border-color: rgba(255, 68, 255, 0.08); }
        body.theme-cyber .ai-section { background: rgba(255, 68, 255, 0.02); border-color: rgba(255, 68, 255, 0.06); }
        body.theme-cyber .header { border-bottom-color: rgba(255, 68, 255, 0.08); }
        body.theme-cyber select, body.theme-cyber input { background: rgba(255, 68, 255, 0.04); color: #ff66ff; border-color: rgba(255, 68, 255, 0.08); }
        body.theme-cyber select option { background: #0d0a1a; color: #ff66ff; }
        body.theme-cyber .ai-controls { background: rgba(255, 68, 255, 0.03); }

        body.theme-matrix { background: #0a0f0a; color: #66ff66; }
        body.theme-matrix .btn-primary { background: #44ff44; color: #0a0f0a; }
        body.theme-matrix select:focus, body.theme-matrix input:focus { border-color: #44ff44; box-shadow: 0 0 0 4px rgba(68, 255, 68, 0.15); }
        body.theme-matrix #aiOutput { border-left-color: #44ff44; }
        body.theme-matrix #panel { background: rgba(68, 255, 68, 0.04); border-color: rgba(68, 255, 68, 0.08); }
        body.theme-matrix .ai-section { background: rgba(68, 255, 68, 0.02); border-color: rgba(68, 255, 68, 0.06); }
        body.theme-matrix .header { border-bottom-color: rgba(68, 255, 68, 0.08); }
        body.theme-matrix select, body.theme-matrix input { background: rgba(68, 255, 68, 0.04); color: #66ff66; border-color: rgba(68, 255, 68, 0.08); }
        body.theme-matrix select option { background: #0a0f0a; color: #66ff66; }
        body.theme-matrix .ai-controls { background: rgba(68, 255, 68, 0.03); }

        body.theme-ocean { background: #0a1a2a; color: #66ddff; }
        body.theme-ocean .btn-primary { background: #44ccff; color: #0a1a2a; }
        body.theme-ocean select:focus, body.theme-ocean input:focus { border-color: #44ccff; box-shadow: 0 0 0 4px rgba(68, 204, 255, 0.15); }
        body.theme-ocean #aiOutput { border-left-color: #44ccff; }
        body.theme-ocean #panel { background: rgba(68, 204, 255, 0.04); border-color: rgba(68, 204, 255, 0.08); }
        body.theme-ocean .ai-section { background: rgba(68, 204, 255, 0.02); border-color: rgba(68, 204, 255, 0.06); }
        body.theme-ocean .header { border-bottom-color: rgba(68, 204, 255, 0.08); }
        body.theme-ocean select, body.theme-ocean input { background: rgba(68, 204, 255, 0.04); color: #66ddff; border-color: rgba(68, 204, 255, 0.08); }
        body.theme-ocean select option { background: #0a1a2a; color: #66ddff; }
        body.theme-ocean .ai-controls { background: rgba(68, 204, 255, 0.03); }

        body.theme-sunset { background: #1a0a0a; color: #ffaa88; }
        body.theme-sunset .btn-primary { background: #ff7744; color: #1a0a0a; }
        body.theme-sunset select:focus, body.theme-sunset input:focus { border-color: #ff7744; box-shadow: 0 0 0 4px rgba(255, 119, 68, 0.15); }
        body.theme-sunset #aiOutput { border-left-color: #ff7744; }
        body.theme-sunset #panel { background: rgba(255, 119, 68, 0.04); border-color: rgba(255, 119, 68, 0.08); }
        body.theme-sunset .ai-section { background: rgba(255, 119, 68, 0.02); border-color: rgba(255, 119, 68, 0.06); }
        body.theme-sunset .header { border-bottom-color: rgba(255, 119, 68, 0.08); }
        body.theme-sunset select, body.theme-sunset input { background: rgba(255, 119, 68, 0.04); color: #ffaa88; border-color: rgba(255, 119, 68, 0.08); }
        body.theme-sunset select option { background: #1a0a0a; color: #ffaa88; }
        body.theme-sunset .ai-controls { background: rgba(255, 119, 68, 0.03); }

        body.theme-forest { background: #0a1a0a; color: #88ff88; }
        body.theme-forest .btn-primary { background: #55ff55; color: #0a1a0a; }
        body.theme-forest select:focus, body.theme-forest input:focus { border-color: #55ff55; box-shadow: 0 0 0 4px rgba(85, 255, 85, 0.15); }
        body.theme-forest #aiOutput { border-left-color: #55ff55; }
        body.theme-forest #panel { background: rgba(85, 255, 85, 0.04); border-color: rgba(85, 255, 85, 0.08); }
        body.theme-forest .ai-section { background: rgba(85, 255, 85, 0.02); border-color: rgba(85, 255, 85, 0.06); }
        body.theme-forest .header { border-bottom-color: rgba(85, 255, 85, 0.08); }
        body.theme-forest select, body.theme-forest input { background: rgba(85, 255, 85, 0.04); color: #88ff88; border-color: rgba(85, 255, 85, 0.08); }
        body.theme-forest select option { background: #0a1a0a; color: #88ff88; }
        body.theme-forest .ai-controls { background: rgba(85, 255, 85, 0.03); }

        body.theme-cosmos { background: #05050f; color: #cc88ff; }
        body.theme-cosmos .btn-primary { background: #aa44ff; color: #05050f; }
        body.theme-cosmos select:focus, body.theme-cosmos input:focus { border-color: #aa44ff; box-shadow: 0 0 0 4px rgba(170, 68, 255, 0.15); }
        body.theme-cosmos #aiOutput { border-left-color: #aa44ff; }
        body.theme-cosmos #panel { background: rgba(170, 68, 255, 0.04); border-color: rgba(170, 68, 255, 0.08); }
        body.theme-cosmos .ai-section { background: rgba(170, 68, 255, 0.02); border-color: rgba(170, 68, 255, 0.06); }
        body.theme-cosmos .header { border-bottom-color: rgba(170, 68, 255, 0.08); }
        body.theme-cosmos select, body.theme-cosmos input { background: rgba(170, 68, 255, 0.04); color: #cc88ff; border-color: rgba(170, 68, 255, 0.08); }
        body.theme-cosmos select option { background: #05050f; color: #cc88ff; }
        body.theme-cosmos .ai-controls { background: rgba(170, 68, 255, 0.03); }

        body.theme-lava { background: #1a0a05; color: #ff8866; }
        body.theme-lava .btn-primary { background: #ff5533; color: #1a0a05; }
        body.theme-lava select:focus, body.theme-lava input:focus { border-color: #ff5533; box-shadow: 0 0 0 4px rgba(255, 85, 51, 0.15); }
        body.theme-lava #aiOutput { border-left-color: #ff5533; }
        body.theme-lava #panel { background: rgba(255, 85, 51, 0.04); border-color: rgba(255, 85, 51, 0.08); }
        body.theme-lava .ai-section { background: rgba(255, 85, 51, 0.02); border-color: rgba(255, 85, 51, 0.06); }
        body.theme-lava .header { border-bottom-color: rgba(255, 85, 51, 0.08); }
        body.theme-lava select, body.theme-lava input { background: rgba(255, 85, 51, 0.04); color: #ff8866; border-color: rgba(255, 85, 51, 0.08); }
        body.theme-lava select option { background: #1a0a05; color: #ff8866; }
        body.theme-lava .ai-controls { background: rgba(255, 85, 51, 0.03); }

        body.theme-gold { background: #1a1a0a; color: #ffdd88; }
        body.theme-gold .btn-primary { background: #ffcc44; color: #1a1a0a; }
        body.theme-gold select:focus, body.theme-gold input:focus { border-color: #ffcc44; box-shadow: 0 0 0 4px rgba(255, 204, 68, 0.15); }
        body.theme-gold #aiOutput { border-left-color: #ffcc44; }
        body.theme-gold #panel { background: rgba(255, 204, 68, 0.04); border-color: rgba(255, 204, 68, 0.08); }
        body.theme-gold .ai-section { background: rgba(255, 204, 68, 0.02); border-color: rgba(255, 204, 68, 0.06); }
        body.theme-gold .header { border-bottom-color: rgba(255, 204, 68, 0.08); }
        body.theme-gold select, body.theme-gold input { background: rgba(255, 204, 68, 0.04); color: #ffdd88; border-color: rgba(255, 204, 68, 0.08); }
        body.theme-gold select option { background: #1a1a0a; color: #ffdd88; }
        body.theme-gold .ai-controls { background: rgba(255, 204, 68, 0.03); }

        body.theme-purple { background: #0a0a1a; color: #dd88ff; }
        body.theme-purple .btn-primary { background: #cc44ff; color: #0a0a1a; }
        body.theme-purple select:focus, body.theme-purple input:focus { border-color: #cc44ff; box-shadow: 0 0 0 4px rgba(204, 68, 255, 0.15); }
        body.theme-purple #aiOutput { border-left-color: #cc44ff; }
        body.theme-purple #panel { background: rgba(204, 68, 255, 0.04); border-color: rgba(204, 68, 255, 0.08); }
        body.theme-purple .ai-section { background: rgba(204, 68, 255, 0.02); border-color: rgba(204, 68, 255, 0.06); }
        body.theme-purple .header { border-bottom-color: rgba(204, 68, 255, 0.08); }
        body.theme-purple select, body.theme-purple input { background: rgba(204, 68, 255, 0.04); color: #dd88ff; border-color: rgba(204, 68, 255, 0.08); }
        body.theme-purple select option { background: #0a0a1a; color: #dd88ff; }
        body.theme-purple .ai-controls { background: rgba(204, 68, 255, 0.03); }

        body.theme-cherry { background: #1a0a12; color: #ff88bb; }
        body.theme-cherry .btn-primary { background: #ff44aa; color: #1a0a12; }
        body.theme-cherry select:focus, body.theme-cherry input:focus { border-color: #ff44aa; box-shadow: 0 0 0 4px rgba(255, 68, 170, 0.15); }
        body.theme-cherry #aiOutput { border-left-color: #ff44aa; }
        body.theme-cherry #panel { background: rgba(255, 68, 170, 0.04); border-color: rgba(255, 68, 170, 0.08); }
        body.theme-cherry .ai-section { background: rgba(255, 68, 170, 0.02); border-color: rgba(255, 68, 170, 0.06); }
        body.theme-cherry .header { border-bottom-color: rgba(255, 68, 170, 0.08); }
        body.theme-cherry select, body.theme-cherry input { background: rgba(255, 68, 170, 0.04); color: #ff88bb; border-color: rgba(255, 68, 170, 0.08); }
        body.theme-cherry select option { background: #1a0a12; color: #ff88bb; }
        body.theme-cherry .ai-controls { background: rgba(255, 68, 170, 0.03); }

        body.theme-emerald { background: #0a1a0a; color: #66ffaa; }
        body.theme-emerald .btn-primary { background: #44ff88; color: #0a1a0a; }
        body.theme-emerald select:focus, body.theme-emerald input:focus { border-color: #44ff88; box-shadow: 0 0 0 4px rgba(68, 255, 136, 0.15); }
        body.theme-emerald #aiOutput { border-left-color: #44ff88; }
        body.theme-emerald #panel { background: rgba(68, 255, 136, 0.04); border-color: rgba(68, 255, 136, 0.08); }
        body.theme-emerald .ai-section { background: rgba(68, 255, 136, 0.02); border-color: rgba(68, 255, 136, 0.06); }
        body.theme-emerald .header { border-bottom-color: rgba(68, 255, 136, 0.08); }
        body.theme-emerald select, body.theme-emerald input { background: rgba(68, 255, 136, 0.04); color: #66ffaa; border-color: rgba(68, 255, 136, 0.08); }
        body.theme-emerald select option { background: #0a1a0a; color: #66ffaa; }
        body.theme-emerald .ai-controls { background: rgba(68, 255, 136, 0.03); }

        body.theme-sunny { background: #f5ede1; color: #3a2a1a; }
        body.theme-sunny .btn-primary { background: #d4a040; color: #f5ede1; }
        body.theme-sunny select:focus, body.theme-sunny input:focus { border-color: #d4a040; box-shadow: 0 0 0 4px rgba(212, 160, 64, 0.15); }
        body.theme-sunny #aiOutput { border-left-color: #d4a040; }
        body.theme-sunny #panel { background: rgba(212, 160, 64, 0.05); border-color: rgba(212, 160, 64, 0.1); }
        body.theme-sunny .ai-section { background: rgba(212, 160, 64, 0.03); border-color: rgba(212, 160, 64, 0.06); }
        body.theme-sunny .header { border-bottom-color: rgba(212, 160, 64, 0.1); }
        body.theme-sunny select, body.theme-sunny input { background: rgba(212, 160, 64, 0.05); color: #3a2a1a; border-color: rgba(212, 160, 64, 0.08); }
        body.theme-sunny select option { background: #f5ede1; color: #3a2a1a; }
        body.theme-sunny .ai-controls { background: rgba(212, 160, 64, 0.04); }

        body.theme-ice { background: #0a1a2a; color: #88ddff; }
        body.theme-ice .btn-primary { background: #44bbff; color: #0a1a2a; }
        body.theme-ice select:focus, body.theme-ice input:focus { border-color: #44bbff; box-shadow: 0 0 0 4px rgba(68, 187, 255, 0.15); }
        body.theme-ice #aiOutput { border-left-color: #44bbff; }
        body.theme-ice #panel { background: rgba(68, 187, 255, 0.04); border-color: rgba(68, 187, 255, 0.08); }
        body.theme-ice .ai-section { background: rgba(68, 187, 255, 0.02); border-color: rgba(68, 187, 255, 0.06); }
        body.theme-ice .header { border-bottom-color: rgba(68, 187, 255, 0.08); }
        body.theme-ice select, body.theme-ice input { background: rgba(68, 187, 255, 0.04); color: #88ddff; border-color: rgba(68, 187, 255, 0.08); }
        body.theme-ice select option { background: #0a1a2a; color: #88ddff; }
        body.theme-ice .ai-controls { background: rgba(68, 187, 255, 0.03); }

        body.theme-wine { background: #1a0508; color: #ff6677; }
        body.theme-wine .btn-primary { background: #ee3355; color: #1a0508; }
        body.theme-wine select:focus, body.theme-wine input:focus { border-color: #ee3355; box-shadow: 0 0 0 4px rgba(238, 51, 85, 0.15); }
        body.theme-wine #aiOutput { border-left-color: #ee3355; }
        body.theme-wine #panel { background: rgba(238, 51, 85, 0.04); border-color: rgba(238, 51, 85, 0.08); }
        body.theme-wine .ai-section { background: rgba(238, 51, 85, 0.02); border-color: rgba(238, 51, 85, 0.06); }
        body.theme-wine .header { border-bottom-color: rgba(238, 51, 85, 0.08); }
        body.theme-wine select, body.theme-wine input { background: rgba(238, 51, 85, 0.04); color: #ff6677; border-color: rgba(238, 51, 85, 0.08); }
        body.theme-wine select option { background: #1a0508; color: #ff6677; }
        body.theme-wine .ai-controls { background: rgba(238, 51, 85, 0.03); }

        /* ============================================================
           МОБИЛЬНАЯ АДАПТАЦИЯ
           ============================================================ */
        @media (max-width: 600px) {
            body { padding: 14px; }
            .header h1 { font-size: 20px; }
            .header h1 span.icon { font-size: 22px; }
            .btn { padding: 6px 16px; font-size: 13px; }
            .ai-section { padding: 16px; }
            #panel { padding: 16px; }
            .panel-grid { grid-template-columns: 1fr; }
            .ai-input-group input { min-width: 120px; }
            .ai-controls { flex-direction: column; gap: 6px; }
            .ai-section h3 { font-size: 18px; }
        }
    </style>
</head>
<body class="theme-neon">
    <!-- ОВЕРЛЕЙ ДЛЯ ПЛАВНОГО ПЕРЕКЛЮЧЕНИЯ -->
    <div id="fadeOverlay"></div>

    <div class="container">
        <div class="header">
            <h1>
                <span class="icon">🧠</span>
                NeoBrain
            </h1>
            <div class="header-actions">
                <button class="btn btn-ghost" id="toggleBtn">▼ Панель</button>
            </div>
        </div>

        <div id="panel">
            <div class="panel-grid">
                <div class="panel-section">
                    <div class="panel-section-title">👥 Персонажи</div>
                    <div class="panel-row">
                        <select id="charSelect"></select>
                        <button class="btn btn-sm" id="addCharBtn">➕</button>
                        <button class="btn btn-sm" id="randomCharBtn">🎲</button>
                        <button class="btn btn-sm btn-danger" id="deleteCharBtn">🗑</button>
                    </div>
                    <div class="panel-row">
                        <button class="btn btn-sm btn-success" id="exportCharsBtn">📤 Экспорт</button>
                        <button class="btn btn-sm btn-warning" id="importCharsBtn">📥 Импорт</button>
                    </div>
                    <div id="charList"></div>
                </div>
                <div class="panel-section">
                    <div class="panel-section-title">⚙️ Настройки</div>
                    <div class="panel-row">
                        <span style="opacity:0.5; font-size:13px;">🤖</span>
                        <select id="providerSelect">
                            <option value="ollama">🦙 Ollama (локально)</option>
                            <option value="openai">🤖 OpenAI</option>
                            <option value="gemini">🔵 Google Gemini</option>
                            <option value="claude">🟣 Anthropic Claude</option>
                        </select>
                    </div>
                    <div class="panel-row" id="modelRow">
                        <span style="opacity:0.5; font-size:13px;">📦</span>
                        <select id="modelSelect">
                            <option value="qwen2.5-coder:1.5b">⚡ Быстрая</option>
                            <option value="llama3.2:3b">🌿 Средняя</option>
                            <option value="mistral:7b">🧠 Умная</option>
                            <option value="llama3.1:8b">🔥 Тяжёлая</option>
                        </select>
                        <span class="badge" id="modelStatus">✅</span>
                    </div>
                    <div class="panel-row" id="apiKeyRow" style="display:none;">
                        <span style="opacity:0.5; font-size:13px;">🔑</span>
                        <input type="password" id="apiKeyInput" placeholder="Введите API ключ...">
                        <button class="btn btn-sm btn-success" id="saveApiKeyBtn">💾 Сохранить</button>
                        <span class="badge" id="apiKeyStatus">❌ Не указан</span>
                    </div>
                    <div class="panel-row">
                        <span style="opacity:0.5; font-size:13px;">🎨</span>
                        <select id="themeSelect">
                            <option value="neon">💠 Неон</option>
                            <option value="cyber">🌀 Киберпанк</option>
                            <option value="matrix">💚 Матрица</option>
                            <option value="ocean">🌊 Океан</option>
                            <option value="sunset">🌅 Закат</option>
                            <option value="forest">🌳 Лес</option>
                            <option value="cosmos">🌠 Космос</option>
                            <option value="lava">🌋 Лава</option>
                            <option value="gold">✨ Золото</option>
                            <option value="purple">🟣 Пурпур</option>
                            <option value="cherry">🌸 Вишня</option>
                            <option value="emerald">💎 Изумруд</option>
                            <option value="sunny">☀️ Солнечная</option>
                            <option value="ice">❄️ Лёд</option>
                            <option value="wine">🍷 Вино</option>
                        </select>
                        <span class="badge" id="themeStatus">✅</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="ai-section">
            <h3>🤖 Общение с AI</h3>
            <div class="ai-controls">
                <span><span class="label">Провайдер:</span> <span id="providerDisplay">🦙 Ollama</span></span>
                <span><span class="label">Модель:</span> <span id="modelDisplay">qwen2.5-coder:1.5b</span></span>
            </div>
            <div class="ai-input-group">
                <input type="text" id="aiInput" placeholder="Напиши что-нибудь...">
                <button class="btn btn-primary" id="aiSendBtn">➤ Отправить</button>
            </div>
            <div id="aiOutput"></div>
        </div>

        <div id="status">✨ Готов к работе...</div>
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
                toggleBtn.textContent = panelOpen ? '▲ Панель' : '▼ Панель';
            });
        }

        // ============================================================
        // 2. ПРОВАЙДЕР И МОДЕЛЬ
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
            'ollama': '🦙 Ollama',
            'openai': '🤖 OpenAI',
            'gemini': '🔵 Google Gemini',
            'claude': '🟣 Anthropic Claude'
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
            // Если текущая модель не в списке, ставим первую
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
            
            // Показываем/скрываем поле для API ключа
            if (currentProvider === 'ollama') {
                apiKeyRow.style.display = 'none';
            } else {
                apiKeyRow.style.display = 'flex';
                // Проверяем, есть ли ключ
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

        // Сохранение API ключа
        if (saveApiKeyBtn) {
            saveApiKeyBtn.addEventListener('click', function() {
                var key = apiKeyInput.value.trim();
                if (key) {
                    localStorage.setItem('api_key_' + currentProvider, key);
                    apiKeyInput.value = '';
                    checkApiKeyStatus();
                    var status = document.getElementById('status');
                    if (status) status.textContent = '✅ API ключ для ' + PROVIDER_NAMES[currentProvider] + ' сохранён!';
                } else {
                    alert('Введите API ключ!');
                }
            });
        }

        // ============================================================
        // 3. ПЛАВНОЕ ПЕРЕКЛЮЧЕНИЕ ТЕМ
        // ============================================================
        var themeSelect = document.getElementById('themeSelect');
        var themeStatus = document.getElementById('themeStatus');
        var overlay = document.getElementById('fadeOverlay');
        var body = document.body;
        var isChanging = false;

        function switchTheme(theme) {
            if (isChanging) return;
            isChanging = true;

            overlay.classList.add('active');

            setTimeout(function() {
                body.className = 'theme-' + theme;
                localStorage.setItem('neobrain_theme', theme);
                if (themeStatus) themeStatus.textContent = '✅ ' + theme;

                setTimeout(function() {
                    overlay.classList.remove('active');
                    
                    setTimeout(function() {
                        isChanging = false;
                    }, 200);
                }, 400);
            }, 600);
        }

        // Инициализация темы
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
                var newTheme = this.value;
                switchTheme(newTheme);
            });
        }

        // ============================================================
        // 4. ПЕРСОНАЖИ
        // ============================================================
        var characters = [];
        var STORAGE_CHARS = 'ai_chat_characters';

        var NAMES = {
            male: [
                'Алексей', 'Дмитрий', 'Максим', 'Артём', 'Иван', 'Сергей', 'Андрей', 'Егор', 'Никита', 'Михаил',
                'Владимир', 'Александр', 'Павел', 'Виктор', 'Василий', 'Григорий', 'Евгений', 'Игорь', 'Леонид', 'Олег',
                'Станислав', 'Юрий', 'Ярослав', 'Борис', 'Глеб', 'Даниил', 'Захар', 'Илья', 'Кирилл', 'Константин',
                'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles',
                'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Mark', 'Donald', 'Steven', 'Paul', 'Andrew', 'Joshua'
            ],
            female: [
                'Анна', 'Мария', 'Екатерина', 'Ольга', 'Татьяна', 'Наталья', 'Ирина', 'Светлана', 'Анастасия', 'Дарья',
                'Елена', 'Александра', 'Людмила', 'Галина', 'Валентина', 'Ксения', 'Полина', 'Вероника', 'София', 'Арина',
                'Кира', 'Милана', 'Алиса', 'Алина', 'Виктория', 'Елизавета', 'Марина', 'Надежда', 'Раиса', 'Зоя',
                'Mary', 'Patricia', 'Jennifer', 'Linda', 'Barbara', 'Elizabeth', 'Susan', 'Jessica', 'Sarah', 'Karen',
                'Lisa', 'Nancy', 'Betty', 'Margaret', 'Sandra', 'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle'
            ]
        };

        function loadCharacters() {
            var saved = localStorage.getItem(STORAGE_CHARS);
            if (saved) {
                try {
                    characters = JSON.parse(saved);
                } catch(e) {
                    characters = [{ id: 'default', name: '🤖 Помощник' }];
                }
            } else {
                characters = [{ id: 'default', name: '🤖 Помощник' }];
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
            if (status) status.textContent = '✅ Загружено персонажей: ' + characters.length;
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

                if (char.id !== 'default') {
                    var delBtn = document.createElement('button');
                    delBtn.className = 'char-delete';
                    delBtn.textContent = '✖';
                    delBtn.title = 'Удалить';
                    delBtn.onclick = (function(id) {
                        return function() {
                            deleteCharacter(id);
                        };
                    })(char.id);
                    div.appendChild(delBtn);
                }
                container.appendChild(div);
            }
        }

        function deleteCharacter(charId) {
            if (charId === 'default') {
                alert('🧠 Главный ИИ не может быть удалён!');
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
                if (status) status.textContent = '🗑 Персонаж удалён';
            }
        }

        function addCharacter(name) {
            var id = Date.now().toString();
            characters.push({ id: id, name: name });
            saveCharacters();
            renderCharacterSelect();
            renderCharList();
        }

        // ============================================================
        // ЭКСПОРТ/ИМПОРТ ПЕРСОНАЖЕЙ
        // ============================================================
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
            if (status) status.textContent = '📤 Экспортировано персонажей: ' + characters.length;
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
                            alert('❌ Неверный формат файла!');
                            return;
                        }
                        // Проверяем, есть ли персонаж с id 'default'
                        var hasDefault = imported.some(function(c) { return c.id === 'default'; });
                        if (!hasDefault) {
                            imported.unshift({ id: 'default', name: '🤖 Помощник' });
                        }
                        characters = imported;
                        saveCharacters();
                        renderCharacterSelect();
                        renderCharList();
                        var status = document.getElementById('status');
                        if (status) status.textContent = '📥 Импортировано персонажей: ' + characters.length;
                        alert('✅ Импортировано ' + characters.length + ' персонажей!');
                    } catch(err) {
                        alert('❌ Ошибка при импорте: ' + err.message);
                    }
                };
                reader.readAsText(file);
            };
            input.click();
        }

        // ============================================================
        // ГЕНЕРАЦИЯ СЛУЧАЙНОГО ПЕРСОНАЖА
        // ============================================================
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
                if (status) status.textContent = '⚠️ Все имена уже использованы! Удалите несколько персонажей.';
                return;
            }

            var randomIndex = Math.floor(Math.random() * availableNames.length);
            var selectedName = availableNames[randomIndex];

            var isMale = NAMES.male.indexOf(selectedName) !== -1;
            var isFemale = NAMES.female.indexOf(selectedName) !== -1;
            
            var genderIcon;
            if (isMale) {
                genderIcon = '👨';
            } else if (isFemale) {
                genderIcon = '👩';
            } else {
                genderIcon = '👤';
            }

            var fullName = genderIcon + ' ' + selectedName;
            addCharacter(fullName);
            
            var status = document.getElementById('status');
            if (status) status.textContent = '🎲 Создан персонаж: ' + fullName;
        }

        // ============================================================
        // ОБРАБОТЧИКИ КНОПОК
        // ============================================================
        var addCharBtn = document.getElementById('addCharBtn');
        if (addCharBtn) {
            addCharBtn.addEventListener('click', function() {
                var name = prompt('Введите имя персонажа:');
                if (name && name.trim()) {
                    var existing = characters.some(function(char) {
                        return char.name.replace(/[👨👩👤🤖]/g, '').trim().toLowerCase() === name.trim().toLowerCase();
                    });
                    
                    if (existing) {
                        alert('⚠️ Персонаж с таким именем уже существует!');
                        return;
                    }
                    
                    addCharacter('👤 ' + name.trim());
                    var status = document.getElementById('status');
                    if (status) status.textContent = '✅ Создан персонаж: ' + name.trim();
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
                    var id = select.value;
                    deleteCharacter(id);
                }
            });
        }

        // Экспорт/Импорт
        var exportCharsBtn = document.getElementById('exportCharsBtn');
        if (exportCharsBtn) {
            exportCharsBtn.addEventListener('click', exportCharacters);
        }

        var importCharsBtn = document.getElementById('importCharsBtn');
        if (importCharsBtn) {
            importCharsBtn.addEventListener('click', importCharacters);
        }

        // ============================================================
        // 5. ОТПРАВКА СООБЩЕНИЯ В AI
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

                output.textContent = '⏳ Думаю... (' + provider + '/' + model + ')';
                input.disabled = true;

                // Для облачных провайдеров — берём API ключ из localStorage
                var apiKey = null;
                if (provider !== 'ollama') {
                    apiKey = localStorage.getItem('api_key_' + provider);
                    if (!apiKey || apiKey.length === 0) {
                        output.textContent = '❌ API ключ для ' + PROVIDER_NAMES[provider] + ' не указан!';
                        input.disabled = false;
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
                    if (data.error) {
                        output.textContent = '❌ ' + data.error;
                    } else {
                        output.textContent = data.response || '⚠️ Ответ не получен';
                    }
                    input.disabled = false;
                    input.value = '';
                })
                .catch(function(error) {
                    output.textContent = '❌ Ошибка: ' + error.message;
                    input.disabled = false;
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
        // 6. ИНИЦИАЛИЗАЦИЯ
        // ============================================================
        document.addEventListener('DOMContentLoaded', function() {
            // Загружаем сохранённый провайдер
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
            
            // Инициализируем модель
            updateModelSelect(currentProvider);
            updateDisplay();
            loadCharacters();

            // Проверяем статус API ключа
            checkApiKeyStatus();
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
            return {"error": f"❌ Неизвестный провайдер: {provider}"}

    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    import uvicorn

    # Проверяем Ollama
    if not check_ollama():
        print("\n" + "=" * 55)
        print("⚠️  Ollama не обнаружена!")
        print("Для работы NeoBrain нужно установить Ollama.")
        print("📥 Скачайте: https://ollama.com")
        print("После установки перезапустите NeoBrain.")
        print("=" * 55)
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    # Открываем браузер автоматически
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"

    print("\n" + "=" * 55)
    print("🧠 NeoBrain запущен!")
    print("📌 Открывается браузер...")
    print(f"   → http://localhost:8000")
    print("📦 Поддерживаемые провайдеры:")
    print("   🦙 Ollama (локально)")
    print("   🤖 OpenAI (GPT-3.5, GPT-4)")
    print("   🔵 Google Gemini")
    print("   🟣 Anthropic Claude")
    print("\n⏹️  Для остановки нажми Ctrl+C")
    print("=" * 55 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)