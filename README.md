# 🧠 NeoBrain

**NeoBrain** — это десктопное приложение для общения с AI через локальные и облачные модели. Поддерживает **Ollama**, **OpenAI**, **Google Gemini** и **Anthropic Claude**.

[![GitHub release](https://img.shields.io/github/v/release/Sbeuvadyarik67/NeoBrain)](https://github.com/Sbeuvadyarik67/NeoBrain/releases)
[![GitHub](https://img.shields.io/github/license/Sbeuvadyarik67/NeoBrain)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)

---

## ✨ Возможности

- 🌍 **Полная локализация** — Русский, English, Українська
- 🤖 **Поддержка AI провайдеров**:
  - **Ollama** — локально, бесплатно!
  - **OpenAI** — GPT-3.5, GPT-4
  - **Google Gemini**
  - **Anthropic Claude**
- 🎨 **Стили интерфейса** — Minimal, Vibes, Cyber, Cloudy
- 📋 **Копирование текста** — кнопка при наведении на сообщение
- 🔥 **Кринжометр** — регулировка "кринжовости" ответов от 1 до 10
- 👤 **Персонажи** — создание, удаление, экспорт, импорт
- ⚡ **Автозапуск Ollama** — при старте приложения
- 📱 **Адаптивный дизайн** — работает на любом экране

---

## 🚀 Быстрый старт

### Windows (рекомендуется)

1. Скачай последний релиз:  
   👉 [NeoBrain/releases](https://github.com/Sbeuvadyarik67/NeoBrain/releases)
2. Распакуй архив и запусти `NeoBrain_v2.1.exe`
3. Выбери язык интерфейса
4. Настрой AI провайдера и общайся!

### Из исходников

```bash
# 1. Клонируй репозиторий
git clone https://github.com/Sbeuvadyarik67/NeoBrain.git
cd NeoBrain

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Установи Ollama (для локальных моделей)
# Windows: https://ollama.com/download/OllamaSetup.exe
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 4. Скачай модель (опционально)
ollama pull qwen2.5-coder:1.5b

# 5. Запусти приложение
python main.py


```

---

## 🎯 Настройка AI

### 🔹 Ollama (локально, бесплатно)

```bash
# Скачай модель
ollama pull qwen2.5-coder:1.5b

# Запусти сервер (автоматически при старте NeoBrain)
ollama serve
```

> **NeoBrain автоматически запускает Ollama при старте!** 🚀

### 🔹 OpenAI / Gemini / Claude

1. Получи API ключ у провайдера
2. В настройках NeoBrain выбери провайдера
3. Вставь API ключ и сохрани

---

## 🛠️ Сборка .exe

```bash
# Установи PyInstaller
pip install pyinstaller

# Собери .exe
pyinstaller --onefile --windowed --name "NeoBrain_v2.1" --add-data "neobrain_config.json;." main.py
```

---

## 📁 Структура проекта

```
NeoBrain/
├── main.py                      # Основной файл приложения
├── requirements.txt             # Зависимости Python
├── neobrain_config.example.json # Пример конфигурации
├── .gitignore                   # Игнорируемые файлы
├── LICENSE                      # Лицензия MIT
└── README.md                    # Этот файл
```

---

## 📦 Зависимости

```txt
fastapi==0.115.0      # Веб-фреймворк
uvicorn==0.30.0       # ASGI сервер
requests==2.32.0      # HTTP запросы
pywebview==4.2.2      # Десктопное окно
python-multipart==0.0.9
```

Полный список в `requirements.txt`

---

## 🤝 Лицензия

MIT License — свободно для использования и модификации.

---

## 🌟 Автор

**[Sbeuvadyarik67](https://github.com/Sbeuvadyarik67)**

---

## ⭐ Поддержка проекта

Если проект тебе полезен — поставь звезду на GitHub!  
Это поможет другим людям найти проект.

[![GitHub stars](https://img.shields.io/github/stars/Sbeuvadyarik67/NeoBrain)](https://github.com/Sbeuvadyarik67/NeoBrain/stargazers)
