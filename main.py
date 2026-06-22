from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import requests
import uvicorn
import subprocess
import time
import socket
import json

def start_ollama():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        print("✅ Ollama уже запущен")
    except:
        print("🔄 Запуск Ollama...")
        subprocess.Popen(["ollama", "serve"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        print("✅ Ollama запущен")

start_ollama()

app = FastAPI()

@app.get("/models")
async def get_models():
    try:
        r = requests.get("http://localhost:11434/api/tags")
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return {"models": models}
    except:
        pass
    return {"models": ["qwen2.5-coder:7b", "qwen2.5-coder:1.5b"]}

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeoBrain | AI чат</title>
    <style>
        /* ===== ОБЩИЕ СТИЛИ ===== */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1rem;
            transition: all 0.3s;
        }
        
        /* ===== ОСНОВНОЙ КОНТЕЙНЕР ===== */
        .chat-app {
            max-width: 1200px;
            width: 100%;
            height: 90vh;
            backdrop-filter: blur(14px);
            border-radius: 2rem;
            border: 2px solid var(--neon, #00ffff);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
            transition: all 0.3s;
        }
        .chat-app::before {
            content: '';
            position: absolute;
            top: -30px; left: -30px; right: -30px; bottom: -30px;
            border-radius: 3rem;
            z-index: -1;
            filter: blur(30px);
            opacity: 0.25;
            background: var(--neon, #00ffff);
            transition: all 0.3s;
        }
        
        /* ===== ШАПКА ===== */
        .header {
            padding: 0.8rem 1.8rem;
            background: rgba(0,0,0,0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.8rem;
            flex-shrink: 0;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand h1 {
            font-size: 1.4rem;
            color: #fff;
            text-shadow: 0 0 20px var(--neon, #00ffff);
        }
        .brand p {
            font-size: 0.7rem;
            opacity: 0.6;
            color: #fff;
        }
        
        /* ===== ПАНЕЛЬ УПРАВЛЕНИЯ ===== */
        .controls {
            display: flex;
            gap: 0.6rem;
            align-items: center;
            flex-wrap: wrap;
        }
        .controls select, .controls button {
            background: rgba(0,0,0,0.4);
            border: 1px solid var(--neon, #00ffff);
            padding: 6px 14px;
            border-radius: 2rem;
            color: #fff;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        .controls select:hover, .controls button:hover {
            background: var(--neon, #00ffff);
            color: #000;
        }
        .controls select option {
            background: #1a1a2e;
            color: #fff;
        }
        
        /* ===== ВЫПАДАЮЩЕЕ МЕНЮ ТЕМ ===== */
        .theme-dropdown {
            position: relative;
            display: inline-block;
        }
        .theme-dropdown-content {
            display: none;
            position: absolute;
            background: rgba(0,0,0,0.85);
            border: 1px solid var(--neon, #00ffff);
            border-radius: 1rem;
            padding: 8px;
            z-index: 100;
            min-width: 180px;
            right: 0;
            top: 40px;
        }
        .theme-dropdown-content.show {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            justify-content: center;
        }
        .theme-btn {
            background: none;
            border: 1px solid var(--neon, #00ffff);
            border-radius: 50%;
            width: 32px;
            height: 32px;
            font-size: 0.9rem;
            cursor: pointer;
            color: #fff;
            transition: all 0.3s;
        }
        .theme-btn:hover {
            transform: scale(1.15);
            box-shadow: 0 0 20px var(--neon, #00ffff);
        }
        .theme-btn.active {
            background: var(--neon, #00ffff);
            color: #000;
        }
        
        /* ===== ОКНО ЧАТА ===== */
        .chat-window {
            flex: 1;
            overflow-y: auto;
            padding: 1.2rem 1.8rem;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        
        /* ===== СООБЩЕНИЯ ===== */
        .msg {
            display: flex;
            gap: 12px;
            max-width: 80%;
            animation: slideUp 0.3s ease;
        }
        .user-msg {
            align-self: flex-end;
            flex-direction: row-reverse;
        }
        .ai-msg {
            align-self: flex-start;
        }
        .avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: rgba(0,0,0,0.4);
            border: 1px solid var(--neon, #00ffff);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            flex-shrink: 0;
            box-shadow: 0 0 10px var(--neon, #00ffff);
        }
        .bubble {
            padding: 10px 18px;
            border-radius: 24px;
            font-size: 0.95rem;
            background: rgba(10,10,30,0.5);
            backdrop-filter: blur(8px);
            color: #fff;
            border: 1px solid var(--neon, #00ffff);
            box-shadow: 0 0 8px var(--neon, #00ffff);
            word-break: break-word;
        }
        .user-msg .bubble {
            background: rgba(40,80,140,0.8);
            border-bottom-right-radius: 8px;
        }
        .ai-msg .bubble {
            border-bottom-left-radius: 8px;
        }
        .msg-time {
            font-size: 0.6rem;
            opacity: 0.5;
            padding-left: 56px;
            color: #fff;
        }
        .user-msg .msg-time {
            text-align: right;
            padding-right: 10px;
        }
        
        /* ===== ПОЛЕ ВВОДА ===== */
        .input-area {
            background: rgba(0,0,0,0.3);
            border-top: 1px solid var(--neon, #00ffff);
            padding: 0.8rem 1.5rem;
            display: flex;
            gap: 12px;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .input-area input {
            flex: 1;
            max-width: 700px;
            padding: 10px 18px;
            border-radius: 60px;
            border: 1px solid var(--neon, #00ffff);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.3s;
        }
        .input-area input:focus {
            border-color: var(--neon, #00ffff);
            box-shadow: 0 0 15px var(--neon, #00ffff);
        }
        .input-area input::placeholder {
            color: rgba(255,255,255,0.4);
        }
        .input-area button {
            background: var(--neon, #00ffff);
            border: none;
            padding: 10px 28px;
            border-radius: 60px;
            font-weight: bold;
            color: #000;
            cursor: pointer;
            transition: all 0.3s;
            flex-shrink: 0;
        }
        .input-area button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 25px var(--neon, #00ffff);
        }
        
        /* ===== ИНДИКАТОР ПЕЧАТИ ===== */
        .typing-block {
            display: none;
            align-items: center;
            gap: 12px;
            padding: 0.5rem 1.5rem;
            flex-shrink: 0;
        }
        .typing-dots span {
            width: 8px;
            height: 8px;
            background: var(--neon, #00ffff);
            border-radius: 50%;
            display: inline-block;
            animation: wave 1.2s infinite;
            box-shadow: 0 0 10px var(--neon, #00ffff);
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes wave {
            0%,60%,100% { opacity: 0.4; transform: translateY(0); }
            30% { opacity: 1; transform: translateY(-4px); }
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* ===== МОДАЛЬНЫЕ ОКНА ===== */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            backdrop-filter: blur(8px);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-content {
            background: rgba(0,0,0,0.8);
            border: 1px solid var(--neon, #00ffff);
            border-radius: 2rem;
            padding: 2rem;
            width: 90%;
            max-width: 400px;
            color: #fff;
            box-shadow: 0 0 40px var(--neon, #00ffff);
        }
        .modal-content h3 {
            margin-bottom: 1rem;
            color: var(--neon, #00ffff);
            text-shadow: 0 0 20px var(--neon, #00ffff);
        }
        .modal-content input, .modal-content textarea {
            width: 100%;
            margin: 8px 0;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--neon, #00ffff);
            border-radius: 12px;
            color: #fff;
            font-size: 0.95rem;
        }
        .modal-content textarea {
            resize: vertical;
            min-height: 80px;
        }
        .modal-buttons {
            display: flex;
            gap: 10px;
            margin-top: 12px;
        }
        .modal-buttons button {
            flex: 1;
            padding: 8px;
            border-radius: 2rem;
            cursor: pointer;
            border: none;
            font-weight: bold;
            transition: all 0.3s;
        }
        .modal-buttons button:first-child {
            background: var(--neon, #00ffff);
            color: #000;
            box-shadow: 0 0 20px var(--neon, #00ffff);
        }
        .modal-buttons button:first-child:hover {
            transform: scale(1.02);
        }
        .modal-buttons button:last-child {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        
        /* ===== НАСТРОЙКИ ===== */
        #settingsModal .modal-box {
            background: rgba(10,10,30,0.9);
            border: 2px solid var(--neon, #00ffff);
            border-radius: 2rem;
            padding: 2.5rem;
            width: 90%;
            max-width: 400px;
            color: #fff;
            text-align: center;
            box-shadow: 0 0 60px var(--neon, #00ffff);
        }
        #settingsModal .modal-box h2 {
            font-size: 1.6rem;
            margin-bottom: 1.5rem;
            color: var(--neon, #00ffff);
            text-shadow: 0 0 20px var(--neon, #00ffff);
        }
        #settingsModal .modal-box .btn-group {
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }
        #settingsModal .modal-box .btn-group button {
            padding: 12px 24px;
            border-radius: 2rem;
            border: 2px solid var(--neon, #00ffff);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        #settingsModal .modal-box .btn-group button:hover {
            background: var(--neon, #00ffff);
            color: #000;
            transform: scale(1.02);
            box-shadow: 0 0 30px var(--neon, #00ffff);
        }
        #settingsModal .modal-box .btn-group button.default-btn {
            border-color: #4caf50;
        }
        #settingsModal .modal-box .btn-group button.default-btn:hover {
            background: #4caf50;
        }
        #settingsModal .modal-box .close-btn {
            margin-top: 1.5rem;
            padding: 8px 24px;
            border-radius: 2rem;
            border: 1px solid rgba(255,255,255,0.2);
            background: none;
            color: #fff;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.3s;
        }
        #settingsModal .modal-box .close-btn:hover {
            background: rgba(255,255,255,0.1);
        }
        
        /* ===== ПРИВЕТСТВИЕ ===== */
        #welcomeModal .modal-box {
            background: rgba(10,10,30,0.9);
            border: 2px solid var(--neon, #00ffff);
            border-radius: 2rem;
            padding: 2.5rem;
            width: 90%;
            max-width: 500px;
            color: #fff;
            text-align: center;
            box-shadow: 0 0 60px var(--neon, #00ffff);
        }
        #welcomeModal .modal-box h2 {
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
            color: var(--neon, #00ffff);
            text-shadow: 0 0 20px var(--neon, #00ffff);
        }
        #welcomeModal .modal-box p {
            font-size: 0.95rem;
            opacity: 0.8;
            margin: 0.5rem 0 1.5rem;
            line-height: 1.5;
        }
        #welcomeModal .modal-box .btn-group {
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }
        #welcomeModal .modal-box .btn-group button {
            padding: 12px 24px;
            border-radius: 2rem;
            border: 2px solid var(--neon, #00ffff);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        #welcomeModal .modal-box .btn-group button:hover {
            background: var(--neon, #00ffff);
            color: #000;
            transform: scale(1.02);
            box-shadow: 0 0 30px var(--neon, #00ffff);
        }
        #welcomeModal .modal-box .btn-group button.default-btn {
            border-color: #4caf50;
        }
        #welcomeModal .modal-box .btn-group button.default-btn:hover {
            background: #4caf50;
        }
        
        /* ===== КИБЕР-ДОЖДЬ ===== */
        .cyber-rain {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            pointer-events: none;
            z-index: 0;
            font-family: monospace;
            font-size: 20px;
            color: #00d4ff;
            opacity: 0.25;
            text-shadow: 0 0 5px #00d4ff, 0 0 15px #7b2fbe;
        }
        .cyber-overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.4);
            pointer-events: none;
            z-index: 1;
        }
        .glitch-overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            pointer-events: none;
            z-index: 1;
            background: repeating-linear-gradient(0deg, rgba(0,212,255,0.02) 0px, rgba(123,47,190,0.02) 2px, transparent 4px, transparent 8px);
            animation: glitchScan 4s linear infinite;
        }
        @keyframes glitchScan {
            0% { transform: translateY(-100%); }
            100% { transform: translateY(100%); }
        }
        
        /* ===== ТЕМЫ ===== */
        body[data-theme="neon"] { --neon: #00ffff; background: radial-gradient(circle at 20% 30%, #0a0f1e, #03060c); }
        body[data-theme="babydoll"] { --neon: #ffb6c1; background: linear-gradient(135deg, #ffe0f0, #e0f0ff); }
        body[data-theme="summer"] { --neon: #ffa500; background: linear-gradient(135deg, #c0e0a0, #ffcc80); }
        body[data-theme="beach"] { --neon: #ffd700; background: linear-gradient(135deg, #b0e0ff, #fff0a0); }
        body[data-theme="digital"] { --neon: #ff8c00; background: linear-gradient(135deg, #ffaa70, #c080ff); }
        body[data-theme="creative"] { --neon: #ffb6c1; background: linear-gradient(135deg, #ffc0cb, #a0b080); }
        body[data-theme="warm"] { --neon: #ffaa77; background: linear-gradient(135deg, #ffd0d0, #ffe0b0); }
        body[data-theme="cyber"] { --neon: #00d4ff; background: #0a0a0f; position: relative; overflow: hidden; }
        body[data-theme="wine"] { --neon: #a61b7a; background: radial-gradient(ellipse at 30% 40%, #3a0a1a, #1a050a); }
        
        body[data-theme] .chat-app { border-color: var(--neon); box-shadow: 0 0 30px var(--neon); }
        body[data-theme] .chat-app::before { background: var(--neon); }
        body[data-theme] .bubble { border-color: var(--neon); box-shadow: 0 0 8px var(--neon); }
        body[data-theme] .input-area { border-color: var(--neon); }
        body[data-theme] .controls select, body[data-theme] .controls button { border-color: var(--neon); }
        body[data-theme] .controls select:hover, body[data-theme] .controls button:hover { background: var(--neon); color: #000; }
        body[data-theme] .theme-dropdown-content { border-color: var(--neon); }
        body[data-theme] .avatar { border-color: var(--neon); }
        
        /* ===== РЕЖИМЫ ДЛЯ ДАЛЬТОНИКОВ ===== */
        body.tritanopia { filter: hue-rotate(180deg) saturate(0.6); }
        body.deuteranopia { filter: grayscale(0.3) contrast(1.1); }
        
        /* ===== АДАПТИВНОСТЬ ===== */
        @media (max-width: 768px) {
            .controls { gap: 0.4rem; }
            .controls select, .controls button { padding: 4px 10px; font-size: 0.7rem; }
            .header { padding: 0.5rem 1rem; }
            .brand h1 { font-size: 1.1rem; }
            .chat-window { padding: 0.8rem 1rem; }
            .msg { max-width: 95%; }
            .input-area input { max-width: 100%; }
            #welcomeModal .modal-box { padding: 1.5rem; }
            #welcomeModal .modal-box h2 { font-size: 1.4rem; }
            #settingsModal .modal-box { padding: 1.5rem; }
        }
    </style>
</head>
<body data-theme="neon">
    <div class="chat-app">
        <!-- ШАПКА -->
        <div class="header">
            <div class="brand">
                <span style="font-size:2rem; filter: drop-shadow(0 0 15px var(--neon));">🧠</span>
                <div>
                    <h1>NeoBrain</h1>
                    <p>локальная нейросеть</p>
                </div>
            </div>
            <div class="controls">
                <select id="modelSelect"><option>Загрузка...</option></select>
                <div class="theme-dropdown">
                    <button id="themeToggleBtn" class="theme-btn" style="width:auto; padding:6px 16px;">🎨 Темы</button>
                    <div class="theme-dropdown-content" id="themeDropdown">
                        <button class="theme-btn" data-theme="neon">🌙</button>
                        <button class="theme-btn" data-theme="babydoll">🎀</button>
                        <button class="theme-btn" data-theme="summer">☀️</button>
                        <button class="theme-btn" data-theme="beach">🏖️</button>
                        <button class="theme-btn" data-theme="digital">📱</button>
                        <button class="theme-btn" data-theme="creative">🎨</button>
                        <button class="theme-btn" data-theme="warm">🔥</button>
                        <button class="theme-btn" data-theme="cyber">🎮</button>
                        <button class="theme-btn" data-theme="wine">🍷</button>
                    </div>
                </div>
                <button id="clearBtn">🗑</button>
                <button id="addCharacterBtn">➕</button>
                <label style="color: #fff; font-size: 0.8rem; display: flex; align-items: center; gap: 6px; background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 20px; border: 1px solid var(--neon); cursor: pointer;">
                    <input type="checkbox" id="streamToggle" checked style="accent-color: var(--neon); width: 16px; height: 16px; cursor: pointer;">
                    💨 Поток
                </label>
                <button id="settingsBtn">⚙️</button>
            </div>
        </div>
        
        <!-- ЧАТ -->
        <div class="chat-window" id="chatWindow">
            <div class="msg ai-msg">
                <div class="avatar">🤖</div>
                <div class="bubble">Привет! Я NeoBrain. Напиши что-нибудь 😊</div>
            </div>
        </div>
        
        <!-- ИНДИКАТОР ПЕЧАТИ -->
        <div class="typing-block" id="typingBlock">
            <div class="avatar">🤖</div>
            <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
        
        <!-- ПОЛЕ ВВОДА -->
        <div class="input-area">
            <input type="text" id="msgInput" placeholder="Напиши сообщение..." autofocus>
            <button id="sendBtn">💬</button>
        </div>
    </div>
    
    <!-- МОДАЛКА ПЕРСОНАЖА -->
    <div id="modal" class="modal">
        <div class="modal-content">
            <h3>➕ Новый персонаж</h3>
            <input type="text" id="modalCharName" placeholder="Имя персонажа">
            <textarea id="modalCharDesc" rows="3" placeholder="Опиши характер, стиль речи, роль..."></textarea>
            <div class="modal-buttons">
                <button id="modalSaveBtn">Сохранить</button>
                <button id="modalCancelBtn">Отмена</button>
            </div>
        </div>
    </div>
    
    <!-- ПРИВЕТСТВИЕ -->
    <div id="welcomeModal">
        <div class="modal-box">
            <h2>👋 Добро пожаловать!</h2>
            <p>Выберите режим отображения. Если у вас нет нарушений цветовосприятия, просто оставьте как есть.</p>
            <div class="btn-group">
                <button class="default-btn" onclick="setAccessibility('default')">✅ Оставить как есть</button>
                <button onclick="setAccessibility('tritanopia')">👁️ Режим для тританопии</button>
                <button onclick="setAccessibility('deuteranopia')">👁️ Режим для дейтеранопии</button>
            </div>
            <p style="font-size:0.75rem; opacity:0.5; margin-top:1.5rem;">Настройку можно изменить через ⚙️</p>
        </div>
    </div>
    
    <!-- НАСТРОЙКИ -->
    <div id="settingsModal">
        <div class="modal-box">
            <h2>⚙️ Настройки</h2>
            <div class="btn-group">
                <button class="default-btn" onclick="setAccessibility('default')">✅ Обычный режим</button>
                <button onclick="setAccessibility('tritanopia')">👁️ Тританопия</button>
                <button onclick="setAccessibility('deuteranopia')">👁️ Дейтеранопия</button>
            </div>
            <button class="close-btn" onclick="document.getElementById('settingsModal').style.display='none'">✕ Закрыть</button>
        </div>
    </div>

    <script>
        // ===== ЭЛЕМЕНТЫ =====
        const chatWindow = document.getElementById('chatWindow');
        const msgInput = document.getElementById('msgInput');
        const sendBtn = document.getElementById('sendBtn');
        const clearBtn = document.getElementById('clearBtn');
        const modelSelect = document.getElementById('modelSelect');
        const typingBlock = document.getElementById('typingBlock');
        const addCharacterBtn = document.getElementById('addCharacterBtn');
        const modal = document.getElementById('modal');
        const modalCharName = document.getElementById('modalCharName');
        const modalCharDesc = document.getElementById('modalCharDesc');
        const modalSaveBtn = document.getElementById('modalSaveBtn');
        const modalCancelBtn = document.getElementById('modalCancelBtn');
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        const themeDropdown = document.getElementById('themeDropdown');
        const welcomeModal = document.getElementById('welcomeModal');
        const settingsModal = document.getElementById('settingsModal');
        const settingsBtn = document.getElementById('settingsBtn');
        const streamToggle = document.getElementById('streamToggle');

        // ===== ДОСТУПНОСТЬ =====
        function setAccessibility(mode) {
            document.body.classList.remove('tritanopia', 'deuteranopia');
            if (mode !== 'default') document.body.classList.add(mode);
            localStorage.setItem('neobrain_accessibility', mode);
            welcomeModal.style.display = 'none';
            settingsModal.style.display = 'none';
            showToast('Режим: ' + (mode === 'default' ? 'Обычный' : mode === 'tritanopia' ? 'Тританопия' : 'Дейтеранопия'));
        }

        function showToast(text) {
            const toast = document.createElement('div');
            toast.style.cssText = `
                position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                background: var(--neon, #00ffff); color: #000;
                padding: 12px 24px; border-radius: 30px; font-weight: bold;
                z-index: 9999; box-shadow: 0 0 30px var(--neon, #00ffff);
                transition: all 0.3s;
            `;
            toast.innerText = text;
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(-50%) translateY(20px)';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // ===== ЗАГРУЗКА МОДЕЛЕЙ =====
        async function loadModels() {
            try {
                const res = await fetch('/models');
                const data = await res.json();
                modelSelect.innerHTML = '';
                if (data.models && data.models.length) {
                    data.models.forEach(m => {
                        if (m === 'phi3:3.8b' || m === 'llama3.2:3b') return;
                        const opt = document.createElement('option');
                        opt.value = m;
                        let name = m;
                        if (m === 'mistral:7b') name = '🧠 Mistral 7b — Умная';
                        else if (m === 'qwen2.5-coder:7b') name = '💻 Qwen 7b — Сбалансированная';
                        else if (m === 'qwen2.5-coder:1.5b') name = '⚡ Qwen 1.5b — Молниеносная';
                        else if (m === 'llama3.1:8b') name = '🎭 Llama 3.1 8b — Творческая';
                        else name = m;
                        opt.textContent = name;
                        modelSelect.appendChild(opt);
                    });
                }
            } catch(e) { console.error(e); }
        }

        // ===== ТЕМЫ =====
        function applyTheme(theme) {
            document.body.setAttribute('data-theme', theme);
            localStorage.setItem('neobrain_theme', theme);
            themeDropdown.classList.remove('show');
            document.querySelectorAll('.theme-btn[data-theme]').forEach(b => b.classList.remove('active'));
            const activeBtn = document.querySelector(`.theme-btn[data-theme="${theme}"]`);
            if (activeBtn) activeBtn.classList.add('active');
            themeToggleBtn.textContent = (activeBtn ? activeBtn.textContent : '🎨') + ' Темы';
            if (theme === 'cyber') startCyberRain();
            else stopCyberRain();
        }

        document.querySelectorAll('.theme-btn[data-theme]').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                applyTheme(this.dataset.theme);
            });
        });

        themeToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            themeDropdown.classList.toggle('show');
        });
        document.addEventListener('click', () => themeDropdown.classList.remove('show'));

        // ===== КИБЕР-ДОЖДЬ =====
        let cyberInterval = null, glitchInterval = null;

        function startCyberRain() {
            if (cyberInterval) return;
            const container = document.createElement('div');
            container.className = 'cyber-rain';
            container.id = 'cyberRain';
            document.body.appendChild(container);

            const overlay = document.createElement('div');
            overlay.className = 'cyber-overlay';
            overlay.id = 'cyberOverlay';
            document.body.appendChild(overlay);

            const glitch = document.createElement('div');
            glitch.className = 'glitch-overlay';
            glitch.id = 'glitchOverlay';
            document.body.appendChild(glitch);

            const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            const cols = Math.floor(window.innerWidth / 18);
            const drops = [];

            for (let i = 0; i < cols; i++) {
                const col = document.createElement('div');
                col.style.position = 'absolute';
                col.style.top = (-50 - Math.random() * 300) + 'px';
                col.style.left = i * 18 + 'px';
                col.style.fontFamily = 'monospace';
                col.style.fontSize = (16 + Math.random() * 10) + 'px';
                col.style.color = Math.random() > 0.6 ? '#7b2fbe' : '#00d4ff';
                col.style.opacity = 0.1 + Math.random() * 0.3;
                col.style.textShadow = `0 0 8px ${col.style.color}`;
                const len = 5 + Math.floor(Math.random() * 15);
                let txt = '';
                for (let j = 0; j < len; j++) txt += chars[Math.floor(Math.random() * chars.length)] + '\\n';
                col.textContent = txt;
                container.appendChild(col);
                drops.push({ el: col, speed: 0.5 + Math.random() * 3 });
            }

            cyberInterval = setInterval(() => {
                for (const d of drops) {
                    let top = parseFloat(d.el.style.top);
                    top += d.speed;
                    if (top > window.innerHeight + 200) {
                        top = -50 - Math.random() * 300;
                        d.el.style.color = Math.random() > 0.6 ? '#7b2fbe' : '#00d4ff';
                        d.el.style.textShadow = `0 0 8px ${d.el.style.color}`;
                        const newLen = 5 + Math.floor(Math.random() * 15);
                        let txt = '';
                        for (let j = 0; j < newLen; j++) txt += chars[Math.floor(Math.random() * chars.length)] + '\\n';
                        d.el.textContent = txt;
                        d.el.style.opacity = 0.1 + Math.random() * 0.3;
                    }
                    d.el.style.top = top + 'px';
                }
            }, 70);

            glitchInterval = setInterval(() => {
                const el = document.getElementById('glitchOverlay');
                if (el) {
                    const r1 = 0.02 + Math.random() * 0.05;
                    const r2 = 0.02 + Math.random() * 0.05;
                    const r3 = 8 + Math.random() * 25;
                    el.style.background = `repeating-linear-gradient(0deg, rgba(0,212,255,${r1}) 0px, rgba(123,47,190,${r2}) 2px, transparent 4px, transparent ${r3}px)`;
                    setTimeout(() => {
                        el.style.background = 'repeating-linear-gradient(0deg, rgba(0,212,255,0.02) 0px, rgba(123,47,190,0.02) 2px, transparent 4px, transparent 8px)';
                    }, 200);
                }
            }, 4000 + Math.random() * 6000);
        }

        function stopCyberRain() {
            if (cyberInterval) { clearInterval(cyberInterval); cyberInterval = null; }
            if (glitchInterval) { clearInterval(glitchInterval); glitchInterval = null; }
            document.getElementById('cyberRain')?.remove();
            document.getElementById('cyberOverlay')?.remove();
            document.getElementById('glitchOverlay')?.remove();
        }

        // ===== ВОССТАНОВЛЕНИЕ НАСТРОЕК =====
        const savedTheme = localStorage.getItem('neobrain_theme') || 'neon';
        applyTheme(savedTheme);

        const savedAccess = localStorage.getItem('neobrain_accessibility');
        if (savedAccess) {
            welcomeModal.style.display = 'none';
            setAccessibility(savedAccess);
        }

        // ===== СООБЩЕНИЯ =====
        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = 'msg ' + (isUser ? 'user-msg' : 'ai-msg');
            div.innerHTML = `
                <div class="avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="bubble">${text}</div>
            `;
            chatWindow.appendChild(div);
            const time = document.createElement('div');
            time.className = 'msg-time';
            time.innerText = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            chatWindow.appendChild(time);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        function clearChat() {
            if (confirm('Очистить чат?')) {
                chatWindow.innerHTML = '';
                addMessage('Чат очищен. Напиши что-нибудь!', false);
            }
        }

        function showTyping() { typingBlock.style.display = 'flex'; }
        function hideTyping() { typingBlock.style.display = 'none'; }

        // ===== ПЕРСОНАЖИ =====
        let characters = [];
        let activeCharacterId = null;
        const STORAGE_CHARS = 'neobrain_chars';
        const STORAGE_ACTIVE = 'neobrain_active_char';

        function loadCharacters() {
            const saved = localStorage.getItem(STORAGE_CHARS);
            characters = saved ? JSON.parse(saved) : [{ id: 'default', name: 'Помощник', description: 'Ты дружелюбный и умный ассистент. Отвечай на русском кратко.' }];
            const active = localStorage.getItem(STORAGE_ACTIVE);
            activeCharacterId = active && characters.some(c => c.id === active) ? active : characters[0].id;
        }

        function saveCharacters() {
            localStorage.setItem(STORAGE_CHARS, JSON.stringify(characters));
            localStorage.setItem(STORAGE_ACTIVE, activeCharacterId);
        }

        function addCharacter(name, desc) {
            const id = Date.now().toString();
            characters.push({ id, name, description: desc });
            activeCharacterId = id;
            saveCharacters();
        }

        loadCharacters();

        // ===== ОТПРАВКА СООБЩЕНИЙ =====
        async function sendMessage() {
            const streamEnabled = streamToggle.checked;
            if (streamEnabled) {
                await sendMessageStream();
            } else {
                await sendMessageNormal();
            }
        }

        async function sendMessageNormal() {
            const text = msgInput.value.trim();
            if (!text) return;
            const model = modelSelect.value;
            if (!model || model === 'Загрузка...') {
                addMessage('Сначала выберите модель', false);
                return;
            }
            addMessage(text, true);
            msgInput.value = '';
            showTyping();

            const aiDiv = document.createElement('div');
            aiDiv.className = 'msg ai-msg';
            aiDiv.innerHTML = '<div class="avatar">🤖</div><div class="bubble"></div>';
            const bubble = aiDiv.querySelector('.bubble');
            chatWindow.appendChild(aiDiv);

            try {
                const selectedChar = characters.find(c => c.id === activeCharacterId);
                const charDesc = selectedChar ? selectedChar.description : 'Ты полезный ассистент. Отвечай на русском кратко.';
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: text,
                        model: model,
                        temperature: 0.7,
                        character_description: charDesc,
                        history: []
                    })
                });
                let answer = await response.text();
                bubble.innerText = answer;
                const time = document.createElement('div');
                time.className = 'msg-time';
                time.innerText = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                chatWindow.appendChild(time);
                chatWindow.scrollTop = chatWindow.scrollHeight;
            } catch(err) {
                bubble.innerText = 'Ошибка: ' + err.message;
            } finally {
                hideTyping();
            }
        }

        async function sendMessageStream() {
            const text = msgInput.value.trim();
            if (!text) return;
            const model = modelSelect.value;
            if (!model || model === 'Загрузка...') {
                addMessage('Сначала выберите модель', false);
                return;
            }
            
            addMessage(text, true);
            msgInput.value = '';
            showTyping();

            const aiDiv = document.createElement('div');
            aiDiv.className = 'msg ai-msg';
            aiDiv.innerHTML = '<div class="avatar">🤖</div><div class="bubble"></div>';
            const bubble = aiDiv.querySelector('.bubble');
            chatWindow.appendChild(aiDiv);
            
            try {
                const selectedChar = characters.find(c => c.id === activeCharacterId);
                const charDesc = selectedChar ? selectedChar.description : 'Ты полезный ассистент. Отвечай на русском кратко.';
                
                const response = await fetch('/ask-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: text,
                        model: model,
                        temperature: 0.7,
                        character_description: charDesc
                    })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullText = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value, { stream: true });
                    fullText += chunk;
                    bubble.textContent = fullText;
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                }

                const time = document.createElement('div');
                time.className = 'msg-time';
                time.innerText = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                chatWindow.appendChild(time);
            } catch(err) {
                bubble.innerText = 'Ошибка: ' + err.message;
            } finally {
                hideTyping();
            }
        }

        // ===== СОБЫТИЯ =====
        sendBtn.addEventListener('click', sendMessage);
        msgInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        clearBtn.addEventListener('click', clearChat);
        settingsBtn.addEventListener('click', () => { settingsModal.style.display = 'flex'; });

        addCharacterBtn.addEventListener('click', () => {
            modalCharName.value = '';
            modalCharDesc.value = '';
            modal.style.display = 'flex';
        });

        modalSaveBtn.addEventListener('click', () => {
            const name = modalCharName.value.trim();
            const desc = modalCharDesc.value.trim();
            if (name && desc) {
                addCharacter(name, desc);
                modal.style.display = 'none';
                showToast('✅ Персонаж "' + name + '" создан!');
            } else {
                showToast('❌ Заполните имя и описание');
            }
        });

        modalCancelBtn.addEventListener('click', () => modal.style.display = 'none');
        window.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

        // ===== ЗАПУСК =====
        loadModels();
    </script>
</body>
</html>"""

@app.get("/")
async def home():
    return HTMLResponse(HTML)

@app.post("/ask")
async def ask(request: dict):
    try:
        prompt = request.get("prompt")
        model = request.get("model")
        temperature = request.get("temperature", 0.7)
        history = request.get("history", [])
        character_description = request.get("character_description", "Ты полезный ассистент. Отвечай на русском кратко.")
        
        full_prompt = f"{character_description}\n\nСледуй своему описанию. Отвечай от первого лица, как этот персонаж.\n\n"
        for m in history:
            full_prompt += f"{'Пользователь' if m['role']=='user' else 'Ассистент'}: {m['content']}\n"
        full_prompt += f"Пользователь: {prompt}\nАссистент:"
        
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": model, "prompt": full_prompt, "stream": False, "temperature": temperature
        }, timeout=90)
        
        answer = r.json().get("response", "Нет ответа")
        answer = answer.strip()
        if answer.startswith('"') and answer.endswith('"'):
            answer = answer[1:-1]
        if answer.startswith("'") and answer.endswith("'"):
            answer = answer[1:-1]
        answer = answer.replace('\\"', '"').replace("\\'", "'")
        return answer
    except Exception as e:
        return f"Ошибка: {e}"

@app.post("/ask-stream")
async def ask_stream(request: dict):
    try:
        prompt = request.get("prompt")
        model = request.get("model")
        temperature = request.get("temperature", 0.7)
        character_description = request.get("character_description", "Ты полезный ассистент. Отвечай на русском кратко.")
        
        full_prompt = f"{character_description}\n\nСледуй своему описанию. Отвечай от первого лица, как этот персонаж.\n\nПользователь: {prompt}\nАссистент:"
        
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": True,
                "temperature": temperature
            },
            stream=True
        )
        
        def generate():
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        yield chunk
                    except:
                        pass
        
        return StreamingResponse(generate(), media_type="text/plain")
    except Exception as e:
        return f"Ошибка: {e}"

if __name__ == "__main__":
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    print("\n✅ Сервер NeoBrain запущен!")
    print("📌 Открыть в браузере: http://localhost:8000")
    if local_ip != "127.0.0.1":
        print(f"📌 В локальной сети: http://{local_ip}:8000")
    print("⏹️  Для остановки нажми Ctrl+C\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
