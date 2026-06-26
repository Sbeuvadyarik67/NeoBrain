from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import requests
import json
import uvicorn
import socket

app = FastAPI()

html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>AI Чат | NeoBrain</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', system-ui, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            transition: all 0.3s ease;
            margin-left: 0;
            transition: margin-left 0.3s ease;
        }
        body.chat-panel-open {
            margin-left: 260px;
        }
        /* --- Тема по умолчанию (Неон) --- */
        body.neon {
            background: radial-gradient(circle at 20% 30%, #0a0f1e, #03060c);
            color: #eef5ff;
        }
        body.neon .chat-glass {
            background: rgba(10, 20, 30, 0.65);
            border: 1px solid rgba(255, 0, 255, 0.6);
            box-shadow: 0 0 15px rgba(255, 0, 255, 0.3);
        }
        body.neon .bubble {
            background: #111a24dd;
            border: 1px solid rgba(255, 0, 255, 0.4);
        }
        body.neon .input-area input {
            background: #0e1a24;
            border: 1px solid magenta;
        }
        /* --- Тема Baby-doll (розовый + светло-голубой) --- */
        body.babydoll {
            background: linear-gradient(135deg, #ffe0f0, #e0f0ff);
            color: #5a3e5a;
        }
        body.babydoll .chat-glass {
            background: rgba(255, 240, 250, 0.85);
            border: 1px solid #ffb6c1;
            box-shadow: 0 0 15px #ffb6c1;
        }
        body.babydoll .bubble {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ffb6c1;
            color: #5a3e5a;
        }
        body.babydoll .input-area input {
            background: white;
            border: 1px solid #ffb6c1;
        }
        /* --- Тема Летняя (зелёный + оранжевый) --- */
        body.summer {
            background: linear-gradient(135deg, #c0e0a0, #ffcc80);
            color: #2d4a2d;
        }
        body.summer .chat-glass {
            background: rgba(255, 248, 225, 0.85);
            border: 1px solid #ffa500;
            box-shadow: 0 0 15px #ffa500;
        }
        body.summer .bubble {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ffa500;
            color: #2d4a2d;
        }
        body.summer .input-area input {
            background: white;
            border: 1px solid #ffa500;
        }
        /* --- Тема Пляжная (синий + жёлтый) --- */
        body.beach {
            background: linear-gradient(135deg, #b0e0ff, #fff0a0);
            color: #1a3a6a;
        }
        body.beach .chat-glass {
            background: rgba(255, 255, 240, 0.85);
            border: 1px solid #ffd700;
            box-shadow: 0 0 15px #ffd700;
        }
        body.beach .bubble {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ffd700;
            color: #1a3a6a;
        }
        body.beach .input-area input {
            background: white;
            border: 1px solid #ffd700;
        }
        /* --- Тема Цифровая (оранжевый + фиолетовый) --- */
        body.digital {
            background: linear-gradient(135deg, #ffaa70, #c080ff);
            color: #2e1a4a;
        }
        body.digital .chat-glass {
            background: rgba(0, 0, 0, 0.75);
            border: 1px solid #ff8c00;
            box-shadow: 0 0 15px #ff8c00;
        }
        body.digital .bubble {
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #ff8c00;
            color: #f0f0f0;
        }
        body.digital .input-area input {
            background: #1e1e2f;
            border: 1px solid #ff8c00;
        }
        /* --- Тема Творческая (розовый + оливково-зелёный) --- */
        body.creative {
            background: linear-gradient(135deg, #ffc0cb, #a0b080);
            color: #3a4a2a;
        }
        body.creative .chat-glass {
            background: rgba(255, 250, 240, 0.85);
            border: 1px solid #ffb6c1;
            box-shadow: 0 0 15px #ffb6c1;
        }
        body.creative .bubble {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ffb6c1;
            color: #3a4a2a;
        }
        body.creative .input-area input {
            background: white;
            border: 1px solid #ffb6c1;
        }
        /* --- Тема Тёплая (пудрово-розовый + оранжевый) --- */
        body.warm {
            background: linear-gradient(135deg, #ffd0d0, #ffe0b0);
            color: #5a3a2a;
        }
        body.warm .chat-glass {
            background: rgba(255, 250, 245, 0.85);
            border: 1px solid #ffaa77;
            box-shadow: 0 0 15px #ffaa77;
        }
        body.warm .bubble {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ffaa77;
            color: #5a3a2a;
        }
        body.warm .input-area input {
            background: white;
            border: 1px solid #ffaa77;
        }
        /* --- Общие стили (не зависят от темы) --- */
        .chat-glass {
            max-width: 1200px;
            width: 100%;
            height: 90vh;
            backdrop-filter: blur(14px);
            border-radius: 2rem;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .chat-header {
            padding: 0.8rem 1.8rem;
            background: rgba(0, 20, 30, 0.6);
            border-bottom: 1px solid currentColor;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: center;
        }
        .brand { display: flex; align-items: center; gap: 14px; margin-right: auto; }
        .neon-icon { font-size: 36px; }
        .brand-text h1 { font-size: 1.6rem; margin-bottom: 0; }
        .brand-text p { font-size: 0.75rem; }
        .character-selector {
            display: flex;
            gap: 0.8rem;
            align-items: center;
            background: #041018cc;
            padding: 0.8rem 1.8rem;
            border-bottom: 1px solid currentColor;
            flex-wrap: wrap;
        }
        .temperature-control {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            background: #041018cc;
            padding: 0.8rem 1.8rem;
            border-bottom: 1px solid currentColor;
        }
        .temp-slider {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .temp-slider input {
            flex: 1;
            cursor: pointer;
            height: 4px;
            border-radius: 5px;
        }
        .temp-presets {
            display: flex;
            gap: 0.8rem;
            justify-content: center;
            flex-wrap: wrap;
            margin: 0.5rem 0;
        }
        .temp-presets button {
            background: #1e293b;
            border: 1px solid currentColor;
            padding: 4px 12px;
            border-radius: 2rem;
            color: white;
            cursor: pointer;
            transition: all 0.2s;
        }
        .temp-presets button:hover {
            transform: scale(1.02);
        }
        .temp-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.7rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .controls {
            display: flex;
            gap: 0.8rem;
            align-items: center;
            flex-wrap: wrap;
        }
        .controls select, .controls button, .character-selector select, .character-selector button, .temperature-control button {
            background: #1e293b;
            border: 1px solid currentColor;
            padding: 8px 16px;
            border-radius: 2rem;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .controls button, .character-selector button { background: #2e7d32; border-color: #4caf50; }
        .status {
            background: rgba(0, 0, 0, 0.3);
            padding: 6px 14px;
            border-radius: 60px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
        }
        .led {
            width: 10px; height: 10px;
            background: #0f0;
            border-radius: 50%;
            box-shadow: 0 0 4px #0f0;
            animation: pulseGreen 1.5s infinite;
        }
        @keyframes pulseGreen {
            0% { opacity: 0.5; transform: scale(0.7);}
            100% { opacity: 1; transform: scale(1.2);}
        }
        .chat-window {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .msg {
            display: flex;
            gap: 12px;
            max-width: 80%;
            animation: slideUp 0.25s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(16px);}
            to { opacity: 1; transform: translateY(0);}
        }
        .user-msg { align-self: flex-end; flex-direction: row-reverse; }
        .ai-msg { align-self: flex-start; }
        .avatar {
            width: 42px; height: 42px;
            background: linear-gradient(145deg, #1e2a3a, #0a121f);
            border-radius: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
        }
        .bubble {
            padding: 10px 20px;
            border-radius: 24px;
            font-size: 0.95rem;
            backdrop-filter: blur(8px);
            transition: border 0.2s;
        }
        .bubble:hover {
            border-color: cyan;
            box-shadow: 0 0 8px cyan;
        }
        .user-msg .bubble {
            border-bottom-right-radius: 8px;
        }
        .ai-msg .bubble { border-bottom-left-radius: 8px; }
        .msg-time {
            font-size: 0.65rem;
            margin-top: 5px;
            padding-left: 56px;
        }
        .user-msg .msg-time { text-align: right; padding-right: 10px; }
        .typing-block {
            display: none;
            align-items: center;
            gap: 12px;
            margin-top: 8px;
        }
        .typing-dots {
            background: #111a24dd;
            backdrop-filter: blur(12px);
            padding: 10px 20px;
            border-radius: 30px;
            display: flex;
            gap: 8px;
        }
        .typing-dots span {
            width: 8px; height: 8px;
            background: #88ccff;
            border-radius: 50%;
            animation: wave 1.2s infinite;
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes wave {
            0%, 60%, 100% { opacity: 0.4; transform: translateY(0px);}
            30% { opacity: 1; transform: translateY(-4px);}
        }
        .input-area {
            background: #041018cc;
            border-top: 1px solid currentColor;
            padding: 1rem 1.5rem;
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .input-area input {
            flex: 1;
            padding: 12px 20px;
            border-radius: 60px;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.2s;
        }
        .input-area input:focus {
            box-shadow: 0 0 12px currentColor;
        }
        .input-area button {
            background: linear-gradient(95deg, #1e88e5, #0d47a1);
            border: none;
            padding: 10px 32px;
            border-radius: 60px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            transition: 0.2s;
        }
        .input-area button:hover {
            transform: scale(1.02);
            background: #42a5f5;
        }
        .chat-window::-webkit-scrollbar { width: 6px; }
        .chat-window::-webkit-scrollbar-track { background: #021018; }
        .chat-window::-webkit-scrollbar-thumb { background: currentColor; border-radius: 12px; }
        @media (max-width: 768px) {
            .chat-glass { height: 95vh; border-radius: 1rem; }
            .chat-header { padding: 0.5rem 1rem; }
            .brand-text h1 { font-size: 1.2rem; }
            .controls select, .controls button, .character-selector select, .character-selector button, .temp-presets button { padding: 4px 10px; font-size: 0.7rem; }
            .temperature-control { padding: 0.5rem 1rem; }
            .temp-labels { font-size: 0.6rem; flex-wrap: wrap; justify-content: center; }
            .msg { max-width: 95%; }
            .bubble { font-size: 0.85rem; padding: 8px 12px; word-break: break-word; }
            .avatar { width: 36px; height: 36px; font-size: 1.4rem; }
            .input-area { padding: 0.5rem 1rem; }
            .input-area input { padding: 8px 12px; font-size: 0.85rem; }
            .input-area button { padding: 8px 20px; font-size: 0.85rem; }
            body.chat-panel-open { margin-left: 0; }
            .chats-panel { width: 85%; max-width: 280px; }
        }
        @media (max-width: 480px) {
            .chat-header { flex-direction: column; align-items: stretch; gap: 0.5rem; }
            .brand { justify-content: center; }
            .controls { justify-content: center; }
            .character-selector { justify-content: center; }
            .temp-presets { gap: 0.4rem; }
            .temp-labels { flex-direction: column; align-items: center; }
        }
        /* --- Принудительные стили для читаемого текста в элементах управления --- */
        .controls select, .controls button, .character-selector select, .character-selector button, .temperature-control button, .temp-presets button {
            color: #ffffff !important;
            background: #1e293b !important;
            border-color: currentColor;
        }
        .controls select option, .character-selector select option {
            background: #1e293b;
            color: #ffffff;
        }
        body.digital .controls select, body.digital .controls button,
        body.digital .character-selector select, body.digital .character-selector button,
        body.digital .temperature-control button, body.digital .temp-presets button {
            color: #ffffff !important;
            background: #2a2a3a !important;
        }
        body.babydoll .controls select, body.babydoll .controls button,
        body.babydoll .character-selector select, body.babydoll .character-selector button,
        body.babydoll .temperature-control button, body.babydoll .temp-presets button {
            color: #2d2d2d !important;
            background: #ffe0f0 !important;
        }
        body.summer .controls select, body.summer .controls button,
        body.summer .character-selector select, body.summer .character-selector button,
        body.summer .temperature-control button, body.summer .temp-presets button {
            color: #2d4a2d !important;
            background: #ffcc80 !important;
        }
        body.beach .controls select, body.beach .controls button,
        body.beach .character-selector select, body.beach .character-selector button,
        body.beach .temperature-control button, body.beach .temp-presets button {
            color: #1a3a6a !important;
            background: #fff0a0 !important;
        }
        body.creative .controls select, body.creative .controls button,
        body.creative .character-selector select, body.creative .character-selector button,
        body.creative .temperature-control button, body.creative .temp-presets button {
            color: #3a4a2a !important;
            background: #ffc0cb !important;
        }
        body.warm .controls select, body.warm .controls button,
        body.warm .character-selector select, body.warm .character-selector button,
        body.warm .temperature-control button, body.warm .temp-presets button {
            color: #5a3a2a !important;
            background: #ffd0d0 !important;
        }
    
        /* Поле ввода на тёмных темах – светлый фон, чёрный текст */
        body.neon .input-area input,
        body.digital .input-area input {
            background: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #cccccc !important;
        }
        body.neon .input-area input:focus,
        body.digital .input-area input:focus {
            border-color: #4caf50 !important;
            box-shadow: 0 0 8px #4caf50 !important;
        }
        /* Эффект наклона кнопок за курсором */
        .tilt-button {
            transition: transform 0.1s linear;
            will-change: transform;
            backface-visibility: hidden;
        }
        
        /* ===== ВОЛНЫ ПО ВСЕМ КРАЯМ (С ПЛАВНЫМ ЗАТУХАНИЕМ) ===== */
        .waves-wrapper {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 1;
            transition: opacity 1s ease;
        }
        .waves-wrapper.hidden {
            opacity: 0;
        }
        
        .waves-decor {
            position: absolute;
            background: repeating-linear-gradient(100deg, 
                rgba(0, 255, 255, 0.5) 0px,
                rgba(0, 255, 255, 0.5) 6px,
                transparent 6px,
                transparent 30px);
            animation: waveMove 4s ease-in-out infinite;
            background-size: 400% 100%;
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
        }
        
        .waves-decor.bottom {
            bottom: 0;
            left: 0;
            width: 100%;
            height: 150px;
            mask-image: radial-gradient(ellipse at 50% 100%, black 20%, transparent 80%);
            -webkit-mask-image: radial-gradient(ellipse at 50% 100%, black 20%, transparent 80%);
        }
        
        .waves-decor.top {
            top: 0;
            left: 0;
            width: 100%;
            height: 150px;
            mask-image: radial-gradient(ellipse at 50% 0%, black 20%, transparent 80%);
            -webkit-mask-image: radial-gradient(ellipse at 50% 0%, black 20%, transparent 80%);
        }
        
        .waves-decor.left {
            top: 0;
            left: 0;
            width: 120px;
            height: 100%;
            background: repeating-linear-gradient(0deg, 
                rgba(0, 255, 255, 0.5) 0px,
                rgba(0, 255, 255, 0.5) 6px,
                transparent 6px,
                transparent 30px);
            mask-image: radial-gradient(ellipse at 0% 50%, black 20%, transparent 80%);
            -webkit-mask-image: radial-gradient(ellipse at 0% 50%, black 20%, transparent 80%);
            animation: waveMoveVertical 4s ease-in-out infinite;
            background-size: 100% 400%;
        }
        
        .waves-decor.right {
            top: 0;
            right: 0;
            width: 120px;
            height: 100%;
            background: repeating-linear-gradient(0deg, 
                rgba(0, 255, 255, 0.5) 0px,
                rgba(0, 255, 255, 0.5) 6px,
                transparent 6px,
                transparent 30px);
            mask-image: radial-gradient(ellipse at 100% 50%, black 20%, transparent 80%);
            -webkit-mask-image: radial-gradient(ellipse at 100% 50%, black 20%, transparent 80%);
            animation: waveMoveVertical 4s ease-in-out infinite;
            background-size: 100% 400%;
        }
        
        @keyframes waveMove {
            0% { background-position: 0% 0%; }
            50% { background-position: 100% 0%; }
            100% { background-position: 0% 0%; }
        }
        
        @keyframes waveMoveVertical {
            0% { background-position: 0% 0%; }
            50% { background-position: 0% 100%; }
            100% { background-position: 0% 0%; }
        }
        
        /* --- Увеличение шрифта для мелких текстовых элементов --- */
        .temp-labels span,
        .temp-labels,
        .temp-presets button,
        .temperature-control .temp-labels,
        .msg-time,
        .status,
        .character-selector label,
        .modal-content p,
        .modal-content label,
        .accessibility-btn,
        #toggleWaves + label,
        #closeDonateModal,
        #copyPhoneBtn {
            font-size: 0.95rem !important;
        }

        /* Температурные пресеты чуть крупнее */
        .temp-presets button {
            font-size: 0.9rem !important;
            padding: 6px 14px !important;
        }

        /* Время сообщений (не перегружать, но читаемо) */
        .msg-time {
            font-size: 0.75rem !important;
        }

        /* Ссылка на ВК в модалке доната */
        #donateModal a {
            font-size: 0.95rem !important;
        }
        
        /* Панель чатов — стильный полупрозрачный вариант */
        .chats-panel {
            position: fixed;
            left: 0;
            top: 0;
            width: 260px;
            height: 100vh;
            background: rgba(10, 20, 40, 0.85);
            backdrop-filter: blur(16px);
            border-right: 1px solid rgba(0, 255, 255, 0.3);
            box-shadow: 2px 0 15px rgba(0, 255, 255, 0.1);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            padding: 1rem;
            padding-top: 70px;
            gap: 0.5rem;
            overflow-y: auto;
            transform: translateX(-100%);
            transition: transform 0.3s ease;
        }
        .chats-panel.open {
            transform: translateX(0%);
        }
        .toggle-chats-btn {
            position: fixed;
            left: 10px;
            top: 10px;
            z-index: 1001;
            background: #4caf50;
            border: 1px solid #ffffff;
            color: white;
            padding: 6px 12px;
            border-radius: 2rem;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: bold;
            box-shadow: 0 0 8px rgba(76, 175, 80, 0.5);
        }
        .toggle-chats-btn:hover {
            background: #2e7d32;
            transform: scale(1.02);
        }
        .new-chat-btn {
            width: 100%;
            background: #f39c12;
            border: none;
            padding: 10px;
            border-radius: 2rem;
            cursor: pointer;
            font-weight: bold;
            margin-bottom: 0.5rem;
            color: #1e1e2f;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .new-chat-btn:hover {
            background: #e67e22;
            transform: scale(1.01);
        }
        .chat-item {
            padding: 10px 12px;
            margin: 4px 0;
            border-radius: 1.5rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .chat-item.active {
            background: rgba(0, 255, 255, 0.15);
            border: 1px solid rgba(0, 255, 255, 0.5);
            box-shadow: 0 0 8px rgba(0, 255, 255, 0.3);
        }
        .chat-item:hover {
            background: rgba(0, 255, 255, 0.1);
            border-color: rgba(0, 255, 255, 0.4);
            transform: translateX(4px);
        }
        .chat-name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .chat-actions button {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            padding: 4px 6px;
            border-radius: 0.75rem;
            transition: all 0.2s;
            color: #ccc;
        }
        .chat-actions button:hover {
            background: rgba(255,255,255,0.15);
            color: #f39c12;
            transform: scale(1.05);
        }
    </style>
</head>
<body class="neon">
    <!-- ВОЛНЫ (обёртка) -->
    <div class="waves-wrapper" id="wavesWrapper">
        <div class="waves-decor top"></div>
        <div class="waves-decor bottom"></div>
        <div class="waves-decor left"></div>
        <div class="waves-decor right"></div>
    </div>

    <div class="chat-glass">
        <div class="chat-header">
            <div class="brand">
                <div class="neon-icon">🧠✨</div>
                <div class="brand-text">
                    <h1>AI Чат — NeoBrain</h1>
                    <p>персонажи · локальная нейросеть · несколько чатов</p>
                </div>
            </div>
            <div class="controls">
                <select id="modelSelect">
                    <option value="qwen2.5-coder:7b">🧠 Умная модель (7b)</option>
                    <option value="qwen2.5-coder:1.5b">🌿 Быстрая модель (1.5b)</option>
                </select>
                <select id="themeSelect">
                    <option value="neon">🌙 Неон (по умолчанию)</option>
                    <option value="babydoll">🎀 Baby-doll</option>
                    <option value="summer">☀️ Летняя</option>
                    <option value="beach">🏖️ Пляжная</option>
                    <option value="digital">📱 Цифровая</option>
                    <option value="creative">🎨 Творческая</option>
                    <option value="warm">🔥 Тёплая</option>
                </select>
                <div class="status">
                    <span class="led"></span> онлайн
                </div>
                <button id="clearChatBtn">🗑 Очистить чат</button>
                <button id="donateBtn" style="background: #f39c12; border: none; padding: 8px 16px; border-radius: 2rem; font-weight: bold; cursor: pointer;">💖 Поддержать проект</button>
                <button id="settingsBtn" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;" title="Настройки">⚙️</button>
            </div>
        </div>
        <div class="character-selector">
            <select id="characterSelect"></select>
            <button id="addCharacterBtn">➕ Создать персонажа</button>
        </div>
        <div class="temperature-control">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem;">
                <div style="color: #e0e0e0; font-weight: 500;">🌡️ Температура (1 ❄️ – 10 🔥):</div>
                <button id="toggleTempBtn" style="background: none; border: none; font-size: 1.2rem; cursor: pointer;">▲</button>
            </div>
            <div id="tempContent" style="display: block;">
                <div class="temp-slider">
                    <span>❄️</span>
                    <input type="range" id="temperatureSlider" min="1" max="10" step="1" value="5">
                    <span>🔥</span>
                    <span id="tempValueDisplay" style="font-weight: bold; min-width: 2rem;">5</span>
                </div>
                <div class="temp-presets">
                    <button type="button" class="temp-preset" data-temp="1">❄️ Холодный (чётко)</button>
                    <button type="button" class="temp-preset" data-temp="5">🌿 Нейтральный (баланс)</button>
                    <button type="button" class="temp-preset" data-temp="10">🔥 Горячий (креативно)</button>
                </div>
                <div class="temp-labels">
                    <span>❄️ Холодный — коротко, по делу, без лишних слов</span>
                    <span>🌿 Нейтральный — спокойный, умеренный</span>
                    <span>🔥 Горячий — эмоционально, творчески, возможны шутки и стикеры</span>
                </div>
            </div>
        </div>
        <div class="chat-window" id="chatWindow">
            <div class="msg ai-msg">
                <div class="avatar">🤖</div>
                <div class="bubble">Привет! Я твой нейро-помощник. Выбери или создай персонажа, настрой температуру и тему — и я буду общаться в нужном стиле 🤍</div>
            </div>
            <div class="msg-time">только что</div>
        </div>
        <div class="typing-block" id="typingBlock">
            <div class="avatar" style="background:#1a2a3a;">🤖</div>
            <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
        <div class="input-area">
            <input type="text" id="msgInput" placeholder="Напиши что-нибудь... 🔮" autofocus>
            <button id="sendBtn">💬 Отправить</button>
        </div>
    </div>

    <!-- Панель чатов -->
    <div id="chatsPanel" class="chats-panel">
        <button id="newChatBtn" class="new-chat-btn">➕ Новый чат</button>
        <div id="chatsList"></div>
    </div>
    <button id="toggleChatsBtn" class="toggle-chats-btn">☰ Чаты</button>

    <!-- Модальное окно выбора режима цветовосприятия -->
    <div id="accessibilityModal" class="modal" style="display: none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); backdrop-filter:blur(4px); justify-content:center; align-items:center; z-index:2000;">
        <div class="modal-content" style="background:#1e1e2f; border:2px solid #4caf50; border-radius:2rem; padding:2rem; width:90%; max-width:500px; text-align:center; color:white;">
            <h2 style="margin-top:0;">👋 Добро пожаловать!</h2>
            <p style="margin:1rem 0;">Чтобы вам было комфортно пользоваться чатом, выберите режим отображения:</p>
            <div style="display:flex; flex-direction:column; gap:0.8rem; margin:1.5rem 0;">
                <button class="accessibility-btn" data-mode="neon" style="background:#4caf50; border:none; padding:10px; border-radius:2rem; cursor:pointer;">🌙 Классическая тема</button>
                <button class="accessibility-btn" data-mode="tritanopia" style="background:#ffaa88; border:none; padding:10px; border-radius:2rem; cursor:pointer;">👁️ Режим для тританопии (сине-жёлтая слепота)</button>
            </div>
            <div style="margin-top: 1rem; padding-top: 0.5rem; border-top: 1px solid #4caf50;">
                <p style="margin: 0.5rem 0;"><strong>✨ Эффекты:</strong></p>
                <label style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; cursor: pointer;">
                    <input type="checkbox" id="toggleWaves" checked> 🌊 Декоративные волны
                </label>
            </div>
            <p style="font-size:0.8rem; opacity:0.7;">*Настройку можно изменить в любое время в меню ⚙️</p>
        </div>
    </div>

    <!-- Модальное окно добавления персонажа -->
    <div id="characterModal" class="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); justify-content:center; align-items:center; z-index:1000;">
        <div class="modal-content" style="background:#0f172a; border:1px solid cyan; border-radius:2rem; padding:2rem; width:90%; max-width:400px; color:white;">
            <h3>Новый персонаж</h3>
            <input type="text" id="charName" placeholder="Имя персонажа" style="width:100%; margin:0.5rem 0; padding:0.6rem; background:#1e293b; border:1px solid cyan; border-radius:1rem; color:white;">
            <textarea id="charDesc" rows="3" placeholder="Опиши характер, стиль речи, роль..." style="width:100%; margin:0.5rem 0; padding:0.6rem; background:#1e293b; border:1px solid cyan; border-radius:1rem; color:white;"></textarea>
            <div class="modal-buttons" style="display:flex; gap:1rem; margin-top:1rem;">
                <button id="saveCharacterBtn" style="flex:1; padding:0.5rem; border-radius:2rem; cursor:pointer;">Сохранить</button>
                <button id="cancelModalBtn" style="flex:1; padding:0.5rem; border-radius:2rem; cursor:pointer;">Отмена</button>
            </div>    
        </div>
    </div>

    <!-- Модальное окно для пожертвований -->
    <div id="donateModal" class="modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); backdrop-filter:blur(4px); justify-content:center; align-items:center; z-index:2000;">
        <div class="modal-content" style="background:#1e1e2f; border:2px solid #f39c12; border-radius:2rem; padding:2rem; width:90%; max-width:400px; text-align:center; color:white;">
            <h2 style="margin-top:0;">💖 Поддержать NeoBrain</h2>
            <p style="margin:1rem 0;">Ваша помощь помогает проекту развиваться дальше. Спасибо! 🙏</p>
            <div style="background:#2a2a3a; padding:1rem; border-radius:1rem; margin:1rem 0;">
                <p style="margin:0.5rem 0;"><strong>Банк:</strong> ВТБ</p>
                <p style="margin:0.5rem 0;"><strong>Номер телефона:</strong> <span id="phoneNumber" style="font-size:1.2rem; font-weight:bold;">+7 927 218 25 49</span></p>
                <button id="copyPhoneBtn" style="margin-top:0.5rem; background:#f39c12; border:none; padding:5px 15px; border-radius:2rem; cursor:pointer;">📋 Скопировать номер</button>
            </div>
            <div style="margin-top: 1rem; padding-top: 0.5rem; border-top: 1px solid #f39c12;">
                <p style="margin: 0.5rem 0;"><strong>📌 Связь со мной:</strong></p>
                <a href="https://vk.com/v_rusich007" target="_blank" style="display: inline-block; background: #4caf50; color: white; text-decoration: none; padding: 8px 20px; border-radius: 2rem; margin-top: 5px; font-size: 0.9rem;">📱 Написать в ВКонтакте</a>
                <p style="margin: 0.5rem 0; font-size: 0.75rem; opacity: 0.7;">По вопросам сотрудничества, идей и предложений</p>
            </div>
            <button id="closeDonateModal" style="margin-top:1rem; background:#4caf50; border:none; padding:8px 20px; border-radius:2rem; cursor:pointer;">Закрыть</button>
        </div>
    </div>
       
    <script>
        // --- ВСПЛЫВАЮЩЕЕ УВЕДОМЛЕНИЕ (TOAST) ---
        function showToast(message, bgColor = '#f39c12') {
            const oldToast = document.querySelector('.toast-notification');
            if (oldToast) oldToast.remove();
            
            const toast = document.createElement('div');
            toast.className = 'toast-notification';
            toast.innerText = message;
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${bgColor};
                color: #1e1e2f;
                padding: 12px 20px;
                border-radius: 30px;
                font-weight: bold;
                font-size: 0.9rem;
                z-index: 10000;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                backdrop-filter: blur(8px);
                border: 1px solid rgba(255,255,255,0.3);
                opacity: 0;
                transform: translateX(50px);
                transition: opacity 0.3s ease, transform 0.3s ease;
                pointer-events: none;
            `;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '1';
                toast.style.transform = 'translateX(0)';
            }, 10);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(50px)';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }
        
        // --- Персонажи (localStorage) ---
        let characters = [];
        let activeCharacterId = null;
        const STORAGE_CHARS = 'ai_chat_characters';
        const STORAGE_ACTIVE = 'ai_chat_active_character';
        
        // --- Температура ---
        const tempSlider = document.getElementById('temperatureSlider');
        const tempDisplay = document.getElementById('tempValueDisplay');
        const STORAGE_TEMP = 'ai_chat_temperature';
        
        function loadTemperature() {
            const savedTemp = localStorage.getItem(STORAGE_TEMP);
            if (savedTemp !== null) {
                const val = parseInt(savedTemp);
                tempSlider.value = val;
                tempDisplay.innerText = val;
            } else {
                tempSlider.value = 5;
                tempDisplay.innerText = 5;
            }
        }
        
        function saveTemperature(value) {
            localStorage.setItem(STORAGE_TEMP, value);
        }
        
        tempSlider.addEventListener('input', (e) => {
            const val = e.target.value;
            tempDisplay.innerText = val;
            saveTemperature(val);
        });
        
        // --- Предустановки температуры (пресеты) ---
        const presetButtons = document.querySelectorAll('.temp-preset');
        presetButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const newTemp = parseInt(btn.getAttribute('data-temp'));
                tempSlider.value = newTemp;
                tempDisplay.innerText = newTemp;
                saveTemperature(newTemp);
            });
        });
        
        // --- Сворачивание блока температуры ---
        const toggleBtn = document.getElementById('toggleTempBtn');
        const tempContent = document.getElementById('tempContent');
        const STORAGE_TEMP_COLLAPSED = 'ai_chat_temp_collapsed';
        
        const isCollapsed = localStorage.getItem(STORAGE_TEMP_COLLAPSED) === 'true';
        if (isCollapsed) {
            tempContent.style.display = 'none';
            toggleBtn.innerText = '▼';
        } else {
            tempContent.style.display = 'block';
            toggleBtn.innerText = '▲';
        }
        
        toggleBtn.addEventListener('click', () => {
            const currentlyCollapsed = tempContent.style.display === 'none';
            if (currentlyCollapsed) {
                tempContent.style.display = 'block';
                toggleBtn.innerText = '▲';
                localStorage.setItem(STORAGE_TEMP_COLLAPSED, 'false');
            } else {
                tempContent.style.display = 'none';
                toggleBtn.innerText = '▼';
                localStorage.setItem(STORAGE_TEMP_COLLAPSED, 'true');
            }
        });
        
        // --- Темы оформления ---
        const themeSelect = document.getElementById('themeSelect');
        const STORAGE_THEME = 'ai_chat_theme';
        
        function loadTheme() {
            const savedTheme = localStorage.getItem(STORAGE_THEME);
            if (savedTheme && themeSelect.querySelector(`option[value="${savedTheme}"]`)) {
                document.body.className = savedTheme;
                themeSelect.value = savedTheme;
            } else {
                document.body.className = 'neon';
                themeSelect.value = 'neon';
            }
        }
        
        function saveTheme(theme) {
            localStorage.setItem(STORAGE_THEME, theme);
        }
        
        themeSelect.addEventListener('change', (e) => {
            const newTheme = e.target.value;
            document.body.className = newTheme;
            saveTheme(newTheme);
        });
        
        // --- Настройки доступности (цветовая слепота) ---
        const accessibilityModal = document.getElementById('accessibilityModal');
        const settingsBtn = document.getElementById('settingsBtn');
        const STORAGE_ACCESS_MODE = 'ai_chat_accessibility_mode';
        
        function setAccessibilityMode(mode) {
            document.body.classList.remove('tritanopia');
            if (mode !== 'neon') {
                document.body.classList.add(mode);
            }
            localStorage.setItem(STORAGE_ACCESS_MODE, mode);
        }
        
        function loadAccessibilityMode() {
            const savedMode = localStorage.getItem(STORAGE_ACCESS_MODE);
            if (savedMode) {
                setAccessibilityMode(savedMode);
                if (accessibilityModal) accessibilityModal.style.display = 'none';
            } else {
                if (accessibilityModal) accessibilityModal.style.display = 'flex';
            }
        }
        
        document.querySelectorAll('.accessibility-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.getAttribute('data-mode');
                setAccessibilityMode(mode);
                if (accessibilityModal) accessibilityModal.style.display = 'none';
            });
        });
        
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                if (accessibilityModal) accessibilityModal.style.display = 'flex';
            });
        }
        
        // Закрытие модального окна при клике вне его
        window.addEventListener('click', function(event) {
            if (event.target === accessibilityModal) {
                accessibilityModal.style.display = 'none';
            }
        });
        
        // --- Персонажи ---
        function loadCharacters() {
            const saved = localStorage.getItem(STORAGE_CHARS);
            if (saved) {
                characters = JSON.parse(saved);
            } else {
                characters = [{ id: 'default', name: 'Помощник', description: 'Ты дружелюбный и умный ассистент. Отвечаешь кратко, но по делу.' }];
                saveCharacters();
            }
            renderCharacterSelect();
            loadActiveCharacter();
        }
        
        function saveCharacters() {
            localStorage.setItem(STORAGE_CHARS, JSON.stringify(characters));
        }
        
        function renderCharacterSelect() {
            const select = document.getElementById('characterSelect');
            select.innerHTML = '';
            characters.forEach(char => {
                const option = document.createElement('option');
                option.value = char.id;
                option.textContent = char.name;
                if (activeCharacterId === char.id) option.selected = true;
                select.appendChild(option);
            });
        }
        
        function setActiveCharacter(id) {
            activeCharacterId = id;
            localStorage.setItem(STORAGE_ACTIVE, id);
            renderCharacterSelect();
        }
        
        function loadActiveCharacter() {
            const saved = localStorage.getItem(STORAGE_ACTIVE);
            if (saved && characters.some(c => c.id === saved)) {
                activeCharacterId = saved;
            } else if (characters.length > 0) {
                activeCharacterId = characters[0].id;
            }
            renderCharacterSelect();
        }
        
        function addCharacter(name, description) {
            const id = Date.now().toString();
            characters.push({ id, name, description });
            saveCharacters();
            renderCharacterSelect();
            setActiveCharacter(id);
        }
        
        // --- НОВАЯ СИСТЕМА ЧАТОВ ---
        const STORAGE_CHATS = 'neobrain_chats';
        const STORAGE_ACTIVE_CHAT = 'neobrain_active_chat';
        
        let chats = [];
        let activeChatId = null;
        
        function initChats() {
            const savedChats = localStorage.getItem(STORAGE_CHATS);
            if (savedChats) {
                chats = JSON.parse(savedChats);
            } else {
                const oldMessages = JSON.parse(localStorage.getItem('ai_chat_messages') || '[]');
                const defaultCharacter = characters.find(c => c.id === 'default') || characters[0];
                const defaultChat = {
                    id: Date.now().toString(),
                    name: 'Основной чат',
                    characterId: defaultCharacter?.id || 'default',
                    messages: oldMessages,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                };
                chats = [defaultChat];
                localStorage.setItem(STORAGE_CHATS, JSON.stringify(chats));
                localStorage.removeItem('ai_chat_messages');
            }
            
            const savedActive = localStorage.getItem(STORAGE_ACTIVE_CHAT);
            if (savedActive && chats.some(c => c.id === savedActive)) {
                activeChatId = savedActive;
            } else if (chats.length > 0) {
                activeChatId = chats[0].id;
            }
            saveActiveChatId();
            renderChatList();
            loadCurrentChatMessages();
        }
        
        function saveChats() {
            localStorage.setItem(STORAGE_CHATS, JSON.stringify(chats));
        }
        
        function saveActiveChatId() {
            if (activeChatId) localStorage.setItem(STORAGE_ACTIVE_CHAT, activeChatId);
        }
        
        function createNewChat() {
            const selectedCharId = characterSelect.value;
            const selectedChar = characters.find(c => c.id === selectedCharId);
            const newChat = {
                id: Date.now().toString(),
                name: `Чат с ${selectedChar?.name || 'помощником'}`,
                characterId: selectedCharId,
                messages: [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            chats.push(newChat);
            saveChats();
            activeChatId = newChat.id;
            saveActiveChatId();
            renderChatList();
            loadCurrentChatMessages();
            showToast('✅ Новый чат создан');
        }
        
        function switchToChat(chatId) {
            if (!chats.find(c => c.id === chatId)) return;
            activeChatId = chatId;
            saveActiveChatId();
            renderChatList();
            loadCurrentChatMessages();
        }
        
        function deleteChat(chatId) {
            if (chats.length === 1) {
                alert('Нельзя удалить последний чат');
                return;
            }
            if (confirm('🗑 Удалить этот чат?')) {
                chats = chats.filter(c => c.id !== chatId);
                if (activeChatId === chatId) {
                    activeChatId = chats[0].id;
                    saveActiveChatId();
                }
                saveChats();
                renderChatList();
                loadCurrentChatMessages();
                showToast('🗑 Чат удалён');
            }
        }
        
        function renameChat(chatId, newName) {
            const chat = chats.find(c => c.id === chatId);
            if (chat) {
                chat.name = newName.trim() || 'Безымянный чат';
                saveChats();
                renderChatList();
                showToast('✏️ Чат переименован');
            }
        }
        
        function loadCurrentChatMessages() {
            const currentChat = chats.find(c => c.id === activeChatId);
            if (!currentChat) return;
            
            const chatWindow = document.getElementById('chatWindow');
            chatWindow.innerHTML = '';
            if (currentChat.messages.length === 0) {
                chatWindow.innerHTML = `
                    <div class="msg ai-msg">
                        <div class="avatar">🤖</div>
                        <div class="bubble">Привет! Я твой нейро-помощник. Выбери или создай персонажа, настрой температуру и тему — и я буду общаться в нужном стиле 🤍</div>
                    </div>
                    <div class="msg-time">только что</div>
                `;
            } else {
                for (const msg of currentChat.messages) {
                    const msgDiv = document.createElement('div');
                    msgDiv.className = `msg ${msg.isUser ? 'user-msg' : 'ai-msg'}`;
                    const avatar = document.createElement('div');
                    avatar.className = 'avatar';
                    avatar.innerText = msg.isUser ? '👤' : '🤖';
                    const bubble = document.createElement('div');
                    bubble.className = 'bubble';
                    bubble.innerText = msg.text;
                    msgDiv.appendChild(avatar);
                    msgDiv.appendChild(bubble);
                    chatWindow.appendChild(msgDiv);
                    
                    const timeDiv = document.createElement('div');
                    timeDiv.className = 'msg-time';
                    timeDiv.innerText = msg.time;
                    chatWindow.appendChild(timeDiv);
                }
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }
        }
        
        function saveMessageToCurrentChat(text, isUser, timeText) {
            const currentChat = chats.find(c => c.id === activeChatId);
            if (currentChat) {
                currentChat.messages.push({ text, isUser, time: timeText });
                currentChat.updatedAt = new Date().toISOString();
                saveChats();
            }
        }
        
        function renderChatList() {
            const container = document.getElementById('chatsList');
            if (!container) return;
            
            container.innerHTML = '';
            chats.forEach(chat => {
                const chatDiv = document.createElement('div');
                chatDiv.className = 'chat-item';
                if (activeChatId === chat.id) chatDiv.classList.add('active');
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'chat-name';
                nameSpan.innerText = chat.name;
                nameSpan.onclick = () => switchToChat(chat.id);
                
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'chat-actions';
                
                const renameBtn = document.createElement('button');
                renameBtn.innerText = '✏️';
                renameBtn.title = 'Переименовать';
                renameBtn.onclick = (e) => {
                    e.stopPropagation();
                    const newName = prompt('Новое название:', chat.name);
                    if (newName && newName.trim()) renameChat(chat.id, newName);
                };
                
                const deleteBtn = document.createElement('button');
                deleteBtn.innerText = '🗑️';
                deleteBtn.title = 'Удалить';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteChat(chat.id);
                };
                
                actionsDiv.appendChild(renameBtn);
                actionsDiv.appendChild(deleteBtn);
                chatDiv.appendChild(nameSpan);
                chatDiv.appendChild(actionsDiv);
                container.appendChild(chatDiv);
            });
        }
        
        // --- Функции чата (переопределяем addMessage и sendMessage) ---
        function addMessage(text, isUser) {
            const chatWindow = document.getElementById('chatWindow');
            const msgDiv = document.createElement('div');
            msgDiv.className = `msg ${isUser ? 'user-msg' : 'ai-msg'}`;
            const avatar = document.createElement('div');
            avatar.className = 'avatar';
            avatar.innerText = isUser ? '👤' : '🤖';
            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.innerText = text;
            msgDiv.appendChild(avatar);
            msgDiv.appendChild(bubble);
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'msg-time';
            const now = new Date();
            const timeText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            timeDiv.innerText = timeText;
            
            chatWindow.appendChild(msgDiv);
            chatWindow.appendChild(timeDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
            
            saveMessageToCurrentChat(text, isUser, timeText);
            
            if (!isUser) {
                const copyBtn = document.createElement('button');
                copyBtn.innerText = '📋';
                copyBtn.title = 'Копировать ответ';
                copyBtn.style.cssText = 'background: none; border: none; cursor: pointer; font-size: 1.2rem; margin-left: 8px; padding: 4px;';
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(text);
                    showToast('✅ Ответ скопирован!');
                };
                bubble.appendChild(copyBtn);
            }
        }
        
        function clearChat() {
            if (confirm('🧹 Вы уверены, что хотите очистить текущий чат?')) {
                const currentChat = chats.find(c => c.id === activeChatId);
                if (currentChat) {
                    currentChat.messages = [];
                    saveChats();
                    loadCurrentChatMessages();
                    showToast('🧹 Чат очищен');
                }
            }
        }
        
        function showTyping() {
            const typingBlock = document.getElementById('typingBlock');
            typingBlock.style.display = 'flex';
            const chatWindow = document.getElementById('chatWindow');
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
        
        function hideTyping() {
            const typingBlock = document.getElementById('typingBlock');
            typingBlock.style.display = 'none';
        }
        
        async function sendMessage() {
            const msgInput = document.getElementById('msgInput');
            const text = msgInput.value.trim();
            if (!text) return;
            
            const currentChat = chats.find(c => c.id === activeChatId);
            if (!currentChat) return;
            
            const selectedChar = characters.find(c => c.id === currentChat.characterId);
            if (!selectedChar) {
                addMessage('⚠️ Сначала создай или выбери персонажа', false);
                return;
            }
            
            const temp = parseFloat(tempSlider.value);
            const temperatureValue = 0.1 + (temp - 1) * 0.1;
            
            const messages = currentChat.messages || [];
            const lastMessages = messages.slice(-5);
            const history = lastMessages.map(msg => ({
                role: msg.isUser ? 'user' : 'assistant',
                content: msg.text
            }));
            
            addMessage(text, true);
            msgInput.value = '';
            msgInput.focus();
            showTyping();
            
            const chatWindow = document.getElementById('chatWindow');
            const msgDiv = document.createElement('div');
            msgDiv.className = 'msg ai-msg';
            const avatar = document.createElement('div');
            avatar.className = 'avatar';
            avatar.innerText = '🤖';
            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.innerText = '';
            msgDiv.appendChild(avatar);
            msgDiv.appendChild(bubble);
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'msg-time';
            const now = new Date();
            timeDiv.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            chatWindow.appendChild(msgDiv);
            chatWindow.appendChild(timeDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
            
            let fullAnswer = '';
            
            try {
                const modelSelect = document.getElementById('modelSelect');
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: text,
                        model: modelSelect.value,
                        character_description: selectedChar.description,
                        temperature: temperatureValue,
                        history: history
                    })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    fullAnswer += chunk;
                    bubble.innerText = fullAnswer;
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                }
                
                const finalTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                saveMessageToCurrentChat(fullAnswer, false, finalTime);
                
                const copyBtn = document.createElement('button');
                copyBtn.innerText = '📋';
                copyBtn.title = 'Копировать ответ';
                copyBtn.style.cssText = 'background: none; border: none; cursor: pointer; font-size: 1.2rem; margin-left: 8px; padding: 4px;';
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(fullAnswer);
                    showToast('✅ Ответ скопирован!');
                };
                bubble.appendChild(copyBtn);
                
            } catch (err) {
                bubble.innerText = '⚠️ Ошибка соединения с сервером';
                console.error(err);
            } finally {
                hideTyping();
            }
        }
        
        // --- Управление панелью чатов ---
        const chatsPanel = document.getElementById('chatsPanel');
        const toggleChatsBtn = document.getElementById('toggleChatsBtn');
        
        toggleChatsBtn.addEventListener('click', () => {
            chatsPanel.classList.toggle('open');
        });
        
        document.getElementById('newChatBtn')?.addEventListener('click', () => createNewChat());
        
        // --- ПОЖЕРТВОВАНИЯ ---
        const donateBtn = document.getElementById('donateBtn');
        const donateModal = document.getElementById('donateModal');
        const closeDonateModal = document.getElementById('closeDonateModal');
        const copyPhoneBtn = document.getElementById('copyPhoneBtn');
        const phoneNumberSpan = document.getElementById('phoneNumber');
        
        const phoneNumber = phoneNumberSpan.innerText;
        
        donateBtn.addEventListener('click', () => {
            donateModal.style.display = 'flex';
        });
        
        closeDonateModal.addEventListener('click', () => {
            donateModal.style.display = 'none';
        });
        
        copyPhoneBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(phoneNumber.replace(/\\s/g, ''));
            showToast('✅ Номер скопирован! Спасибо за поддержку 🙏');
        });
        
        window.addEventListener('click', (event) => {
            if (event.target === donateModal) {
                donateModal.style.display = 'none';
            }
        });
        
        // --- УПРАВЛЕНИЕ ДЕКОРАТИВНЫМИ ВОЛНАМИ (С ПЛАВНЫМ ЗАТУХАНИЕМ) ---
        const wavesWrapper = document.getElementById('wavesWrapper');
        const toggleWaves = document.getElementById('toggleWaves');
        
        function applyWavesState() {
            const enabled = localStorage.getItem('neobrain_waves') !== 'false';
            if (wavesWrapper) {
                if (enabled) {
                    wavesWrapper.classList.remove('hidden');
                } else {
                    wavesWrapper.classList.add('hidden');
                }
            }
            if (toggleWaves) toggleWaves.checked = enabled;
        }
        
        if (toggleWaves) {
            toggleWaves.addEventListener('change', () => {
                const enabled = toggleWaves.checked;
                localStorage.setItem('neobrain_waves', enabled);
                if (wavesWrapper) {
                    if (enabled) {
                        wavesWrapper.classList.remove('hidden');
                    } else {
                        wavesWrapper.classList.add('hidden');
                    }
                }
            });
        }
        
        applyWavesState();
        
        // --- ИНИЦИАЛИЗАЦИЯ ---
        const chatWindow = document.getElementById('chatWindow');
        const msgInput = document.getElementById('msgInput');
        const sendBtn = document.getElementById('sendBtn');
        const typingBlock = document.getElementById('typingBlock');
        const clearBtn = document.getElementById('clearChatBtn');
        const modelSelect = document.getElementById('modelSelect');
        const characterSelect = document.getElementById('characterSelect');
        const addCharBtn = document.getElementById('addCharacterBtn');
        const modal = document.getElementById('characterModal');
        const saveCharBtn = document.getElementById('saveCharacterBtn');
        const cancelModalBtn = document.getElementById('cancelModalBtn');
        const charNameInput = document.getElementById('charName');
        const charDescInput = document.getElementById('charDesc');
        
        loadCharacters();
        loadTemperature();
        loadTheme();
        loadAccessibilityMode();
        initChats();
        
        sendBtn.addEventListener('click', sendMessage);
        msgInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        clearBtn.addEventListener('click', clearChat);
        
        addCharBtn.addEventListener('click', () => {
            charNameInput.value = '';
            charDescInput.value = '';
            modal.style.display = 'flex';
        });
        
        saveCharBtn.addEventListener('click', () => {
            const name = charNameInput.value.trim();
            const desc = charDescInput.value.trim();
            if (name && desc) {
                addCharacter(name, desc);
                modal.style.display = 'none';
            } else {
                alert('Заполните имя и описание персонажа');
            }
        });
        
        cancelModalBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        window.onclick = (e) => {
            if (e.target === modal) modal.style.display = 'none';
        };
        
        // Эффект наклона кнопок за курсором
        function initTiltEffect() {
            const buttons = document.querySelectorAll('button, .temp-preset, .controls select, .character-selector select, .modal button');
            const maxRotate = 5;
            
            buttons.forEach(btn => {
                btn.classList.add('tilt-button');
                
                btn.addEventListener('mousemove', (e) => {
                    const rect = btn.getBoundingClientRect();
                    const x = (e.clientX - rect.left) / rect.width - 0.5;
                    const y = (e.clientY - rect.top) / rect.height - 0.5;
                    const rotY = x * maxRotate;
                    const rotX = y * -maxRotate;
                    btn.style.transform = `perspective(400px) rotateX(${rotX}deg) rotateY(${rotY}deg)`;
                });
                
                btn.addEventListener('mouseleave', () => {
                    btn.style.transform = '';
                });
            });
        }
        
        document.addEventListener('DOMContentLoaded', initTiltEffect);
    </script>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
async def home():
    return html_template


@app.post("/ask")
async def ask(request: dict):
    try:
        prompt = request.get("prompt", "")
        model = request.get("model", "qwen2.5-coder:7b")
        character_description = request.get("character_description", "Ты дружелюбный и умный ассистент.")
        temperature = request.get("temperature", 0.7)
        history = request.get("history", [])
        
        full_prompt = character_description + "\n"
        for msg in history:
            if msg["role"] == "user":
                full_prompt += f"Пользователь: {msg['content']}\n"
            else:
                full_prompt += f"Ты: {msg['content']}\n"
        full_prompt += f"Пользователь: {prompt}\nТы:"
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": True,
                "temperature": temperature,
            },
            timeout=90,
            stream=True
        )
        
        def generate():
            for chunk in response.iter_lines():
                if chunk:
                    try:
                        data = json.loads(chunk.decode('utf-8'))
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                    except:
                        pass
        
        return StreamingResponse(generate(), media_type="text/plain")
    
    except Exception as e:
        async def error_gen():
            yield f"Ошибка соединения с Ollama: {str(e)}"
        return StreamingResponse(error_gen(), media_type="text/plain")


if __name__ == "__main__":
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    
    print("\n✅ Сервер NeoBrain запущен!")
    print("📌 Открыть в браузере:")
    print(f"   → http://localhost:8000")
    print(f"   → http://127.0.0.1:8000")
    if local_ip != "127.0.0.1":
        print(f"   → http://{local_ip}:8000  (для доступа с других устройств в сети)")
    print("\n⏹️  Для остановки сервера нажми Ctrl+C\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)