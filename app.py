from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QScrollArea, QFrame, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer
import sys
import requests

API_BASE_URL = "http://127.0.0.1:8080"
ACCESS_TOKEN = "my_secure_token"

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Bot Interface")
        self.resize(800, 600)

        # Layouts for user list and chat
        main_layout = QHBoxLayout()
        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self.open_chat)

        self.chat_layout = QVBoxLayout()
        self.chat_header = QLabel("Select a user to start chatting")
        self.chat_header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        self.chat_messages = QVBoxLayout()
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area_widget = QWidget()
        self.chat_scroll_area_widget.setLayout(self.chat_messages)
        self.chat_scroll_area.setWidget(self.chat_scroll_area_widget)
        self.chat_scroll_area.setWidgetResizable(True)

        self.input_field = QLineEdit()
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)

        self.chat_layout.addWidget(self.chat_header)
        self.chat_layout.addWidget(self.chat_scroll_area)
        self.chat_layout.addLayout(input_layout)

        self.current_user_id = None

        # Add layouts to the main layout
        main_layout.addWidget(self.user_list, 1)
        main_layout.addLayout(self.chat_layout, 3)

        self.setLayout(main_layout)

        self.load_users()

        # Timer for message updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.load_chat_messages)
        self.update_timer.start(5000)

    def load_users(self):
        try:
            response = requests.get(f"{API_BASE_URL}/users", headers={"Authorization": ACCESS_TOKEN})
            response.raise_for_status()
            users = response.json()
            self.user_list.clear()
            for user in users:
                item = QListWidgetItem(user["username"] or user["first_name"] or str(user["id"]))
                item.setData(Qt.UserRole, user)
                self.user_list.addItem(item)
        except Exception as e:
            print(f"Error loading users: {e}")

    def open_chat(self, item):
        user = item.data(Qt.UserRole)
        self.current_user_id = user["id"]
        self.chat_header.setText(f"{user['first_name']} {user['last_name']}")
        self.load_chat_messages()
        self.scroll_to_bottom()

    def load_chat_messages(self):
        if not self.current_user_id:
            return
        try:
            response = requests.get(
                f"{API_BASE_URL}/messages?chat_id={self.current_user_id}",
                headers={"Authorization": ACCESS_TOKEN}
            )
            response.raise_for_status()
            messages = response.json()

            # Clear existing messages
            for i in range(self.chat_messages.count()):
                child = self.chat_messages.itemAt(i).widget()
                if child:
                    child.deleteLater()

            # Add new messages
            for message in messages:
                self.add_message_to_chat(message)

            self.scroll_to_bottom()
        except Exception as e:
            print(f"Error loading chat messages: {e}")

    def add_message_to_chat(self, message):
        # Frame and layout for message
        frame = QFrame()
        layout = QHBoxLayout()
        frame.setLayout(layout)

        if message["username"] == "bot":
            layout.setAlignment(Qt.AlignRight)
            frame.setStyleSheet("""
                background-color: #d9f9d9; border-radius: 10px; padding: 15px;
                border: 1px solid #ccc; margin: 5px; margin-right: 0;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            """)
        else:
            layout.setAlignment(Qt.AlignLeft)
            frame.setStyleSheet("""
                background-color: #f1f1f1; border-radius: 10px; padding: 15px;
                border: 1px solid #ccc; margin: 5px; margin-left: 0;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            """)

        # Adding message text
        msg_label = QLabel(f"{message['username']}: {message['command']}")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # Ensuring the message takes up the full width
        layout.setStretch(0, 1)

        self.chat_messages.addWidget(frame)

    def send_message(self):
        if not self.current_user_id or not self.input_field.text().strip():
            return
        try:
            message = self.input_field.text()
            requests.post(f"{API_BASE_URL}/send_message", json={
                "user_id": self.current_user_id,
                "message": message
            }, headers={"Authorization": ACCESS_TOKEN})
            self.add_message_to_chat({"username": "bot", "command": message})
            self.input_field.clear()
            self.scroll_to_bottom()
        except Exception as e:
            print(f"Error sending message: {e}")

    def scroll_to_bottom(self):
        """Автоматическая прокрутка в самый низ с учетом пересчета размеров."""
        self.chat_scroll_area_widget.adjustSize()  # Убедиться, что размеры обновлены
        QTimer.singleShot(0, lambda: self.chat_scroll_area.verticalScrollBar().setValue(
            self.chat_scroll_area.verticalScrollBar().maximum()
        ))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
