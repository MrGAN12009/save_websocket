import sqlite3
import json
import asyncio
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from telebot import TeleBot
import websockets

# Укажите ваш токен Telegram-бота
API_TOKEN = "7430419581:AAFV5bZJrV04IjBnx7Gl3dcezE9Xn0xBbOA"
ACCESS_TOKEN = "my_secure_token"

bot = TeleBot(API_TOKEN)

# Подключение к базе данных
conn = sqlite3.connect("db.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    command TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

users = {}

def save_command(user_id, username, first_name, last_name, command):
    cursor.execute(
        "INSERT INTO commands (user_id, username, first_name, last_name, command) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, first_name, last_name, command)
    )
    conn.commit()

def get_chat_messages(chat_id):
    cursor.execute("SELECT * FROM commands WHERE user_id = ? ORDER BY timestamp ASC", (chat_id,))
    rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "first_name": row[3],
            "last_name": row[4],
            "command": row[5],
            "timestamp": row[6]
        } for row in rows
    ]

def validate_token(headers):
    token = headers.get("Authorization")
    return token == ACCESS_TOKEN

class RequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self):
        if not validate_token(self.headers):
            self._send_response(403, {"error": "Forbidden: Invalid or missing token"})
            return

        if self.path.startswith("/users"):
            self._send_response(200, list(users.values()))
        elif self.path.startswith("/messages"):
            try:
                query_components = {k: v for k, v in [param.split("=") for param in self.path.split("?")[1].split("&")]} if "?" in self.path else {}
                chat_id = query_components.get("chat_id")

                if not chat_id:
                    raise ValueError("chat_id parameter is required")

                messages = get_chat_messages(int(chat_id))
                self._send_response(200, messages)
            except Exception as e:
                self._send_response(400, {"error": str(e)})
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        if not validate_token(self.headers):
            self._send_response(403, {"error": "Forbidden: Invalid or missing token"})
            return

        if self.path == "/send_message":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                user_id = data.get("user_id")
                message = data.get("message")

                if not user_id or not message:
                    raise ValueError("Missing user_id or message")

                bot.send_message(user_id, message)
                save_command(user_id, 'bot', 'bot', 'bot', message)
                self._send_response(200, {"status": "Message sent successfully"})
            except Exception as e:
                self._send_response(400, {"error": str(e)})
        else:
            self._send_response(404, {"error": "Not found"})

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "Unknown"
    last_name = message.from_user.last_name or "Unknown"
    command = message.text

    if user_id not in users:
        users[user_id] = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name
        }
    save_command(user_id, username, first_name, last_name, command)
    response = "Команда сохранена в базе данных!"
    save_command(user_id, 'bot', 'bot', 'bot', response)
    bot.reply_to(message, response)

async def websocket_handler(websocket, path):
    async for message in websocket:
        print(f"Получено сообщение: {message}")
        await websocket.send(f"Эхо: {message}")

def start_websocket_server():
    asyncio.run(_start_websocket_server())

async def _start_websocket_server():
    async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
        print("WebSocket-сервер запущен на порту 8765")
        await asyncio.Future()

if __name__ == "__main__":
    print("Бот запущен...")

    server_address = ('', 8080)
    httpd = HTTPServer(server_address, RequestHandler)
    print("HTTP-сервер запущен на порту 8080")

    websocket_thread = Thread(target=start_websocket_server)
    websocket_thread.start()

    bot_thread = Thread(target=lambda: bot.polling(none_stop=True))
    bot_thread.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Остановка серверов...")
        httpd.server_close()
        websocket_thread.join()
        bot_thread.join()
