import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QScrollArea, QStackedWidget, QFrame
)
from PyQt5.QtCore import Qt, QTimer

API_BASE_URL = "http://127.0.0.1:8080"

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Bot Interface")
        self.resize(600, 400)

        # Стек виджетов для переключения между экранами
        self.stacked_widget = QStackedWidget(self)
        self.user_list_screen = QWidget()
        self.chat_screen = QWidget()

        self.stacked_widget.addWidget(self.user_list_screen)
        self.stacked_widget.addWidget(self.chat_screen)

        self.init_user_list_screen()
        self.init_chat_screen()

        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

        self.load_users()

        # Таймер для регулярного обновления сообщений
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.load_chat_messages)
        self.update_timer.start(5000)  # Обновление сообщений каждую секунду

    def init_user_list_screen(self):
        layout = QVBoxLayout()

        self.user_buttons = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area_widget = QWidget()
        scroll_area_widget.setLayout(self.user_buttons)
        scroll_area.setWidget(scroll_area_widget)
        scroll_area.setWidgetResizable(True)

        layout.addWidget(QLabel("Пользователи:"))
        layout.addWidget(scroll_area)

        self.user_list_screen.setLayout(layout)

    def init_chat_screen(self):
        layout = QVBoxLayout()

        self.chat_title = QLabel("Чат")
        self.chat_title.setAlignment(Qt.AlignCenter)

        self.chat_messages = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area_widget = QWidget()
        scroll_area_widget.setLayout(self.chat_messages)
        scroll_area.setWidget(scroll_area_widget)
        scroll_area.setWidgetResizable(True)

        self.input_field = QLineEdit()
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message)

        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.go_back)

        input_layout = QVBoxLayout()
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)

        layout.addWidget(self.back_button)
        layout.addWidget(self.chat_title)
        layout.addWidget(scroll_area)
        layout.addLayout(input_layout)

        self.chat_screen.setLayout(layout)

    def load_users(self):
        try:
            response = requests.get(f"{API_BASE_URL}/users")
            users = response.json()
            for user in users:
                user_button = QPushButton(user["username"] or user["first_name"] or str(user["id"]))
                user_button.clicked.connect(lambda _, uid=user["id"]: self.open_chat(uid))
                self.user_buttons.addWidget(user_button)
        except Exception as e:
            print(f"Ошибка загрузки пользователей: {e}")

    def open_chat(self, user_id):
        self.current_user_id = user_id
        self.chat_messages_layout = QVBoxLayout()
        self.load_chat_messages()
        self.stacked_widget.setCurrentWidget(self.chat_screen)

    def load_chat_messages(self):
        try:
            response = requests.get(f"{API_BASE_URL}/messages?chat_id={self.current_user_id}")
            messages = response.json()

            # Удаляем все старые сообщения
            for i in range(self.chat_messages.count()):
                child = self.chat_messages.itemAt(i).widget()
                if child is not None:
                    child.deleteLater()

            # Добавляем новые сообщения
            for message in messages:
                self.add_message_to_chat(message)
        except Exception as e:
            print(f"Ошибка загрузки сообщений: {e}")

    def add_message_to_chat(self, message):
        frame = QFrame()
        layout = QVBoxLayout()

        if message["username"] == "bot":
            layout.setAlignment(Qt.AlignRight)
        else:
            layout.setAlignment(Qt.AlignLeft)

        msg_label = QLabel(f"{message['username']}: {message['command']}")
        msg_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(msg_label)

        frame.setLayout(layout)
        self.chat_messages.addWidget(frame)

    def send_message(self):
        message = self.input_field.text()
        if message.strip():
            try:
                requests.post(f"{API_BASE_URL}/send_message", json={
                    "user_id": self.current_user_id,
                    "message": message
                })
                self.add_message_to_chat({"username": "bot", "command": message})
                self.input_field.clear()
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")

    def go_back(self):
        self.stacked_widget.setCurrentWidget(self.user_list_screen)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
