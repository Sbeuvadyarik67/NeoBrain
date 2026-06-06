from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import uvicorn
import subprocess
import time
import socket

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
    <title>NeoBrain | AI чат</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: radial-gradient(circle at 20% 30%, #0a0f1e, #03060c);
            font-family: 'Inter', system-ui, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 1rem;
        }
        .chat {
            max-width: 1000px;
            width: 100%;
            height: 90vh;
            background: rgba(10, 20, 30, 0.65);
            backdrop-filter: blur(14px);
            border-radius: 2rem;
            border: 1px solid rgba(0, 255, 255, 0.6);
            box-shadow: 0 0 15px rgba(255, 0, 255, 0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            padding: 1rem 1.8rem;
            background: rgba(0, 20, 30, 0.6);
            border-bottom: 1px solid rgba(255, 0, 255, 0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .brand { display: flex; align-items: center; gap: 14px; }
        .neon-icon { font-size: 36px; }
        .brand-text h1 { font-size: 1.6rem; color: #eef5ff; }
        .brand-text p { font-size: 0.75rem; opacity: 0.7; color: #eef5ff; }
        .controls {
            display: flex;
            gap: 0.8rem;
            align-items: center;
            flex-wrap: wrap;
        }
        select, button {
            background: #1e293b;
            border: 1px solid #4caf50;
            padding: 8px 16px;
            border-radius: 2rem;
            font-size: 0.85rem;
            cursor: pointer;
            color: white;
        }
        button { background: #2e7d32; border-color: #4caf50; }
        button:hover { background: #4caf50; }
        .create-char-btn {
            background: #f39c12;
            border-color: #ffaa00;
        }
        .create-char-btn:hover { background: #e67e22; }
        .temp-control {
            display: flex;
            align-items: center;
            gap: 12px;
            background: #1e293b;
            padding: 4px 16px;
            border-radius: 2rem;
        }
        .temp-control span { color: white; font-size: 0.85rem; }
        input[type="range"] { width: 120px; cursor: pointer; background: #4caf50; height: 4px; border-radius: 5px; }
        #tempValue { color: #4caf50; font-weight: bold; min-width: 35px; }
        .chat-window { flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 18px; }
        .msg { display: flex; gap: 12px; max-width: 80%; animation: slideUp 0.25s ease; }
        @keyframes slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
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
            background: #111a24dd;
            border: 1px solid rgba(255, 0, 255, 0.4);
            padding: 10px 20px;
            border-radius: 24px;
            font-size: 0.95rem;
            backdrop-filter: blur(8px);
            color: #eef5ff;
        }
        .user-msg .bubble { background: #0c5e32dd; border: 1px solid #8affaa; color: #ffffff; }
        .msg-time { font-size: 0.65rem; margin-top: 5px; padding-left: 56px; opacity: 0.6; color: #aaccff; }
        .typing-block { display: none; align-items: center; gap: 12px; padding-left: 1.5rem; }
        .typing-dots { background: rgba(17, 26, 36, 0.8); padding: 10px 20px; border-radius: 30px; display: flex; gap: 8px; }
        .typing-dots span { width: 8px; height: 8px; background: #88ccff; border-radius: 50%; animation: wave 1.2s infinite; }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes wave { 0%,60%,100% { opacity: 0.4; transform: translateY(0px); } 30% { opacity: 1; transform: translateY(-4px); } }
        .input-area {
            background: rgba(0, 0, 0, 0.3);
            border-top: 1px solid cyan;
            padding: 1rem 1.5rem;
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .input-area input { flex: 1; background: #0e1a24; border: 1px solid magenta; padding: 12px 20px; border-radius: 60px; font-size: 0.95rem; outline: none; color: white; }
        .input-area button { background: linear-gradient(95deg, #1e88e5, #0d47a1); border: none; padding: 10px 32px; border-radius: 60px; font-weight: bold; color: white; cursor: pointer; }
        .input-area button:hover { background: #42a5f5; }
        
        body.babydoll { background: linear-gradient(135deg, #ffe0f0, #e0f0ff); color: #5a3e5a; }
        body.babydoll .bubble { background: rgba(255, 255, 255, 0.9); border: 1px solid #ffb6c1; color: #5a3e5a; }
        body.summer { background: linear-gradient(135deg, #c0e0a0, #ffcc80); color: #2d4a2d; }
        body.summer .bubble { background: rgba(255, 255, 255, 0.9); border: 1px solid #ffa500; color: #2d4a2d; }
        body.beach { background: linear-gradient(135deg, #b0e0ff, #fff0a0); color: #1a3a6a; }
        body.beach .bubble { background: rgba(255, 255, 255, 0.9); border: 1px solid #ffd700; color: #1a3a6a; }
        body.digital { background: linear-gradient(135deg, #ffaa70, #c080ff); color: #2e1a4a; }
        body.digital .bubble { background: rgba(0, 0, 0, 0.8); border: 1px solid #ff8c00; color: #f0f0f0; }
        body.creative { background: linear-gradient(135deg, #ffc0cb, #a0b080); color: #3a4a2a; }
        body.creative .bubble { background: rgba(255, 255, 255, 0.9); border: 1px solid #ffb6c1; color: #3a4a2a; }
        body.warm { background: linear-gradient(135deg, #ffd0d0, #ffe0b0); color: #5a3a2a; }
        body.warm .bubble { background: rgba(255, 255, 255, 0.9); border: 1px solid #ffaa77; color: #5a3a2a; }
        
        .characters-panel {
            position: fixed;
            left: 0;
            top: 0;
            width: 280px;
            height: 100vh;
            background: rgba(10, 20, 40, 0.95);
            backdrop-filter: blur(16px);
            border-right: 1px solid cyan;
            transform: translateX(-100%);
            transition: transform 0.3s ease;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            padding: 70px 15px 20px 15px;
            gap: 10px;
        }
        .characters-panel.open { transform: translateX(0); }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 10px;
            color: white;
            background: rgba(0,0,0,0.5);
            border-radius: 12px;
            margin-bottom: 5px;
        }
        .panel-toggle-btn {
            position: fixed;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            background: cyan;
            border: none;
            color: black;
            font-size: 1.2rem;
            padding: 12px 6px;
            border-radius: 0 12px 12px 0;
            cursor: pointer;
            z-index: 10000;
            font-weight: bold;
            transition: 0.2s;
            box-shadow: 2px 0 8px rgba(0,0,0,0.3);
        }
        .panel-toggle-btn:hover { background: #00cccc; padding-right: 10px; }
        #charactersList { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .character-item {
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .character-item.active { background: rgba(0, 255, 255, 0.3); border-left: 3px solid cyan; }
        .character-name { color: white; font-size: 0.9rem; }
        .delete-char { background: none; border: none; color: #ff6b6b; cursor: pointer; font-size: 1rem; }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 20000;
        }
        .modal-content {
            background: #0f172a;
            border: 1px solid cyan;
            border-radius: 2rem;
            padding: 2rem;
            width: 90%;
            max-width: 400px;
            color: white;
        }
        .modal-content input, .modal-content textarea {
            width: 100%;
            margin: 10px 0;
            padding: 10px;
            background: #1e293b;
            border: 1px solid cyan;
            border-radius: 12px;
            color: white;
            font-size: 0.9rem;
        }
        .modal-content textarea { resize: vertical; }
        .modal-buttons { display: flex; gap: 10px; margin-top: 15px; }
        .modal-buttons button { flex: 1; }
    </style>
</head>
<body>
<div class="chat">
    <div id="charactersPanel" class="characters-panel">
        <div class="panel-header">
            <span>🎭 Персонажи</span>
        </div>
        <div id="charactersList"></div>
    </div>
    <button id="togglePanelBtn" class="panel-toggle-btn">▶</button>
    <div class="header">
        <div class="brand">
            <div class="neon-icon">🧠✨</div>
            <div class="brand-text">
                <h1>NeoBrain</h1>
                <p>локальная нейросеть</p>
            </div>
        </div>
        <div class="controls">
            <select id="modelSelect"><option>Загрузка...</option></select>
            <select id="themeSelect">
                <option value="neon">🌙 Неон</option>
                <option value="babydoll">🎀 Baby-doll</option>
                <option value="summer">☀️ Летняя</option>
                <option value="beach">🏖️ Пляжная</option>
                <option value="digital">📱 Цифровая</option>
                <option value="creative">🎨 Творческая</option>
                <option value="warm">🔥 Тёплая</option>
            </select>
            <div class="temp-control">
                <span>🌡️</span>
                <input type="range" id="temperatureSlider" min="1" max="10" step="1" value="5">
                <span id="tempValue">5</span>
            </div>
            <button id="clearBtn">🗑 Очистить</button>
            <button id="addCharacterBtn" class="create-char-btn">➕ Создать персонажа</button>
        </div>
    </div>
    <div class="chat-window" id="chatWindow">
        <div class="msg ai-msg">
            <div class="avatar">🤖</div>
            <div class="bubble">Привет! Я NeoBrain. Напиши что-нибудь 😊</div>
        </div>
    </div>
    <div class="typing-block" id="typingBlock">
        <div class="avatar">🤖</div>
        <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>
    <div class="input-area">
        <input type="text" id="msgInput" placeholder="Напиши сообщение..." autofocus>
        <button id="sendBtn">💬 Отправить</button>
    </div>
</div>

<div id="modal" class="modal">
    <div class="modal-content">
        <h3>➕ Новый персонаж</h3>
        <input type="text" id="modalCharName" placeholder="Имя персонажа">
        <textarea id="modalCharDesc" rows="3" placeholder="Опишите характер, стиль речи, роль...&#10;Пример: Ты — старый маг, говоришь загадками, любишь шутить."></textarea>
        <div class="modal-buttons">
            <button id="modalSaveBtn">Сохранить</button>
            <button id="modalCancelBtn">Отмена</button>
        </div>
    </div>
</div>

<script>
    // ДОМ элементы
    const chatWindow = document.getElementById('chatWindow');
    const msgInput = document.getElementById('msgInput');
    const sendBtn = document.getElementById('sendBtn');
    const clearBtn = document.getElementById('clearBtn');
    const modelSelect = document.getElementById('modelSelect');
    const typingBlock = document.getElementById('typingBlock');
    const temperatureSlider = document.getElementById('temperatureSlider');
    const tempValue = document.getElementById('tempValue');
    const themeSelect = document.getElementById('themeSelect');
    const toggleBtn = document.getElementById('togglePanelBtn');
    const charactersPanel = document.getElementById('charactersPanel');
    const charactersList = document.getElementById('charactersList');
    const addCharacterBtn = document.getElementById('addCharacterBtn');
    const modal = document.getElementById('modal');
    const modalCharName = document.getElementById('modalCharName');
    const modalCharDesc = document.getElementById('modalCharDesc');
    const modalSaveBtn = document.getElementById('modalSaveBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');

    // === ТЕМПЕРАТУРА ===
    if (temperatureSlider) {
        temperatureSlider.addEventListener('input', () => {
            tempValue.innerText = temperatureSlider.value;
        });
    }

    // === МОДЕЛИ ===
    async function loadModels() {
    try {
        const res = await fetch('/models');
        const data = await res.json();
        modelSelect.innerHTML = '';
        if (data.models && data.models.length) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                let name = m;
                if (m === 'mistral:7b') name = '🧠 Mistral 7b — умная, хорошо держит роль (тяжелее)';
                else if (m === 'llama3.2:3b') name = '⚡ Llama 3.2 3b — быстрая, лёгкая (менее креативная)';
                else if (m === 'qwen2.5-coder:7b') name = '💻 Qwen 7b — кодовая, не для ролей (средняя)';
                else if (m === 'qwen2.5-coder:1.5b') name = '🚀 Qwen 1.5b — очень быстрая, но простая';
                else if (m === 'llama3.1:8b') name = '🧠 Llama 3.1 8b — отличная грамматика, умная, хорошо держит роль (рекомендую)';
                else name = m;
                opt.textContent = name;
                modelSelect.appendChild(opt);
            });
        }
    } catch(e) { console.error(e); }
}

    // === СООБЩЕНИЯ ===
    function addMessage(text, isUser) {
        const div = document.createElement('div');
        div.className = `msg ${isUser ? 'user-msg' : 'ai-msg'}`;
        div.innerHTML = `<div class="avatar">${isUser ? '👤' : '🤖'}</div><div class="bubble">${escapeHtml(text)}</div>`;
        chatWindow.appendChild(div);
        const timeDiv = document.createElement('div');
        timeDiv.className = 'msg-time';
        timeDiv.innerText = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        chatWindow.appendChild(timeDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function escapeHtml(str) {
        return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : (m === '<' ? '&lt;' : '&gt;'));
    }

    function clearChat() {
        if (confirm('Очистить чат?')) {
            chatWindow.innerHTML = '';
            addMessage('Чат очищен. Напиши что-нибудь!', false);
        }
    }

    function showTyping() { typingBlock.style.display = 'flex'; }
    function hideTyping() { typingBlock.style.display = 'none'; }

    // === ПЕРСОНАЖИ ===
    let characters = [];
    let activeCharacterId = null;
    const STORAGE_CHARS = 'neobrain_chars';
    const STORAGE_ACTIVE_CHAR = 'neobrain_active_char';

    function saveCharacters() { localStorage.setItem(STORAGE_CHARS, JSON.stringify(characters)); }
    function loadCharacters() {
        const saved = localStorage.getItem(STORAGE_CHARS);
        if (saved) characters = JSON.parse(saved);
        else characters = [{ id: 'default', name: 'Помощник', description: 'Ты дружелюбный и умный ассистент. Отвечай на русском кратко.' }];
        renderCharactersList();
        loadActiveCharacter();
    }
    function renderCharactersList() {
        if (!charactersList) return;
        charactersList.innerHTML = '';
        characters.forEach(c => {
            const div = document.createElement('div');
            div.className = `character-item ${activeCharacterId === c.id ? 'active' : ''}`;
            div.innerHTML = `<span class="character-name">${escapeHtml(c.name)}</span><button class="delete-char" data-id="${c.id}">🗑</button>`;
            div.querySelector('.character-name').onclick = () => setActiveCharacter(c.id);
            div.querySelector('.delete-char').onclick = (e) => {
                e.stopPropagation();
                deleteCharacter(c.id);
            };
            charactersList.appendChild(div);
        });
    }
    function setActiveCharacter(id) {
        activeCharacterId = id;
        localStorage.setItem(STORAGE_ACTIVE_CHAR, id);
        renderCharactersList();
    }
    function loadActiveCharacter() {
        const saved = localStorage.getItem(STORAGE_ACTIVE_CHAR);
        if (saved && characters.some(c => c.id === saved)) activeCharacterId = saved;
        else if (characters.length) activeCharacterId = characters[0].id;
        renderCharactersList();
    }
    function addCharacter(name, desc) {
        const id = Date.now().toString();
        characters.push({ id, name, description: desc });
        saveCharacters();
        renderCharactersList();
        setActiveCharacter(id);
    }
    function deleteCharacter(id) {
        if (characters.length === 1) { alert('Нельзя удалить последнего персонажа'); return; }
        if (confirm('Удалить персонажа?')) {
            characters = characters.filter(c => c.id !== id);
            if (activeCharacterId === id) activeCharacterId = characters[0].id;
            saveCharacters();
            renderCharactersList();
            loadActiveCharacter();
        }
    }

    // === МОДАЛЬНОЕ ОКНО ===
    if (addCharacterBtn) {
        addCharacterBtn.onclick = () => {
            modalCharName.value = '';
            modalCharDesc.value = '';
            modal.style.display = 'flex';
        };
    }
    if (modalSaveBtn) {
        modalSaveBtn.onclick = () => {
            const name = modalCharName.value.trim();
            const desc = modalCharDesc.value.trim();
            if (name && desc) {
                addCharacter(name, desc);
                modal.style.display = 'none';
            } else {
                alert('Заполните имя и описание персонажа');
            }
        };
    }
    if (modalCancelBtn) {
        modalCancelBtn.onclick = () => modal.style.display = 'none';
    }
    window.onclick = (e) => {
        if (e.target === modal) modal.style.display = 'none';
    };

    // === КНОПКА ПАНЕЛИ ===
    if (toggleBtn && charactersPanel) {
        toggleBtn.onclick = () => {
            charactersPanel.classList.toggle('open');
            toggleBtn.innerText = charactersPanel.classList.contains('open') ? '◀' : '▶';
        };
    }

    // === ОТПРАВКА СООБЩЕНИЯ ===
    async function sendMessage() {
        const text = msgInput.value.trim();
        if (!text) return;
        const model = modelSelect.value;
        if (!model || model === 'Нет моделей') {
            addMessage('Сначала выберите модель', false);
            return;
        }
        addMessage(text, true);
        msgInput.value = '';
        showTyping();

        const aiDiv = document.createElement('div');
        aiDiv.className = 'msg ai-msg';
        aiDiv.innerHTML = `<div class="avatar">🤖</div><div class="bubble"></div>`;
        const bubble = aiDiv.querySelector('.bubble');
        chatWindow.appendChild(aiDiv);

        try {
            let tempRaw = temperatureSlider ? parseFloat(temperatureSlider.value) : 5;
            const temperature = 0.1 + (tempRaw - 1) * 0.211;
            const selectedChar = characters.find(c => c.id === activeCharacterId);
            const charDesc = selectedChar ? selectedChar.description : 'Ты полезный ассистент. Отвечай на русском кратко.';
            
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: text,
                    model: model,
                    temperature: temperature,
                    character_description: charDesc,
                    history: []
                })
            });
            
            let answer = await response.text();
            answer = answer.trim();
            if (answer.startsWith('"') && answer.endsWith('"')) answer = answer.slice(1, -1);
            if (answer.startsWith("'") && answer.endsWith("'")) answer = answer.slice(1, -1);
            bubble.innerHTML = answer.replace(/\\n/g, '<br>');
            
            const copyBtn = document.createElement('button');
            copyBtn.innerText = '📋 Копировать';
            copyBtn.style.cssText = 'background:#2e7d32; border:none; border-radius:20px; padding:4px 12px; font-size:0.7rem; color:white; cursor:pointer; margin-top:6px; display:block;';
            copyBtn.onclick = () => { navigator.clipboard.writeText(answer); alert('✅ Ответ скопирован!'); };
            bubble.appendChild(copyBtn);
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'msg-time';
            timeDiv.innerText = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            chatWindow.appendChild(timeDiv);
        } catch(err) {
            bubble.innerText = 'Ошибка: ' + err.message;
        } finally {
            hideTyping();
        }
    }

    // === ТЕМЫ ===
    if (themeSelect) {
        const savedTheme = localStorage.getItem('neobrain_theme');
        if (savedTheme) {
            document.body.className = savedTheme;
            themeSelect.value = savedTheme;
        }
        themeSelect.addEventListener('change', (e) => {
            document.body.className = e.target.value;
            localStorage.setItem('neobrain_theme', e.target.value);
        });
    }

    // === ЗАПУСК ===
    loadCharacters();
    loadModels();
    sendBtn.onclick = sendMessage;
    clearBtn.onclick = clearChat;
    msgInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
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
