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
import subprocess
import signal
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

# ============================================================
# НАСТРОЙКА КОДИРОВКИ ДЛЯ WINDOWS
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')
    except:
        pass

# ============================================================
# ОТКЛЮЧАЕМ ВЫВОД В КОНСОЛЬ (НО ЛОГИ СОХРАНЯЕМ)
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
# СЛОВАРЬ СЛЕНГА
# ============================================================
SLANG_FILE = "slang_dict.json"
PENDING_FILE = "pending_words.txt"
LAST_RUN_FILE = "last_run.txt"

def load_slang():
    if os.path.exists(SLANG_FILE):
        try:
            with open(SLANG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_slang(slang):
    with open(SLANG_FILE, 'w', encoding='utf-8') as f:
        json.dump(slang, f, indent=2, ensure_ascii=False)

def add_pending_word(word):
    with open(PENDING_FILE, 'a', encoding='utf-8') as f:
        f.write(word.strip() + "\n")

def get_pending_words():
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        return [w.strip() for w in f.readlines() if w.strip()]

def clear_pending():
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)

def should_run_agent():
    if not os.path.exists(LAST_RUN_FILE):
        return True
    try:
        with open(LAST_RUN_FILE, 'r') as f:
            last = float(f.read())
        return (time.time() - last) > 2 * 60 * 60
    except:
        return True

def update_last_run():
    with open(LAST_RUN_FILE, 'w') as f:
        f.write(str(time.time()))

slang_dict = load_slang()

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

def get_local_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

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
# АВТОЗАПУСК OLLAMA
# ============================================================
def is_ollama_running():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False

def start_ollama():
    print("🔄 Запуск Ollama...")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        return True
    except FileNotFoundError:
        print("❌ Ollama не найдена в системе!")
        print("📥 Скачайте: https://ollama.com")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске Ollama: {e}")
        return False

# ============================================================
# AI ПРОВАЙДЕРЫ
# ============================================================
def ask_ollama(prompt, model, system_prompt=""):
    try:
        check = requests.get("http://localhost:11434/api/tags", timeout=3)
        if check.status_code != 200:
            return {"error": "Ollama не отвечает"}
    except:
        return {"error": "Ollama не запущена"}

    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\nЗапрос пользователя: {prompt}"

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": full_prompt,
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

def ask_openai(prompt, api_key, model="gpt-3.5-turbo", system_prompt=""):
    if not api_key:
        return {"error": "API ключ OpenAI не указан"}
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
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

def ask_gemini(prompt, api_key, model="gemini-pro", system_prompt=""):
    if not api_key:
        return {"error": "API ключ Google Gemini не указан"}
    
    try:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{full_prompt}"
            
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": full_prompt}]}]
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

def ask_claude(prompt, api_key, model="claude-3-haiku-20240307", system_prompt=""):
    if not api_key:
        return {"error": "API ключ Anthropic Claude не указан"}
    
    try:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{full_prompt}"
            
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
                "messages": [{"role": "user", "content": full_prompt}]
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

def process_pending_words():
    pending = get_pending_words()
    if not pending:
        return
    
    print(f"🔄 Обработка {len(pending)} новых слов...")
    
    for word in pending:
        try:
            if word not in slang_dict:
                slang_dict[word] = "Новое слово (ожидает проверки)"
                print(f"  ➕ Добавлено: {word}")
        except:
            pass
    
    save_slang(slang_dict)
    clear_pending()
    update_last_run()
    print("✅ Словарь обновлён")

# ============================================================
# HTML ТЕМПЛЕЙТ С ЛОКАЛИЗАЦИЕЙ И КОПИРОВАНИЕМ
# ============================================================
html_template = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeoBrain</title>
    <style>
    /* ===== СТИЛИ ДЛЯ ВЫПАДАЮЩИХ СПИСКОВ ===== */
select, .panel-row select, #themeSelect, #languageSelect, #providerSelect, #modelSelect {
    background-color: #1a1f35 !important;
    color: #e0f0ff !important;
    border: 1px solid rgba(0, 212, 255, 0.15) !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    outline: none !important;
    appearance: none !important;
    -webkit-appearance: none !important;
    cursor: pointer !important;
}

select:hover, .panel-row select:hover {
    border-color: rgba(0, 212, 255, 0.3) !important;
}

select:focus, .panel-row select:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1) !important;
}

/* Стили для опций внутри select */
select option {
    background-color: #0a0e1a !important;
    color: #e0f0ff !important;
    padding: 8px !important;
}

select option:hover {
    background-color: #1a2a4a !important;
}

/* Для темных тем в themeSelect (особый случай) */
#themeSelect {
    background-color: #1a1f35 !important;
    color: #e0f0ff !important;
}

#themeSelect option {
    background-color: #0a0e1a !important;
    color: #e0f0ff !important;
}
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; padding: 20px; min-height: 100vh; background: #0a0e1a; color: #e8f0ff; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; padding: 16px 0 20px 0; border-bottom: 2px solid rgba(0, 212, 255, 0.15); margin-bottom: 24px; }
        .header h1 { font-size: 26px; font-weight: 700; background: linear-gradient(135deg, #00d4ff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .btn { padding: 8px 20px; border: none; border-radius: 12px; font-weight: 600; font-size: 14px; cursor: pointer; background: rgba(255,255,255,0.04); color: #d4e8ff; transition: all 0.3s ease; }
        .btn:hover { transform: translateY(-2px); filter: brightness(1.1); }
        .btn-primary { background: #00d4ff; color: #0a0e1a; }
        .btn-primary:hover { background: #33ddff; }
        .btn-ghost { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }
        .btn-ghost:hover { background: rgba(255,255,255,0.08); }
        .btn-sm { padding: 6px 14px; font-size: 13px; border-radius: 10px; }
        .btn-success { background: #51cf66; color: #0a0e1a; }
        .btn-danger { background: #ff6b6b; color: #0a0e1a; }
        #panel { display: none; padding: 24px; margin-bottom: 24px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06); background: rgba(0,212,255,0.02); }
        .panel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
        @media (max-width: 700px) { .panel-grid { grid-template-columns: 1fr; gap: 20px; } }
        .panel-section { display: flex; flex-direction: column; gap: 12px; }
        .panel-section-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; opacity: 0.4; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 4px; }
        .panel-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
        .panel-row select, .panel-row input { flex: 1; min-width: 120px; padding: 10px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); font-size: 14px; background: rgba(255,255,255,0.04); color: #d4e8ff; outline: none; }
        .panel-row select:focus, .panel-row input:focus { border-color: #00d4ff; box-shadow: 0 0 0 4px rgba(0,212,255,0.08); }
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input { display: none; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #444; transition: 0.3s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background: white; transition: 0.3s; border-radius: 50%; }
        input:checked + .slider { background: #00d4ff; }
        input:checked + .slider:before { transform: translateX(20px); }
        #cringeSlider { width: 200px; height: 8px; accent-color: #ff44ff; background: linear-gradient(to right, #00d4ff, #ff44ff, #ff0000); border-radius: 10px; }
        #chatContainer { max-height: 400px; overflow-y: auto; padding: 12px; border-radius: 12px; background: rgba(255,255,255,0.02); margin-bottom: 12px; }
        .chat-message { padding: 10px 16px; margin-bottom: 8px; border-radius: 12px; max-width: 85%; word-break: break-word; }
        .chat-message.user { background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.1); margin-left: auto; text-align: right; }
        .chat-message.ai { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); margin-right: auto; }
        .chat-message .role { font-size: 12px; opacity: 0.5; margin-bottom: 4px; }
        .ai-input-group { display: flex; gap: 12px; flex-wrap: wrap; }
        .ai-input-group input { flex: 1; min-width: 180px; padding: 10px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); font-size: 14px; background: rgba(255,255,255,0.04); color: #d4e8ff; outline: none; }
        #status { margin-top: 16px; font-size: 13px; opacity: 0.5; padding: 8px 0; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); z-index: 9999; justify-content: center; align-items: center; padding: 20px; }
        .modal-overlay.active { display: flex; }
        .modal { background: #111827; border: 1px solid rgba(0,212,255,0.15); border-radius: 20px; padding: 40px; max-width: 500px; width: 100%; }
        .modal h2 { font-size: 24px; font-weight: 700; color: #e0f0ff; margin-bottom: 8px; background: linear-gradient(135deg, #00d4ff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .modal p { color: #88bbdd; margin-bottom: 16px; }
        .modal .share-link { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; font-family: monospace; font-size: 14px; color: #00d4ff; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .modal .share-link button { background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.2); border-radius: 8px; color: #00d4ff; padding: 6px 14px; cursor: pointer; font-size: 13px; }
        .modal .btn-close-modal { width: 100%; padding: 12px; border: none; border-radius: 12px; background: rgba(255,255,255,0.04); color: #88bbdd; font-size: 14px; cursor: pointer; }
        #charList { display: flex; flex-direction: column; gap: 6px; max-height: 160px; overflow-y: auto; }
        .char-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; border-radius: 10px; font-size: 14px; }
        .char-item:hover { background: rgba(255,255,255,0.06); }
        .char-actions { display: flex; gap: 6px; }
        .char-actions button { background: none; border: none; cursor: pointer; font-size: 14px; padding: 4px 8px; border-radius: 8px; opacity: 0.5; }
        .char-actions button:hover { opacity: 1; background: rgba(255,255,255,0.06); }
        .char-delete { color: #ff6b6b; }
        .char-share { color: #00d4ff; }
        .ai-section { padding: 24px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); display: flex; flex-direction: column; min-height: 500px; }
        .ai-section h3 { font-size: 20px; font-weight: 600; margin-bottom: 16px; color: #e0f0ff; }
        .ai-controls { display: flex; flex-wrap: wrap; gap: 12px 24px; margin-bottom: 16px; font-size: 14px; padding: 12px 16px; border-radius: 12px; background: rgba(255,255,255,0.02); }
        .ai-controls .label { opacity: 0.5; font-weight: 500; }
        #styleSelector { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.92); z-index: 10000; align-items: center; justify-content: center; flex-direction: column; gap: 20px; }
        #styleSelector.active { display: flex; }
        .style-btn { padding: 20px 40px; border-radius: 16px; border: 2px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); color: #d4e8ff; cursor: pointer; font-size: 18px; transition: all 0.3s ease; }
        .style-btn:hover { background: rgba(0,212,255,0.1); border-color: #00d4ff; transform: scale(1.02); }
        body.style-minimal { --radius: 4px; }
        body.style-minimal .btn { border-radius: 4px; }
        body.style-minimal .ai-section { border-radius: 4px; }
        body.style-vibes { --radius: 20px; --shadow: 0 8px 40px rgba(0,212,255,0.05); }
        body.style-vibes .btn { border-radius: 20px; box-shadow: 0 4px 20px rgba(0,212,255,0.1); }
        body.style-vibes .header { border-bottom: none; background: rgba(0,212,255,0.02); border-radius: 20px; padding: 20px; }
        body.style-vibes .ai-section { border-radius: 20px; background: rgba(255,255,255,0.03); }
        body.style-cyber { --radius: 0px; }
        body.style-cyber .btn { border-radius: 0px; border: 1px solid #00d4ff; background: transparent; color: #00d4ff; }
        body.style-cyber .btn-primary { background: #00d4ff; color: #000; }
        body.style-cyber .header { border-bottom: 2px solid #00d4ff; }
        body.style-cyber .ai-section { border-radius: 0px; border: 1px solid rgba(0,212,255,0.2); }
        body.style-cyber * { font-family: 'Courier New', monospace !important; }
        body.style-cloudy { --radius: 16px; --shadow: 0 4px 20px rgba(0,0,0,0.06); background: #f1f5f9; color: #1e293b; }
        body.style-cloudy .header { background: #ffffff; border-radius: var(--radius); border-bottom: none; box-shadow: var(--shadow); padding: 16px 24px; }
        body.style-cloudy .header h1 { background: none; -webkit-text-fill-color: #1e293b; color: #1e293b; }
        body.style-cloudy .btn { border-radius: var(--radius); background: #f1f5f9; color: #1e293b; border: none; }
        body.style-cloudy .btn:hover { background: #e2e8f0; }
        body.style-cloudy .btn-primary { background: #3b82f6; color: #ffffff; }
        body.style-cloudy .btn-primary:hover { background: #2563eb; }
        body.style-cloudy .btn-ghost { background: transparent; border: 1px solid #e2e8f0; color: #1e293b; }
        body.style-cloudy .btn-ghost:hover { background: #f1f5f9; }
        body.style-cloudy #panel { background: #ffffff; border-radius: var(--radius); border: none; box-shadow: var(--shadow); }
        body.style-cloudy .ai-section { background: #ffffff; border-radius: var(--radius); border: none; box-shadow: var(--shadow); }
        body.style-cloudy .ai-section h3 { color: #1e293b; }
        body.style-cloudy select, body.style-cloudy input { background: #f8fafc; color: #1e293b; border: 1px solid #e2e8f0; border-radius: var(--radius); }
        body.style-cloudy select:focus, body.style-cloudy input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
        body.style-cloudy #chatContainer { background: #f8fafc; border-radius: var(--radius); }
        body.style-cloudy .chat-message.user { background: #3b82f6; color: #ffffff; border: none; }
        body.style-cloudy .chat-message.ai { background: #f1f5f9; color: #1e293b; border: none; }
        body.style-cloudy #status { color: #64748b; }
        body.style-cloudy .modal { background: #ffffff; border: none; box-shadow: 0 20px 60px rgba(0,0,0,0.1); }
        body.style-cloudy .modal h2 { background: none; -webkit-text-fill-color: #1e293b; color: #1e293b; }
        body.style-cloudy .modal .share-link { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: var(--radius); color: #3b82f6; }
        body.style-cloudy .modal .share-link button { background: #e2e8f0; color: #1e293b; border: none; }
        body.style-cloudy .modal .share-link button:hover { background: #cbd5e1; }
        body.style-cloudy .modal .btn-close-modal { background: #f1f5f9; color: #1e293b; }
        body.style-cloudy .modal .btn-close-modal:hover { background: #e2e8f0; }
        body.style-cloudy .char-item { background: #f8fafc; border-radius: var(--radius); }
        body.style-cloudy .char-item:hover { background: #f1f5f9; }
        body.style-cloudy .char-name { color: #1e293b; }
        body.style-cloudy .char-share { color: #3b82f6; }
        body.style-cloudy .char-delete { color: #ef4444; }
        body.style-cloudy .switch .slider { background: #cbd5e1; }
        body.style-cloudy input:checked + .slider { background: #3b82f6; }
        body.style-cloudy #cringeLabel { color: #3b82f6 !important; }
        body.style-cloudy .badge { color: #64748b; }
        body.style-cloudy .footer { border-top-color: #e2e8f0; color: #94a3b8; }
        body.style-cloudy .neon-line { background: linear-gradient(90deg, transparent, #3b82f6, transparent); }
        @media (max-width: 600px) { body { padding: 14px; } .panel-grid { grid-template-columns: 1fr; } .modal { padding: 24px; } }
        body.theme-neon { background: #0a0e1a; color: #d4e8ff; }
        body.theme-neon .btn-primary { background: #00d4ff; color: #0a0e1a; }
        body.theme-neon #panel { background: rgba(0,212,255,0.04); border-color: rgba(0,212,255,0.08); }
        body.theme-neon .ai-section { background: rgba(0,212,255,0.02); border-color: rgba(0,212,255,0.06); }
        body.theme-neon .header { border-bottom-color: rgba(0,212,255,0.08); }
        body.theme-cyber { background: #0d0a1a; color: #ff66ff; }
        body.theme-cyber .btn-primary { background: #ff44ff; color: #0d0a1a; }
        body.theme-cyber #panel { background: rgba(255,68,255,0.04); border-color: rgba(255,68,255,0.08); }
        body.theme-cyber .ai-section { background: rgba(255,68,255,0.02); border-color: rgba(255,68,255,0.06); }
        body.theme-cyber .header { border-bottom-color: rgba(255,68,255,0.08); }
        body.theme-matrix { background: #0a0f0a; color: #66ff66; }
        body.theme-matrix .btn-primary { background: #44ff44; color: #0a0f0a; }
        body.theme-matrix #panel { background: rgba(68,255,68,0.04); border-color: rgba(68,255,68,0.08); }
        body.theme-matrix .ai-section { background: rgba(68,255,68,0.02); border-color: rgba(68,255,68,0.06); }
        body.theme-matrix .header { border-bottom-color: rgba(68,255,68,0.08); }
        body.theme-ocean { background: #0a1a2a; color: #66ddff; }
        body.theme-ocean .btn-primary { background: #44ccff; color: #0a1a2a; }
        body.theme-ocean #panel { background: rgba(68,204,255,0.04); border-color: rgba(68,204,255,0.08); }
        body.theme-ocean .ai-section { background: rgba(68,204,255,0.02); border-color: rgba(68,204,255,0.06); }
        body.theme-ocean .header { border-bottom-color: rgba(68,204,255,0.08); }
        body.theme-sunset { background: #1a0a0a; color: #ffaa88; }
        body.theme-sunset .btn-primary { background: #ff7744; color: #1a0a0a; }
        body.theme-sunset #panel { background: rgba(255,119,68,0.04); border-color: rgba(255,119,68,0.08); }
        body.theme-sunset .ai-section { background: rgba(255,119,68,0.02); border-color: rgba(255,119,68,0.06); }
        body.theme-sunset .header { border-bottom-color: rgba(255,119,68,0.08); }
        body.theme-forest { background: #0a1a0a; color: #88ff88; }
        body.theme-forest .btn-primary { background: #55ff55; color: #0a1a0a; }
        body.theme-forest #panel { background: rgba(85,255,85,0.04); border-color: rgba(85,255,85,0.08); }
        body.theme-forest .ai-section { background: rgba(85,255,85,0.02); border-color: rgba(85,255,85,0.06); }
        body.theme-forest .header { border-bottom-color: rgba(85,255,85,0.08); }
        body.theme-cosmos { background: #05050f; color: #cc88ff; }
        body.theme-cosmos .btn-primary { background: #aa44ff; color: #05050f; }
        body.theme-cosmos #panel { background: rgba(170,68,255,0.04); border-color: rgba(170,68,255,0.08); }
        body.theme-cosmos .ai-section { background: rgba(170,68,255,0.02); border-color: rgba(170,68,255,0.06); }
        body.theme-cosmos .header { border-bottom-color: rgba(170,68,255,0.08); }
        body.theme-lava { background: #1a0a05; color: #ff8866; }
        body.theme-lava .btn-primary { background: #ff5533; color: #1a0a05; }
        body.theme-lava #panel { background: rgba(255,85,51,0.04); border-color: rgba(255,85,51,0.08); }
        body.theme-lava .ai-section { background: rgba(255,85,51,0.02); border-color: rgba(255,85,51,0.06); }
        body.theme-lava .header { border-bottom-color: rgba(255,85,51,0.08); }
        body.theme-gold { background: #1a1a0a; color: #ffdd88; }
        body.theme-gold .btn-primary { background: #ffcc44; color: #1a1a0a; }
        body.theme-gold #panel { background: rgba(255,204,68,0.04); border-color: rgba(255,204,68,0.08); }
        body.theme-gold .ai-section { background: rgba(255,204,68,0.02); border-color: rgba(255,204,68,0.06); }
        body.theme-gold .header { border-bottom-color: rgba(255,204,68,0.08); }
        body.theme-purple { background: #0a0a1a; color: #dd88ff; }
        body.theme-purple .btn-primary { background: #cc44ff; color: #0a0a1a; }
        body.theme-purple #panel { background: rgba(204,68,255,0.04); border-color: rgba(204,68,255,0.08); }
        body.theme-purple .ai-section { background: rgba(204,68,255,0.02); border-color: rgba(204,68,255,0.06); }
        body.theme-purple .header { border-bottom-color: rgba(204,68,255,0.08); }
        body.theme-cherry { background: #1a0a12; color: #ff88bb; }
        body.theme-cherry .btn-primary { background: #ff44aa; color: #1a0a12; }
        body.theme-cherry #panel { background: rgba(255,68,170,0.04); border-color: rgba(255,68,170,0.08); }
        body.theme-cherry .ai-section { background: rgba(255,68,170,0.02); border-color: rgba(255,68,170,0.06); }
        body.theme-cherry .header { border-bottom-color: rgba(255,68,170,0.08); }
        body.theme-emerald { background: #0a1a0a; color: #66ffaa; }
        body.theme-emerald .btn-primary { background: #44ff88; color: #0a1a0a; }
        body.theme-emerald #panel { background: rgba(68,255,136,0.04); border-color: rgba(68,255,136,0.08); }
        body.theme-emerald .ai-section { background: rgba(68,255,136,0.02); border-color: rgba(68,255,136,0.06); }
        body.theme-emerald .header { border-bottom-color: rgba(68,255,136,0.08); }
        body.theme-sunny { background: #f5ede1; color: #3a2a1a; }
        body.theme-sunny .btn-primary { background: #d4a040; color: #f5ede1; }
        body.theme-sunny #panel { background: rgba(212,160,64,0.05); border-color: rgba(212,160,64,0.1); }
        body.theme-sunny .ai-section { background: rgba(212,160,64,0.03); border-color: rgba(212,160,64,0.06); }
        body.theme-sunny .header { border-bottom-color: rgba(212,160,64,0.1); }
        body.theme-ice { background: #0a1a2a; color: #88ddff; }
        body.theme-ice .btn-primary { background: #44bbff; color: #0a1a2a; }
        body.theme-ice #panel { background: rgba(68,187,255,0.04); border-color: rgba(68,187,255,0.08); }
        body.theme-ice .ai-section { background: rgba(68,187,255,0.02); border-color: rgba(68,187,255,0.06); }
        body.theme-ice .header { border-bottom-color: rgba(68,187,255,0.08); }
        body.theme-wine { background: #1a0508; color: #ff6677; }
        body.theme-wine .btn-primary { background: #ee3355; color: #1a0508; }
        body.theme-wine #panel { background: rgba(238,51,85,0.04); border-color: rgba(238,51,85,0.08); }
        body.theme-wine .ai-section { background: rgba(238,51,85,0.02); border-color: rgba(238,51,85,0.06); }
        body.theme-wine .header { border-bottom-color: rgba(238,51,85,0.08); }
        body.theme-moon { background: #1a1a2a; color: #c8d0e0; }
        body.theme-moon .btn-primary { background: #8888cc; color: #1a1a2a; }
        body.theme-moon #panel { background: rgba(136,136,204,0.04); border-color: rgba(136,136,204,0.08); }
        body.theme-moon .ai-section { background: rgba(136,136,204,0.02); border-color: rgba(136,136,204,0.06); }
        body.theme-moon .header { border-bottom-color: rgba(136,136,204,0.08); }
        body.theme-hightech { background: #0a0a1a; color: #88ddff; }
        body.theme-hightech .btn-primary { background: #44aaff; color: #0a0a1a; }
        body.theme-hightech #panel { background: rgba(68,170,255,0.04); border-color: rgba(68,170,255,0.08); }
        body.theme-hightech .ai-section { background: rgba(68,170,255,0.02); border-color: rgba(68,170,255,0.06); }
        body.theme-hightech .header { border-bottom-color: rgba(68,170,255,0.08); }
        body.theme-nature { background: #0a1a0a; color: #88dd88; }
        body.theme-nature .btn-primary { background: #44bb44; color: #0a1a0a; }
        body.theme-nature #panel { background: rgba(68,187,68,0.04); border-color: rgba(68,187,68,0.08); }
        body.theme-nature .ai-section { background: rgba(68,187,68,0.02); border-color: rgba(68,187,68,0.06); }
        body.theme-nature .header { border-bottom-color: rgba(68,187,68,0.08); }
        body.theme-noir { background: #0a0a0a; color: #ddccaa; }
        body.theme-noir .btn-primary { background: #ccaa44; color: #0a0a0a; }
        body.theme-noir #panel { background: rgba(204,170,68,0.04); border-color: rgba(204,170,68,0.08); }
        body.theme-noir .ai-section { background: rgba(204,170,68,0.02); border-color: rgba(204,170,68,0.06); }
        body.theme-noir .header { border-bottom-color: rgba(204,170,68,0.08); }
        body.theme-chaos { background: #1a0a1a; color: #ff88ff; }
        body.theme-chaos .btn-primary { background: #ff44ff; color: #1a0a1a; }
        body.theme-chaos #panel { background: rgba(255,68,255,0.04); border-color: rgba(255,68,255,0.08); }
        body.theme-chaos .ai-section { background: rgba(255,68,255,0.02); border-color: rgba(255,68,255,0.06); }
        body.theme-chaos .header { border-bottom-color: rgba(255,68,255,0.08); }

        /* ===== КОПИРОВАНИЕ СООБЩЕНИЙ ===== */
        .chat-message-wrapper {
            position: relative;
            max-width: 85%;
            margin-bottom: 8px;
        }

        .chat-message-wrapper.user {
            margin-left: auto;
        }

        .chat-message-wrapper.ai {
            margin-right: auto;
        }

        .chat-message-wrapper .chat-message {
            margin-bottom: 0;
            max-width: 100%;
            position: relative;
            padding-right: 40px;
            cursor: text;
            user-select: text;
        }

        .chat-message-wrapper .chat-message .role {
            user-select: none;
        }

        .chat-message-wrapper .copy-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(255,255,255,0.05);
            border: none;
            border-radius: 6px;
            color: #8888aa;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
            opacity: 0;
            transition: all 0.2s ease;
        }

        .chat-message-wrapper:hover .copy-btn {
            opacity: 0.6;
        }

        .chat-message-wrapper .copy-btn:hover {
            opacity: 1;
            background: rgba(255,255,255,0.1);
            color: #00d4ff;
        }

        .chat-message-wrapper .copy-btn.copied {
            opacity: 1;
            color: #51cf66;
            background: rgba(81, 207, 102, 0.15);
        }

        .chat-message-wrapper .chat-message ::selection {
            background: rgba(0, 212, 255, 0.25);
            color: #ffffff;
        }

        body.style-cloudy .chat-message-wrapper .chat-message ::selection {
            background: rgba(59, 130, 246, 0.25);
            color: #1e293b;
        }

        body.style-cloudy .chat-message-wrapper .copy-btn {
            background: rgba(0,0,0,0.04);
            color: #64748b;
        }

        body.style-cloudy .chat-message-wrapper .copy-btn:hover {
            background: rgba(0,0,0,0.08);
            color: #3b82f6;
        }

        body.style-cloudy .chat-message-wrapper .copy-btn.copied {
            color: #51cf66;
            background: rgba(81, 207, 102, 0.15);
        }
    </style>
</head>
<body>
    <!-- ======================================== -->
    <!-- ВЫБОР СТИЛЯ -->
    <!-- ======================================== -->
    <div id="styleSelector" class="active">
        <h2 style="color: #e0f0ff; font-size: 28px;" data-i18n="selectStyleTitle">🎨 Выберите стиль интерфейса</h2>
        <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
            <button class="style-btn" data-style="minimal" data-i18n="styleMinimal">⬜ Строгий минимализм</button>
            <button class="style-btn" data-style="vibes" data-i18n="styleVibes">✨ Вайбовый</button>
            <button class="style-btn" data-style="cyber" data-i18n="styleCyber">⚡ Кибер-стиль</button>
            <button class="style-btn" data-style="cloudy" data-i18n="styleCloudy">☁️ Cloudy</button>
        </div>
        <p style="color: #6688aa; font-size: 14px; margin-top: 10px;" data-i18n="styleHint">Выбор сохраняется в настройках</p>
    </div>

    <div class="container">
        <header class="header">
            <h1 id="appTitle">NeoBrain</h1>
            <div class="header-actions">
                <button class="btn btn-ghost" onclick="openShareModal()" data-i18n="shareBtn">Поделиться</button>
                <button class="btn btn-ghost" id="toggleBtn" data-i18n="panelBtn">Панель</button>
            </div>
        </header>

        <div id="panel">
            <div class="panel-grid">
                <div class="panel-section">
                    <div class="panel-section-title" id="charsTitle" data-i18n="charactersTitle">Персонажи</div>
                    <div class="panel-row">
                        <select id="charSelect"></select>
                        <button class="btn btn-sm" id="addCharBtn" data-i18n="addBtn">+</button>
                        <button class="btn btn-sm" id="randomCharBtn" data-i18n="randomBtn">🎲</button>
                        <button class="btn btn-sm btn-danger" id="deleteCharBtn" data-i18n="deleteBtn">🗑</button>
                    </div>
                    <div class="panel-row">
                        <button class="btn btn-sm btn-success" id="exportCharsBtn" data-i18n="exportBtn">Экспорт</button>
                        <button class="btn btn-sm" id="importCharsBtn" data-i18n="importBtn">Импорт</button>
                    </div>
                    <div id="charList"></div>
                </div>
                <div class="panel-section">
                    <div class="panel-section-title" id="settingsTitle" data-i18n="settingsTitle">Настройки</div>
                    <!-- Язык -->
                    <div class="panel-row">
                        <span style="opacity:0.5; font-size:13px;">🌍</span>
                        <select id="languageSelect" style="flex:1; min-width:120px;">
                            <option value="ru">🇷🇺 Русский</option>
                            <option value="uk">🇺🇦 Українська</option>
                            <option value="en">🇬🇧 English</option>
                        </select>
                        <span class="badge" id="languageStatus">✅</span>
                    </div>
                    <!-- Провайдер -->
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
                        <button class="btn btn-sm btn-success" id="saveApiKeyBtn" data-i18n="saveBtn">Сохранить</button>
                        <span class="badge" id="apiKeyStatus">❌</span>
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
                            <option value="moon">🌙 Лунная</option>
                            <option value="hightech">🧊 Хай-тек</option>
                            <option value="nature">🌿 Природа</option>
                            <option value="noir">🕶️ Нуар</option>
                            <option value="chaos">🌀 Хаос</option>
                        </select>
                        <span class="badge" id="themeStatus">✅</span>
                    </div>
                    <!-- ======================================== -->
                    <!-- КРИНЖОМЕТР -->
                    <!-- ======================================== -->
                    <div class="panel-row" style="flex-wrap: wrap;">
                        <span style="opacity:0.5; font-size:13px;" id="trendyLabel" data-i18n="trendyLabel">🔥 В тренде</span>
                        <label class="switch">
                            <input type="checkbox" id="trendyToggle">
                            <span class="slider round"></span>
                        </label>
                        <span style="opacity:0.5; font-size:13px; margin-left:20px;" id="cringeLabelTitle" data-i18n="cringeLabel">🎚️ Кринжометр</span>
                        <div style="display: flex; align-items: center; flex: 1; min-width: 180px;">
                            <input type="range" id="cringeSlider" min="1" max="10" value="5" step="1">
                            <span id="cringeLabel" style="font-size:16px; font-weight:700; min-width:30px; text-align:center; color:#ff44ff;">5</span>
                        </div>
                    </div>
                    <!-- ======================================== -->
                    <!-- КНОПКА СМЕНЫ СТИЛЯ -->
                    <!-- ======================================== -->
                    <div class="panel-row" style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 10px;">
                        <button class="btn btn-ghost" onclick="resetStyle()" style="width:100%; justify-content:center; font-size:14px;" data-i18n="changeStyleBtn">
                            🎨 Сменить стиль интерфейса
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div class="ai-section">
            <h3 id="chatTitle" data-i18n="chatTitle">Общение с AI</h3>
            <div class="ai-controls">
                <span><span class="label" id="providerLabel" data-i18n="providerLabel">Провайдер:</span> <span id="providerDisplay">Ollama</span></span>
                <span><span class="label" id="modelLabel" data-i18n="modelLabel">Модель:</span> <span id="modelDisplay">qwen2.5-coder:1.5b</span></span>
            </div>
            <div id="chatContainer"></div>
            <div class="ai-input-group">
                <input type="text" id="aiInput" placeholder="Напиши что-нибудь..." data-i18n-placeholder="inputPlaceholder">
                <button class="btn btn-primary" id="aiSendBtn" data-i18n="sendBtn">Отправить</button>
            </div>
            <div id="aiOutput"></div>
        </div>

        <div id="status" data-i18n="statusReady">Готов к работе...</div>
    </div>

    <div class="modal-overlay" id="shareModal" onclick="closeModalOutside(event)">
        <div class="modal">
            <h2 id="shareTitle" data-i18n="shareTitle">Поделиться доступом</h2>
            <p id="shareDesc" data-i18n="shareDesc">Отправь эту ссылку друзьям в одной сети:</p>
            <div class="share-link">
                <span id="shareLinkText">Загрузка...</span>
                <button onclick="copyShareLink()" id="copyBtn" data-i18n="copyBtn">Копировать</button>
            </div>
            <p style="font-size:13px; opacity:0.6;" data-i18n="shareHint">
                💡 Друзья должны быть в одной Wi-Fi сети.<br>
                Если доступ не работает — проверь брандмауэр.
            </p>
            <button class="btn-close-modal" onclick="closeShareModal()" id="closeBtn" data-i18n="closeBtn">Закрыть</button>
        </div>
    </div>

    <script>
        // ========================================
        // ПЕРЕВОДЫ НА 3 ЯЗЫКА
        // ========================================
        const LANG = {
            ru: {
                appTitle: 'NeoBrain',
                statusReady: 'Готов к работе...',
                inputPlaceholder: 'Напиши что-нибудь...',
                sendBtn: 'Отправить',
                panelBtn: 'Панель',
                shareBtn: 'Поделиться',
                charactersTitle: 'Персонажи',
                addBtn: '+',
                randomBtn: '🎲',
                deleteBtn: '🗑',
                exportBtn: 'Экспорт',
                importBtn: 'Импорт',
                settingsTitle: 'Настройки',
                providerLabel: 'Провайдер',
                modelLabel: 'Модель',
                trendyLabel: '🔥 В тренде',
                cringeLabel: '🎚️ Кринжометр',
                saveBtn: 'Сохранить',
                chatTitle: 'Общение с AI',
                shareTitle: 'Поделиться доступом',
                shareDesc: 'Отправь эту ссылку друзьям в одной сети:',
                copyBtn: 'Копировать',
                closeBtn: 'Закрыть',
                shareHint: '💡 Друзья должны быть в одной Wi-Fi сети. Если доступ не работает — проверь брандмауэр.',
                selectStyleTitle: '🎨 Выберите стиль интерфейса',
                styleMinimal: '⬜ Строгий минимализм',
                styleVibes: '✨ Вайбовый',
                styleCyber: '⚡ Кибер-стиль',
                styleCloudy: '☁️ Cloudy',
                styleHint: 'Выбор сохраняется в настройках',
                changeStyleBtn: '🎨 Сменить стиль интерфейса',
                copySuccess: 'Ссылка скопирована!',
                copyError: 'Не удалось скопировать',
                apiKeySaved: 'API ключ сохранён!',
                apiKeyMissing: 'Введите API ключ!',
                charDeleted: 'Персонаж удалён',
                charExported: 'Персонаж экспортирован!',
                charsExported: 'Экспортировано: ',
                charsImported: 'Импортировано: ',
                allNamesUsed: 'Все имена использованы!',
                charExists: 'Персонаж уже существует!',
                charCreated: 'Создан персонаж: ',
                charAdded: 'Создан персонаж: ',
                defaultCharDelete: 'Главный ИИ не может быть удалён!',
                confirmDelete: 'Удалить персонажа?',
                importSuccess: 'Импортировано ',
                importError: 'Неверный формат!',
                enterName: 'Введите имя персонажа:',
                loading: 'Загрузка...',
                thinking: 'Думаю...',
                errorNoApiKey: '❌ API ключ не указан!',
                errorResponse: '⚠️ Ответ не получен',
                errorPrefix: '❌ Ошибка: ',
                charLoad: 'Загружено: ',
                charShare: 'Поделиться персонажем',
                roleUser: '👤 Вы',
                roleAI: '🧠 AI',
                copyBtnText: '📋 Копировать',
                copySuccessText: '✅ Скопировано!',
            },
            uk: {
                appTitle: 'NeoBrain',
                statusReady: 'Готовий до роботи...',
                inputPlaceholder: 'Напиши щось...',
                sendBtn: 'Надіслати',
                panelBtn: 'Панель',
                shareBtn: 'Поділитися',
                charactersTitle: 'Персонажі',
                addBtn: '+',
                randomBtn: '🎲',
                deleteBtn: '🗑',
                exportBtn: 'Експорт',
                importBtn: 'Імпорт',
                settingsTitle: 'Налаштування',
                providerLabel: 'Провайдер',
                modelLabel: 'Модель',
                trendyLabel: '🔥 У тренді',
                cringeLabel: '🎚️ Крінжометр',
                saveBtn: 'Зберегти',
                chatTitle: 'Спілкування з AI',
                shareTitle: 'Поділитися доступом',
                shareDesc: 'Відправ це посилання друзям в одній мережі:',
                copyBtn: 'Копіювати',
                closeBtn: 'Закрити',
                shareHint: '💡 Друзі мають бути в одній Wi-Fi мережі. Якщо доступ не працює — перевір брандмауер.',
                selectStyleTitle: '🎨 Виберіть стиль інтерфейсу',
                styleMinimal: '⬜ Строгий мінімалізм',
                styleVibes: '✨ Вайбовий',
                styleCyber: '⚡ Кібер-стиль',
                styleCloudy: '☁️ Cloudy',
                styleHint: 'Вибір зберігається в налаштуваннях',
                changeStyleBtn: '🎨 Змінити стиль інтерфейсу',
                copySuccess: 'Посилання скопійовано!',
                copyError: 'Не вдалося скопіювати',
                apiKeySaved: 'API ключ збережено!',
                apiKeyMissing: 'Введіть API ключ!',
                charDeleted: 'Персонаж видалено',
                charExported: 'Персонаж експортовано!',
                charsExported: 'Експортовано: ',
                charsImported: 'Імпортовано: ',
                allNamesUsed: 'Всі імена використані!',
                charExists: 'Персонаж вже існує!',
                charCreated: 'Створено персонажа: ',
                charAdded: 'Створено персонажа: ',
                defaultCharDelete: 'Головний ШІ не може бути видалений!',
                confirmDelete: 'Видалити персонажа?',
                importSuccess: 'Імпортовано ',
                importError: 'Невірний формат!',
                enterName: 'Введіть ім\'я персонажа:',
                loading: 'Завантаження...',
                thinking: 'Думаю...',
                errorNoApiKey: '❌ API ключ не вказано!',
                errorResponse: '⚠️ Відповідь не отримано',
                errorPrefix: '❌ Помилка: ',
                charLoad: 'Завантажено: ',
                charShare: 'Поділитися персонажем',
                roleUser: '👤 Ви',
                roleAI: '🧠 ШІ',
                copyBtnText: '📋 Копіювати',
                copySuccessText: '✅ Скопійовано!',
            },
            en: {
                appTitle: 'NeoBrain',
                statusReady: 'Ready to work...',
                inputPlaceholder: 'Type something...',
                sendBtn: 'Send',
                panelBtn: 'Panel',
                shareBtn: 'Share',
                charactersTitle: 'Characters',
                addBtn: '+',
                randomBtn: '🎲',
                deleteBtn: '🗑',
                exportBtn: 'Export',
                importBtn: 'Import',
                settingsTitle: 'Settings',
                providerLabel: 'Provider',
                modelLabel: 'Model',
                trendyLabel: '🔥 Trending',
                cringeLabel: '🎚️ Cringe-o-meter',
                saveBtn: 'Save',
                chatTitle: 'Chat with AI',
                shareTitle: 'Share access',
                shareDesc: 'Send this link to friends on the same network:',
                copyBtn: 'Copy',
                closeBtn: 'Close',
                shareHint: '💡 Friends must be on the same Wi-Fi network. If access doesn\'t work — check your firewall.',
                selectStyleTitle: '🎨 Choose interface style',
                styleMinimal: '⬜ Strict minimalism',
                styleVibes: '✨ Vibes',
                styleCyber: '⚡ Cyber style',
                styleCloudy: '☁️ Cloudy',
                styleHint: 'Choice is saved in settings',
                changeStyleBtn: '🎨 Change interface style',
                copySuccess: 'Link copied!',
                copyError: 'Failed to copy',
                apiKeySaved: 'API key saved!',
                apiKeyMissing: 'Enter API key!',
                charDeleted: 'Character deleted',
                charExported: 'Character exported!',
                charsExported: 'Exported: ',
                charsImported: 'Imported: ',
                allNamesUsed: 'All names are used!',
                charExists: 'Character already exists!',
                charCreated: 'Character created: ',
                charAdded: 'Character created: ',
                defaultCharDelete: 'Main AI cannot be deleted!',
                confirmDelete: 'Delete character?',
                importSuccess: 'Imported ',
                importError: 'Invalid format!',
                enterName: 'Enter character name:',
                loading: 'Loading...',
                thinking: 'Thinking...',
                errorNoApiKey: '❌ API key is not set!',
                errorResponse: '⚠️ No response received',
                errorPrefix: '❌ Error: ',
                charLoad: 'Loaded: ',
                charShare: 'Share character',
                roleUser: '👤 You',
                roleAI: '🧠 AI',
                copyBtnText: '📋 Copy',
                copySuccessText: '✅ Copied!',
            }
        };

        // ========================================
        // ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
        // ========================================
        let currentLang = localStorage.getItem('neobrain_lang') || 'ru';
        let panelOpen = false;
        let currentProvider = 'ollama';
        let currentModel = 'qwen2.5-coder:1.5b';
        let historyLoaded = false;
        let characters = [];
        const STORAGE_CHARS = 'ai_chat_characters';

        // ========================================
        // ФУНКЦИЯ ОБНОВЛЕНИЯ ЯЗЫКА
        // ========================================
        function updateLanguage(lang) {
            const t = LANG[lang] || LANG.ru;
            
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (t[key] !== undefined) {
                    el.textContent = t[key];
                }
            });
            
            const inputPlaceholder = document.querySelector('[data-i18n-placeholder]');
            if (inputPlaceholder && t.inputPlaceholder) {
                inputPlaceholder.placeholder = t.inputPlaceholder;
            }
            
            const langStatus = document.getElementById('languageStatus');
            if (langStatus) langStatus.textContent = '✅ ' + lang.toUpperCase();
            
            // Обновляем текст кнопок копирования
            document.querySelectorAll('.copy-btn').forEach(btn => {
                if (!btn.classList.contains('copied')) {
                    btn.textContent = t.copyBtnText;
                }
            });
            
            localStorage.setItem('neobrain_lang', lang);
        }

        // ========================================
        // ВЫБОР СТИЛЯ
        // ========================================
        function initStyleSelector() {
            const styleSelector = document.getElementById('styleSelector');
            const savedStyle = localStorage.getItem('neobrain_style');
            
            if (!savedStyle) {
                styleSelector.classList.add('active');
            } else {
                document.body.classList.add('style-' + savedStyle);
                styleSelector.classList.remove('active');
            }
            
            document.querySelectorAll('.style-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const style = this.dataset.style;
                    localStorage.setItem('neobrain_style', style);
                    document.body.className = document.body.className
                        .split(' ')
                        .filter(c => !c.startsWith('style-'))
                        .join(' ');
                    document.body.classList.add('style-' + style);
                    styleSelector.classList.remove('active');
                });
            });
        }

        // ========================================
        // ИНИЦИАЛИЗАЦИЯ
        // ========================================
        document.addEventListener('DOMContentLoaded', function() {
            const langSelect = document.getElementById('languageSelect');
            if (langSelect) {
                langSelect.value = currentLang;
                updateLanguage(currentLang);
                
                langSelect.addEventListener('change', function() {
                    currentLang = this.value;
                    updateLanguage(currentLang);
                });
            }
            
            initStyleSelector();
            initPanel();
            initChat();
            initProviders();
            initThemes();
            initCharacters();
            initCringeMeter();
            initMessageSend();
        });

        // ========================================
        // ПАНЕЛЬ
        // ========================================
        function initPanel() {
            const toggleBtn = document.getElementById('toggleBtn');
            const panel = document.getElementById('panel');
            
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function() {
                    panelOpen = !panelOpen;
                    panel.style.display = panelOpen ? 'block' : 'none';
                    const t = LANG[currentLang] || LANG.ru;
                    toggleBtn.textContent = panelOpen ? '▲' : t.panelBtn;
                });
            }
        }

        // ========================================
        // КРИНЖОМЕТР
        // ========================================
        function initCringeMeter() {
            const trendyToggle = document.getElementById('trendyToggle');
            const cringeSlider = document.getElementById('cringeSlider');
            const cringeLabel = document.getElementById('cringeLabel');
            
            if (localStorage.getItem('trendy_mode') === 'true') {
                trendyToggle.checked = true;
            }
            
            const savedCringe = localStorage.getItem('cringe_level');
            if (savedCringe !== null) {
                cringeSlider.value = savedCringe;
                cringeLabel.textContent = savedCringe;
            }
            
            trendyToggle.addEventListener('change', function() {
                localStorage.setItem('trendy_mode', this.checked);
            });
            
            cringeSlider.addEventListener('input', function() {
                const val = this.value;
                cringeLabel.textContent = val;
                localStorage.setItem('cringe_level', val);
            });
        }

        // ========================================
        // ПОДЕЛИТЬСЯ
        // ========================================
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
            const text = document.getElementById('shareLinkText').textContent;
            const t = LANG[currentLang] || LANG.ru;
            navigator.clipboard.writeText(text).then(() => {
                document.getElementById('status').textContent = t.copySuccess;
            }).catch(() => {
                document.getElementById('status').textContent = t.copyError;
            });
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeShareModal();
        });

        // ========================================
        // ЧАТ С КОПИРОВАНИЕМ
        // ========================================
        function initChat() {
            const chatContainer = document.getElementById('chatContainer');
            const t = LANG[currentLang] || LANG.ru;
            
            const history = JSON.parse(localStorage.getItem('chat_history') || '[]');
            if (history.length > 0) {
                chatContainer.innerHTML = '';
                history.forEach(msg => {
                    addMessageToChat(msg.role, msg.content, false);
                });
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                addMessageToChat('ai', 'Привет! Я AI-помощник NeoBrain.', false);
            }
            historyLoaded = true;
        }

        function addMessageToChat(role, content, saveToHistory = true) {
            const t = LANG[currentLang] || LANG.ru;
            const chatContainer = document.getElementById('chatContainer');
            
            const wrapper = document.createElement('div');
            wrapper.className = 'chat-message-wrapper ' + role;
            
            const div = document.createElement('div');
            div.className = 'chat-message ' + role;
            const roleLabel = role === 'user' ? t.roleUser : t.roleAI;
            div.innerHTML = '<div class="role">' + roleLabel + '</div>' + content;
            
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.textContent = t.copyBtnText;
            copyBtn.title = t.copyBtnText;
            copyBtn.onclick = function(e) {
                e.stopPropagation();
                copyMessageContent(this, content);
            };
            
            wrapper.appendChild(div);
            wrapper.appendChild(copyBtn);
            chatContainer.appendChild(wrapper);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            if (saveToHistory && historyLoaded) {
                let history = JSON.parse(localStorage.getItem('chat_history') || '[]');
                history.push({ role: role, content: content, timestamp: Date.now() });
                if (history.length > 100) history = history.slice(-100);
                localStorage.setItem('chat_history', JSON.stringify(history));
            }
        }

        function copyMessageContent(btn, text) {
            const t = LANG[currentLang] || LANG.ru;
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = text;
            const plainText = tempDiv.textContent || tempDiv.innerText || '';
            
            navigator.clipboard.writeText(plainText).then(() => {
                btn.textContent = t.copySuccessText;
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.textContent = t.copyBtnText;
                    btn.classList.remove('copied');
                }, 2000);
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = plainText;
                document.body.appendChild(textarea);
                textarea.select();
                try {
                    document.execCommand('copy');
                    btn.textContent = t.copySuccessText;
                    btn.classList.add('copied');
                    setTimeout(() => {
                        btn.textContent = t.copyBtnText;
                        btn.classList.remove('copied');
                    }, 2000);
                } catch (err) {
                    alert(t.copyError);
                }
                document.body.removeChild(textarea);
            });
        }

        // ========================================
        // ПРОВАЙДЕРЫ
        // ========================================
        function initProviders() {
            const providerSelect = document.getElementById('providerSelect');
            const modelSelect = document.getElementById('modelSelect');
            
            const savedProvider = localStorage.getItem('neobrain_provider');
            if (savedProvider && providerSelect) {
                for (let i = 0; i < providerSelect.options.length; i++) {
                    if (providerSelect.options[i].value === savedProvider) {
                        providerSelect.value = savedProvider;
                        currentProvider = savedProvider;
                        break;
                    }
                }
            }
            
            updateModelSelect(currentProvider);
            updateDisplay();
            
            providerSelect.addEventListener('change', function() {
                currentProvider = this.value;
                localStorage.setItem('neobrain_provider', currentProvider);
                updateModelSelect(currentProvider);
                updateDisplay();
            });
            
            modelSelect.addEventListener('change', function() {
                currentModel = this.value;
                updateDisplay();
            });
            
            const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
            if (saveApiKeyBtn) {
                saveApiKeyBtn.addEventListener('click', function() {
                    const t = LANG[currentLang] || LANG.ru;
                    const apiKeyInput = document.getElementById('apiKeyInput');
                    const key = apiKeyInput.value.trim();
                    if (key) {
                        localStorage.setItem('api_key_' + currentProvider, key);
                        apiKeyInput.value = '';
                        checkApiKeyStatus();
                        document.getElementById('status').textContent = t.apiKeySaved;
                    } else {
                        alert(t.apiKeyMissing);
                    }
                });
            }
        }

        const PROVIDER_NAMES = { ollama: 'Ollama', openai: 'OpenAI', gemini: 'Google Gemini', claude: 'Anthropic Claude' };
        const PROVIDER_MODELS = {
            ollama: ['qwen2.5-coder:1.5b', 'llama3.2:3b', 'mistral:7b', 'llama3.1:8b'],
            openai: ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4-turbo'],
            gemini: ['gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash'],
            claude: ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229']
        };

        function updateModelSelect(provider) {
            const models = PROVIDER_MODELS[provider] || ['qwen2.5-coder:1.5b'];
            const modelSelect = document.getElementById('modelSelect');
            modelSelect.innerHTML = '';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
            
            let found = false;
            for (let i = 0; i < modelSelect.options.length; i++) {
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
            document.getElementById('providerDisplay').textContent = PROVIDER_NAMES[currentProvider] || currentProvider;
            document.getElementById('modelDisplay').textContent = currentModel;
            document.getElementById('modelStatus').textContent = '✅ ' + currentModel;
            
            const apiKeyRow = document.getElementById('apiKeyRow');
            if (currentProvider === 'ollama') {
                apiKeyRow.style.display = 'none';
            } else {
                apiKeyRow.style.display = 'flex';
                checkApiKeyStatus();
            }
        }

        function checkApiKeyStatus() {
            const key = localStorage.getItem('api_key_' + currentProvider);
            const apiKeyStatus = document.getElementById('apiKeyStatus');
            if (key && key.length > 0) {
                apiKeyStatus.textContent = '✅ Указан';
                apiKeyStatus.style.color = '#51cf66';
            } else {
                apiKeyStatus.textContent = '❌ Не указан';
                apiKeyStatus.style.color = '#ff6b6b';
            }
        }

        // ========================================
        // ТЕМЫ
        // ========================================
        function initThemes() {
            const themeSelect = document.getElementById('themeSelect');
            const themeStatus = document.getElementById('themeStatus');
            const body = document.body;
            
            const savedTheme = localStorage.getItem('neobrain_theme');
            if (savedTheme) {
                let found = false;
                for (let i = 0; i < themeSelect.options.length; i++) {
                    if (themeSelect.options[i].value === savedTheme) {
                        found = true;
                        break;
                    }
                }
                if (found) {
                    themeSelect.value = savedTheme;
                    body.className = 'theme-' + savedTheme;
                    themeStatus.textContent = '✅ ' + savedTheme;
                }
            }
            
            themeSelect.addEventListener('change', function() {
                const theme = this.value;
                body.className = 'theme-' + theme;
                localStorage.setItem('neobrain_theme', theme);
                themeStatus.textContent = '✅ ' + theme;
            });
        }

        // ========================================
        // ПЕРСОНАЖИ
        // ========================================
        function initCharacters() {
            loadCharacters();
            
            document.getElementById('addCharBtn').addEventListener('click', function() {
                const t = LANG[currentLang] || LANG.ru;
                const name = prompt(t.enterName);
                if (name && name.trim()) {
                    const existing = characters.some(char => 
                        char.name.replace(/[👨👩👤🤖]/g, '').trim().toLowerCase() === name.trim().toLowerCase()
                    );
                    if (existing) {
                        alert(t.charExists);
                        return;
                    }
                    addCharacter('👤 ' + name.trim());
                    document.getElementById('status').textContent = t.charAdded + name.trim();
                }
            });
            
            document.getElementById('randomCharBtn').addEventListener('click', generateRandomCharacter);
            document.getElementById('deleteCharBtn').addEventListener('click', function() {
                const select = document.getElementById('charSelect');
                if (select) deleteCharacter(select.value);
            });
            document.getElementById('exportCharsBtn').addEventListener('click', exportCharacters);
            document.getElementById('importCharsBtn').addEventListener('click', importCharacters);
        }

        const NAMES = {
            male: ['Алексей', 'Дмитрий', 'Максим', 'Артём', 'Иван', 'Сергей', 'Андрей', 'Егор', 'Никита', 'Михаил',
                'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles'],
            female: ['Анна', 'Мария', 'Екатерина', 'Ольга', 'Татьяна', 'Наталья', 'Ирина', 'Светлана', 'Анастасия', 'Дарья',
                'Mary', 'Patricia', 'Jennifer', 'Linda', 'Barbara', 'Elizabeth', 'Susan', 'Jessica', 'Sarah', 'Karen']
        };

        function loadCharacters() {
            const saved = localStorage.getItem(STORAGE_CHARS);
            if (saved) {
                try { characters = JSON.parse(saved); } catch(e) { characters = [{ id: 'default', name: 'Помощник' }]; }
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
            const select = document.getElementById('charSelect');
            if (!select) return;
            select.innerHTML = '';
            characters.forEach(char => {
                const option = document.createElement('option');
                option.value = char.id;
                option.textContent = char.name;
                select.appendChild(option);
            });
            const t = LANG[currentLang] || LANG.ru;
            document.getElementById('status').textContent = t.charLoad + characters.length;
        }

        function renderCharList() {
            const container = document.getElementById('charList');
            if (!container) return;
            container.innerHTML = '';
            characters.forEach(char => {
                const div = document.createElement('div');
                div.className = 'char-item';
                const nameSpan = document.createElement('span');
                nameSpan.className = 'char-name';
                nameSpan.textContent = char.name;
                div.appendChild(nameSpan);
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'char-actions';
                if (char.id !== 'default') {
                    const shareBtn = document.createElement('button');
                    shareBtn.className = 'char-share';
                    shareBtn.textContent = '📤';
                    shareBtn.title = LANG[currentLang]?.charShare || 'Поделиться персонажем';
                    shareBtn.onclick = (function(id) {
                        return function(e) { e.stopPropagation(); shareCharacter(id); };
                    })(char.id);
                    actionsDiv.appendChild(shareBtn);
                    const delBtn = document.createElement('button');
                    delBtn.className = 'char-delete';
                    delBtn.textContent = '✖';
                    delBtn.title = 'Удалить';
                    delBtn.onclick = (function(id) {
                        return function(e) { e.stopPropagation(); deleteCharacter(id); };
                    })(char.id);
                    actionsDiv.appendChild(delBtn);
                }
                div.appendChild(actionsDiv);
                container.appendChild(div);
            });
        }

        function deleteCharacter(charId) {
            const t = LANG[currentLang] || LANG.ru;
            if (charId === 'default') {
                alert(t.defaultCharDelete);
                return;
            }
            if (confirm(t.confirmDelete)) {
                characters = characters.filter(c => c.id !== charId);
                saveCharacters();
                renderCharacterSelect();
                renderCharList();
                document.getElementById('status').textContent = t.charDeleted;
            }
        }

        function addCharacter(name) {
            const id = Date.now().toString();
            characters.push({ id: id, name: name });
            saveCharacters();
            renderCharacterSelect();
            renderCharList();
        }

        function shareCharacter(charId) {
            const char = characters.find(c => c.id === charId);
            if (!char) return;
            const data = JSON.stringify(char, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = char.name.replace(/[^a-zA-Zа-яА-Я0-9]/g, '_') + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            const t = LANG[currentLang] || LANG.ru;
            document.getElementById('status').textContent = t.charExported;
        }

        function exportCharacters() {
            const data = JSON.stringify(characters, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'neobrain_characters_' + new Date().toISOString().slice(0, 10) + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            const t = LANG[currentLang] || LANG.ru;
            document.getElementById('status').textContent = t.charsExported + characters.length;
        }

        function importCharacters() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            const t = LANG[currentLang] || LANG.ru;
            input.onchange = function(e) {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = function(ev) {
                    try {
                        const imported = JSON.parse(ev.target.result);
                        if (!Array.isArray(imported)) {
                            alert(t.importError);
                            return;
                        }
                        const hasDefault = imported.some(c => c.id === 'default');
                        if (!hasDefault) imported.unshift({ id: 'default', name: 'Помощник' });
                        characters = imported;
                        saveCharacters();
                        renderCharacterSelect();
                        renderCharList();
                        document.getElementById('status').textContent = t.charsImported + characters.length;
                        alert(t.importSuccess + characters.length + ' ' + t.charactersTitle.toLowerCase() + '!');
                    } catch(err) { alert(t.importError); }
                };
                reader.readAsText(file);
            };
            input.click();
        }

        function generateRandomCharacter() {
            const t = LANG[currentLang] || LANG.ru;
            const existingNames = characters.map(char => char.name.replace(/[👨👩👤🤖]/g, '').trim());
            const allNames = NAMES.male.concat(NAMES.female);
            const availableNames = allNames.filter(name => existingNames.indexOf(name) === -1);
            if (availableNames.length === 0) {
                document.getElementById('status').textContent = t.allNamesUsed;
                return;
            }
            const randomIndex = Math.floor(Math.random() * availableNames.length);
            const selectedName = availableNames[randomIndex];
            const isMale = NAMES.male.indexOf(selectedName) !== -1;
            const isFemale = NAMES.female.indexOf(selectedName) !== -1;
            const genderIcon = isMale ? '👨' : isFemale ? '👩' : '👤';
            const fullName = genderIcon + ' ' + selectedName;
            addCharacter(fullName);
            document.getElementById('status').textContent = t.charCreated + selectedName;
        }

        // ========================================
        // ОТПРАВКА СООБЩЕНИЯ
        // ========================================
        function initMessageSend() {
            document.getElementById('aiSendBtn').addEventListener('click', sendMessage);
            document.getElementById('aiInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });
        }

        function sendMessage() {
            const t = LANG[currentLang] || LANG.ru;
            const input = document.getElementById('aiInput');
            const text = input.value.trim();
            if (!text) return;

            const provider = currentProvider;
            const model = currentModel;
            const trendyToggle = document.getElementById('trendyToggle');
            const cringeSlider = document.getElementById('cringeSlider');
            const trendyMode = trendyToggle.checked;
            const cringeLevel = parseInt(cringeSlider.value);

            addMessageToChat('user', text);
            input.value = '';

            const chatContainer = document.getElementById('chatContainer');
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'chat-message ai';
            thinkingDiv.id = 'thinkingMessage';
            thinkingDiv.innerHTML = '<div class="role">' + t.roleAI + '</div>' + t.thinking;
            chatContainer.appendChild(thinkingDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            let apiKey = null;
            if (provider !== 'ollama') {
                apiKey = localStorage.getItem('api_key_' + provider);
                if (!apiKey || apiKey.length === 0) {
                    thinkingDiv.remove();
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'chat-message ai';
                    errorDiv.innerHTML = '<div class="role">' + t.roleAI + '</div>' + t.errorNoApiKey;
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
                    api_key: apiKey || '',
                    trendy_mode: trendyMode,
                    cringe_level: cringeLevel
                })
            })
            .then(response => response.json())
            .then(data => {
                thinkingDiv.remove();
                if (data.error) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'chat-message ai';
                    errorDiv.innerHTML = '<div class="role">' + t.roleAI + '</div>❌ ' + data.error;
                    chatContainer.appendChild(errorDiv);
                } else {
                    addMessageToChat('ai', data.response || t.errorResponse);
                }
                chatContainer.scrollTop = chatContainer.scrollHeight;
            })
            .catch(error => {
                thinkingDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.className = 'chat-message ai';
                errorDiv.innerHTML = '<div class="role">' + t.roleAI + '</div>' + t.errorPrefix + error.message;
                chatContainer.appendChild(errorDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            });
        }

        // ========================================
        // СБРОС СТИЛЯ
        // ========================================
        function resetStyle() {
            const t = LANG[currentLang] || LANG.ru;
            localStorage.removeItem('neobrain_style');
            document.body.className = '';
            document.getElementById('styleSelector').classList.add('active');
            document.getElementById('status').textContent = '🎨 ' + t.changeStyleBtn;
        }
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
        trendy_mode = data.get('trendy_mode', False)
        cringe_level = data.get('cringe_level', 0)

        system_prompt = "Ты — полезный и дружелюбный AI-помощник."

        if trendy_mode:
            slang_context = ""
            if slang_dict:
                slang_items = list(slang_dict.items())[:30]
                slang_text = "\n".join([f"- {word}: {meaning}" for word, meaning in slang_items])
                slang_context = f"\n\nАктуальный молодёжный сленг (используй эти слова, если они уместны):\n{slang_text}"
            system_prompt += f" Используй актуальный молодёжный сленг в разговоре.{slang_context}"

        if cringe_level == 1:
            system_prompt += " Отвечай максимально сухо, серьёзно и по делу. Без шуток, без эмодзи, без сленга."
        elif cringe_level <= 3:
            system_prompt += " Отвечай вежливо и дружелюбно, иногда с лёгким юмором."
        elif cringe_level <= 6:
            system_prompt += " Отвечай в разговорном стиле, добавляй немного юмора и иногда используй эмодзи."
        elif cringe_level <= 8:
            system_prompt += " Отвечай с юмором, используй сленг, иногда шути, добавляй эмодзи."
        else:
            system_prompt += " Отвечай максимально кринжово и нелепо! Используй зумерский сленг, капс, много эмодзи, гиперболы. Будь максимально смешным и несерьёзным."

        for word in prompt.split():
            word_clean = word.strip('.,!?;:')
            if word_clean and len(word_clean) > 1 and word_clean.lower() not in slang_dict:
                add_pending_word(word_clean)

        if should_run_agent():
            threading.Thread(target=process_pending_words, daemon=True).start()

        if provider == "ollama":
            return ask_ollama(prompt, model, system_prompt)
        elif provider == "openai":
            return ask_openai(prompt, api_key, model, system_prompt)
        elif provider == "gemini":
            return ask_gemini(prompt, api_key, model, system_prompt)
        elif provider == "claude":
            return ask_claude(prompt, api_key, model, system_prompt)
        else:
            return {"error": f"Неизвестный провайдер: {provider}"}

    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

# ============================================================
# ЗАПУСК (С АВТОЗАПУСКОМ OLLAMA) — ИСПРАВЛЕННАЯ ВЕРСИЯ
# ============================================================
def run_app():
    try:
        is_exe = getattr(sys, 'frozen', False)
        
        # ============================================================
        # АВТОЗАПУСК OLLAMA (ДЛЯ ВСЕХ РЕЖИМОВ)
        # ============================================================
        if not is_ollama_running():
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
            except:
                pass
        
        if is_exe:
            # === .EXE РЕЖИМ — БЕЗ КОНСОЛИ ===
            log_file = open("neobrain.log", "w", encoding='utf-8')
            
            def log(msg):
                try:
                    log_file.write(str(msg) + "\n")
                    log_file.flush()
                except:
                    pass
            
            log("=== NeoBrain started as .exe ===")
            log(f"Python version: {sys.version}")
            log(f"Current directory: {os.getcwd()}")
            log("Starting server...")
            
            def run_server():
                try:
                    log("=== uvicorn starting ===")
                    import io
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = io.StringIO()
                    sys.stderr = io.StringIO()
                    
                    uvicorn.run(
                        app, 
                        host="127.0.0.1", 
                        port=8000, 
                        log_level="critical",
                        access_log=False,
                        use_colors=False
                    )
                    
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                except Exception as e:
                    log(f"Server error: {e}")
                    import traceback
                    log(traceback.format_exc())
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Ждём запуска сервера
            server_ready = False
            for i in range(10):
                log(f"Waiting for server... {i+1}/10")
                time.sleep(1)
                try:
                    response = requests.get("http://127.0.0.1:8000", timeout=1)
                    log(f"Server response: {response.status_code}")
                    server_ready = True
                    break
                except Exception as e:
                    log(f"Server not ready: {e}")
            
            if not server_ready:
                log("WARNING: Server may not be ready, but continuing...")
            
            log("Opening webview...")
            
            try:
                import webview
            except ImportError:
                log("ERROR: pywebview not installed")
                log_file.close()
                return
            
            log("=" * 55)
            log("NeoBrain started!")
            log("Opening application window...")
            log("Close the window to stop")
            log("=" * 55)
            log_file.close()
            
            webview.create_window(
                'NeoBrain',
                'http://127.0.0.1:8000',
                width=1200,
                height=800,
                resizable=True,
                fullscreen=False,
                min_size=(800, 600),
                confirm_close=True,
                easy_drag=True
            )
            webview.start()
            return
        
        # === ОБЫЧНЫЙ РЕЖИМ (ИЗ PYTHON) ===
        # Проверяем порт
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        if result == 0:
            print("WARNING: Port 8000 already in use! Close old instance and restart.")
            input("Press Enter to exit...")
            return

        # Запускаем сервер в фоне
        def run_server():
            try:
                uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
            except Exception as e:
                print(f"Server error: {e}")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        time.sleep(2)

        try:
            requests.get("http://localhost:8000", timeout=2)
            print("Server started!")
        except:
            print("Server failed to start!")
            input("Press Enter to exit...")
            return

        try:
            import webview
        except ImportError:
            print("ERROR: pywebview not installed")
            input("Press Enter to exit...")
            return

        print("\n" + "=" * 55)
        print("NeoBrain started!")
        print("Opening application window...")
        print(f"Local address: http://{LOCAL_IP}:8000")
        print("Close the window to stop")
        print("=" * 55 + "\n")

        webview.create_window(
            'NeoBrain',
            'http://localhost:8000',
            width=1200,
            height=800,
            resizable=True,
            fullscreen=False,
            min_size=(800, 600),
            confirm_close=True,
            easy_drag=True
        )
        webview.start()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass

if __name__ == "__main__":
    run_app()