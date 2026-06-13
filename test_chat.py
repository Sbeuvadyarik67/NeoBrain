from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>Тестовый чат</title>
</head>
<body>
    <input type="text" id="msgInput" placeholder="Напиши...">
    <button id="sendBtn">Отправить</button>
    <div id="output"></div>

    <script>
        const sendBtn = document.getElementById('sendBtn');
        const msgInput = document.getElementById('msgInput');
        const output = document.getElementById('output');

        sendBtn.onclick = () => {
            output.innerHTML = "<p>Вы написали: " + msgInput.value + "</p>";
        };

        msgInput.onkeypress = (e) => {
            if (e.key === 'Enter') {
                output.innerHTML = "<p>Вы написали (Enter): " + msgInput.value + "</p>";
            }
        };
    </script>
</body>
</html>
"""

@app.get("/")
async def home():
    return HTMLResponse(html)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)