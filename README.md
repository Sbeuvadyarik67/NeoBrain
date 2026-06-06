# 🧠 NeoBrain — локальный аналог Character.AI

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)]()
[![Ollama](https://img.shields.io/badge/Ollama-0.1%2B-orange)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![GitHub stars](https://img.shields.io/github/stars/Sbeuvadyarik67/NeoBrain)]()

**NeoBrain** — это веб-приложение для общения с ИИ-персонажами.  
Работает локально через Ollama, **без VPN, регистрации и слежки**.

---

## ✨ Возможности

- 🤖 **Локальная нейросеть** (Ollama)
- 🎭 **Ролевые персонажи** (создавай своих)
- 🎨 **7 цветовых тем** (Неон, Baby-doll, Летняя, Пляжная, Цифровая, Творческая, Тёплая)
- 🌡️ **Температура 1–10** (от чётких до креативных ответов)
- 📋 **Копирование ответов** одной кнопкой
- 💾 **История диалогов** в браузере
- 🧠 **Потоковый ответ** (печатает как ChatGPT)
- 💖 **Поддержка проекта** (ВТБ)

---

## 🖼️ Скриншоты

| Главный экран | Диалог с ИИ | Панель персонажей |
|--------------|-------------|-------------------|
| ![Главный экран](screenshots/main.png) | ![Диалог](screenshots/chat.png) | ![Персонажи](screenshots/characters.png) |

> 📌 Скриншоты нужно добавить в папку `screenshots/` и загрузить на GitHub.

---

## 🚀 Быстрый старт

### 1. Установи [Ollama](https://ollama.com/) и скачай модель:

```bash
ollama pull qwen2.5-coder:7b
