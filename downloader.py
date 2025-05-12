import sys
import os
import time
from datetime import datetime

import vk_api
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QMessageBox, QSplitter, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6 import QtGui



def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)



CONFIG_PATH = os.path.join(os.path.dirname(sys.argv[0]), "last_settings.cfg")



def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    config = {
        "token": lines[0].strip() if len(lines) > 0 else "",
        "download_folder": lines[1].strip() if len(lines) > 1 else os.path.expanduser("~"),
        "album_name": lines[2].strip() if len(lines) > 2 else ""
    }
    return config


def save_config(token="", download_folder="", album_name=""):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(f"{token}\n")
            f.write(f"{download_folder}\n")
            f.write(f"{album_name}\n")
    except Exception as e:
        print(f"💔[ERROR] Не удалось сохранить конфиг: {e}")



class AlbumDownloaderWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, token, album_input, download_folder):
        super().__init__()
        self.token = token
        self.album_input = album_input.strip()
        self.download_folder = download_folder.strip()

    def run(self):
        try:
            self.log_signal.emit("📝[INFO] Подключение к API ВКонтакте...")
            session = vk_api.VkApi(token=self.token)
            vk = session.get_api()
        except Exception as e:
            self.log_signal.emit(f"💔[ERROR] Ошибка подключения к ВК: {e}")
            self.finished_signal.emit()
            return

        try:
            owner_id, album_id = self.parse_album_input(self.album_input)

            
            album_title = self.get_album_title(vk, owner_id, album_id)
            self.log_signal.emit(f"📝[INFO] Загрузка альбома '{album_title}' ({owner_id}_{album_id})...")

            
            offset = 0
            count = 1000  
            all_photos = []

            while True:
                try:
                    response = vk.photos.get(owner_id=owner_id, album_id=album_id, count=count, offset=offset)
                    items = response.get('items', [])
                    if not items:
                        break
                    all_photos.extend(items)
                    offset += count
                except Exception as e:
                    self.log_signal.emit(f"💔[ERROR] Ошибка получения фото: {e}")
                    break

            self.log_signal.emit(f"📝[INFO] Найдено {len(all_photos)} фото в альбоме.")

            
            safe_title = "".join(c for c in album_title if c.isalnum() or c in (" ", "_", "-")).strip()
            folder_name = f"{safe_title} ({owner_id}_{album_id})"
            folder_path = os.path.join(self.download_folder, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            self.log_signal.emit(f"📝[INFO] Сохраняю в папку: {folder_path}")

            
            for i, photo in enumerate(all_photos):
                try:
                    max_size_url = max(photo['sizes'], key=lambda x: x['width'])['url']
                    filename = f"{photo['id']}.jpg"
                    filepath = os.path.join(folder_path, filename)

                    response = requests.get(max_size_url, stream=True)
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(1024 * 1024):  
                            f.write(chunk)

                    self.log_signal.emit(f"🎀[Успешно] Скачано фото #{i + 1}: {filename}")
                    time.sleep(0.5)  
                except Exception as e:
                    self.log_signal.emit(f"💔[ERROR] Ошибка при скачивании фото: {e}")

            self.log_signal.emit("🍺[INFO] Все фото успешно загружены. Пора идти пить пиво.")

        except Exception as e:
            self.log_signal.emit(f"💔[ERROR] Ошибка работы с альбомом: {e}")

        self.finished_signal.emit()

    def parse_album_input(self, input_str):
        input_str = input_str.strip()

        if not input_str:
            raise ValueError("Пустой ввод")

        owner_id = None
        album_id = None

        if input_str.startswith("http"):
            if "album" not in input_str:
                raise ValueError("Ссылка не содержит информации об альбоме")
            parts = input_str.split("album")[-1].split("_")
            if len(parts) < 2:
                raise ValueError("Неверная ссылка на альбом")
            owner_id = parts[0]
            album_id = parts[1].split("?")[0]

        elif input_str.startswith("album"):
            try:
                _, owner_id, album_id = input_str.split("_", maxsplit=2)
            except ValueError:
                raise ValueError(f"Неверный формат album_id: {input_str}")

        elif "_" in input_str:
            owner_id, album_id = input_str.split("_", maxsplit=1)

        else:
            raise ValueError("Некорректный формат ID или ссылки")

        return int(owner_id), int(album_id)

    def get_album_title(self, vk, owner_id, album_id):
        try:
            albums = vk.photos.getAlbums(owner_id=owner_id, album_ids=[album_id])
            return albums['items'][0]['title']
        except Exception as e:
            self.log_signal.emit(f"🤬[WARN] Название альбома не найдено: {e}")
            return f"альбом_{owner_id}_{album_id}"



class VKAlbumDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VK Album Downloader")
        self.resize(800, 500)

        icon_path = resource_path("ico.ico")
        self.setWindowIcon(QtGui.QIcon(icon_path))

        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                color: white;
                font-family: Arial;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 5px;
                color: white;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #444;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
            QPushButton {
                background-color: #00aaff;
                border: none;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #008ecc;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

        left_widget = QWidget()
        left_layout = QVBoxLayout()

        config = load_config()

        
        self.token_input = QLineEdit(config.get("token", ""))
        left_layout.addWidget(QLabel("Ваш токен API:"))
        left_layout.addWidget(self.token_input)

        
        self.album_input = QLineEdit()
        left_layout.addWidget(QLabel("ID или ссылка на альбом:"))
        left_layout.addWidget(self.album_input)

        
        self.folder_input = QLineEdit(config.get("download_folder", os.path.expanduser("~")))
        self.select_folder_button = QPushButton("Выбрать")
        self.select_folder_button.setFixedWidth(100)
        self.select_folder_button.clicked.connect(self.select_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Папка для загрузки:"))
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.select_folder_button)
        left_layout.addLayout(folder_layout)

        
        self.run_button = QPushButton("Скачать альбом")
        self.run_button.clicked.connect(self.start_download)
        left_layout.addWidget(self.run_button)

        
        self.logo_label = QLabel()
        logo_path = resource_path("bckg.png")
        if os.path.exists(logo_path):
            logo_pixmap = QtGui.QPixmap(logo_path)
            self.logo_label.setPixmap(logo_pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("Логотип не найден")
        self.logo_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.logo_label)

        left_layout.addStretch()
        left_widget.setLayout(left_layout)

        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.log_area)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self.folder_input.setText(folder)

    def start_download(self):
        token = self.token_input.text().strip()
        album_input = self.album_input.text().strip()
        download_folder = self.folder_input.text().strip()

        if not token or not album_input or not download_folder:
            QMessageBox.critical(self, "Ошибка", "Заполните все поля.")
            return

        save_config(token, download_folder, "")

        self.run_button.setEnabled(False)
        self.downloader = AlbumDownloaderWorker(token, album_input, download_folder)
        self.downloader.log_signal.connect(self.append_log)
        self.downloader.finished_signal.connect(lambda: self.run_button.setEnabled(True))
        self.downloader.start()

    @Slot(str)
    def append_log(self, text):
        self.log_area.append(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VKAlbumDownloaderApp()
    window.show()
    sys.exit(app.exec())