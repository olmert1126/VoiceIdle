import io
import sys
import pyttsx3
import threading
import sqlite3
import re
import html
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout, \
    QLabel, QFileDialog, QInputDialog
from PyQt6.QtGui import QShortcut, QKeySequence, QPixmap
from PyQt6.QtCore import Qt

if sys.platform == "win32":
    import pythoncom

template = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>1200</width>
    <height>800</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>idle</string>
  </property>
  <widget class="QTextBrowser" name="out_code">
   <property name="geometry">
    <rect>
     <x>50</x>
     <y>520</y>
     <width>1031</width>
     <height>231</height>
    </rect>
   </property>
  </widget>
  <widget class="QPushButton" name="start_code">
   <property name="geometry">
    <rect>
     <x>220</x>
     <y>30</y>
     <width>291</width>
     <height>51</height>
    </rect>
   </property>
   <property name="font">
    <font>
     <pointsize>16</pointsize>
    </font>
   </property>
   <property name="text">
    <string>start</string>
   </property>
  </widget>
  <widget class="QPlainTextEdit" name="input_code">
   <property name="geometry">
    <rect>
     <x>50</x>
     <y>90</y>
     <width>1031</width>
     <height>391</height>
    </rect>
   </property>
  </widget>
  <widget class="QPushButton" name="help_btn">
   <property name="geometry">
    <rect>
     <x>540</x>
     <y>30</y>
     <width>231</width>
     <height>51</height>
    </rect>
   </property>
   <property name="font">
    <font>
     <pointsize>16</pointsize>
    </font>
   </property>
   <property name="text">
    <string>help</string>
   </property>
  </widget>
  <widget class="QProgressBar" name="progressBar">
   <property name="geometry">
    <rect>
     <x>820</x>
     <y>40</y>
     <width>331</width>
     <height>31</height>
    </rect>
   </property>
   <property name="maximum">
    <number>1000</number>
   </property>
   <property name="value">
    <number>0</number>
   </property>
  </widget>
 </widget>
 <tabstops>
  <tabstop>input_code</tabstop>
  <tabstop>start_code</tabstop>
  <tabstop>out_code</tabstop>
 </tabstops>
 <resources/>
 <connections/>
</ui>
"""


def resource_path(relative_path):
    """ Получить абсолютный путь к ресурсу (работает и в .py, и в .exe) """
    try:
        # PyInstaller временная папка
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class TextToSpeech:  # класс реализующий озвучку, игнорит текст пока недоозвучит прошлый
    def __init__(self):
        self._lock = threading.Lock()

    def say(self, text: str):
        if not text.strip():
            return

        thread = threading.Thread(target=self._speak, args=(text,), daemon=True)
        thread.start()

    def _speak(self, text: str):
        if not self._lock.acquire(blocking=False):
            return

        try:
            if sys.platform == "win32":
                pythoncom.CoInitialize()

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()

        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            if sys.platform == "win32":
                pythoncom.CoUninitialize()  # Очистка потока
            self._lock.release()


class FirstWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предисловие")
        self.tts = TextToSpeech()
        self.resize(600, 400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Изображение
        image_label = QLabel()
        pixmap = QPixmap(resource_path("logo.png"))
        if not pixmap.isNull():
            scaled = pixmap.scaledToWidth(
                200,
                Qt.TransformationMode.SmoothTransformation
            )
            image_label.setPixmap(scaled)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

        # Текст
        text_label = QLabel(
            "Добро пожаловать в наше приложение, нажмите F1 для прослушки инструкции в основном окне, нажмите f6 для закрытия окна или нажмие на кнопку")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)
        self.tts.say(
            "Добро пожаловать в наше приложение, нажмите F1 для прослушки инструкции в основном окне, нажмите f6 для закрытия окна или нажмие на кнопку")

        btn = QPushButton("Закрыть")
        shortcut_f6 = QShortcut(QKeySequence("F6"), self)
        btn.clicked.connect(self.accept)
        shortcut_f6.activated.connect(self.accept)
        layout.addWidget(btn)

        self.setLayout(layout)


class Idle(QMainWindow):
    def __init__(self):
        super().__init__()
        f = io.StringIO(template)
        uic.loadUi(f, self)
        self.tts = TextToSpeech()

        self.shortcut_f5 = QShortcut(QKeySequence("F5"),
                                     self)  # шортскапы ОБЯЗАТЕЛЬНО создавай тут чтобы неломался __init__
        self.shortcut_f7 = QShortcut(QKeySequence("F7"), self)
        self.shortcut_f1 = QShortcut(QKeySequence("F1"), self)
        self.shortcut_f6 = QShortcut(QKeySequence("F6"), self)
        self.shortcut_f4 = QShortcut(QKeySequence("F4"), self)
        self.shortcut_f2 = QShortcut(QKeySequence("F2"), self)

        self.connect_key()

        dialog = FirstWindow(self)
        result = dialog.exec()
        self.have_nvda = (result == QDialog.DialogCode.Accepted)

        self.input_code.setTabStopDistance(16)
        self.input_code.installEventFilter(self)  # добавь

        # Получаем меню-бар
        menu_bar = self.menuBar()

        # Меню «Файл»
        file_menu = menu_bar.addMenu("Файл")

        # Действия
        open_action = file_menu.addAction("Открыть файл")
        save_action = file_menu.addAction("Сохранить результат")
        exit_action = file_menu.addAction("Выход")

        exit_action.triggered.connect(self.close)  # close() — закрыть окно

        edit_menu = menu_bar.addMenu("Настройки")
        sub_menu = edit_menu.addMenu("Сменить тему")
        st_light = sub_menu.addAction("Светлая")
        st_dark = sub_menu.addAction("Темная")
        st_yellow = sub_menu.addAction("Желтая")
        # Темная тема
        self.stylesheet_dark = """
                                /* Основной фон — тёмный, но не чёрный (меньше усталости глаз) */
            QMainWindow {
                background-color: #1e1e1e;
            }

            /* Текстовые поля — фон чуть светлее фона окна, текст белее */
            QTextBrowser,
            QPlainTextEdit {
                background-color: #2d2d2d;
                color: #d4d4d4;             /* AAA для 14px на #2d2d2d: 12.6:1 ✅ */
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
                font-family: "Fira Code", "Courier New", monospace;
                selection-background-color: #3a5795;   /* Синий акцент (как в VS Code) */
                selection-color: #ffffff;
            }

            /* Меню */
            QMenuBar {
                background-color: #252526;
                color: #cccccc;              /* AAA: 10.8:1 ✅ */
                padding: 2px;
                border-bottom: 1px solid #3e3e42;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #3a3a3c;
            }

            QMenu {
                background-color: #2d2d30;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 3px;
            }

            QMenu::item:selected {
                background-color: #3a3a3c;
            }

            /* Кнопки */
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;              /* AA: 7.2:1 ✅ */
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                min-height: 26px;
            }

            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #4da6ff;
            }

            QPushButton:pressed {
                background-color: #2b5aa0;
                color: #ffffff;              /* AAA: 5.8:1 ✅ */
                border: 1px solid #214d80;
            }

            QPushButton:disabled {
                background-color: #353535;
                color: #7a7a7a;
                border: 1px solid #444444;
            }

            /* Прочие виджеты */
            QLabel {
                color: #cccccc;
                font-size: 14px;
            }

            QLineEdit {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }

            QLineEdit:focus {
                border: 1px solid #4da6ff;
            }

            QScrollBar:vertical {
                background-color: #252526;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 24px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #7a7a7a;
            }
                            """
        # Светлая тема
        self.stylesheet_light = """
                    /* Стиль для всего главного окна */
                    QMainWindow {
                        background-color: #f0f0f0; /* Светло-серый фон */
                    }

                    /* Стиль для текстового поля */
                    QTextBrowser {
                        background-color: #ffffff; /* Белый фон */
                        color: #333333; /* Тёмно-серый текст */
                        border: 2px solid #cccccc; /* Светло-серая рамка */
                        font-size: 14px;
                        font-family: "Courier New", monospace;
                        border-radius: 5px;
                    }

                    /* Стиль для текстового поля */
                    QPlainTextEdit {
                        background-color: #ffffff; /* Белый фон */
                        color: #333333; /* Тёмно-серый текст */
                        border: 2px solid #cccccc; /* Светло-серая рамка */
                        font-size: 14px;
                        font-family: "Courier New", monospace;
                        border-radius: 5px;
                    }

                    /* Стиль для всего меню-бара */
                    QMenuBar {
                        background-color: #ffffff;
                        color: #333333;
                        border-bottom: 1px solid #cccccc;
                    }

                    /* Стиль для отдельного пункта меню */
                    QMenuBar::item {
                        background-color: transparent;
                        padding: 5px 10px;
                    }

                    /* Стиль для пункта меню при его выборе */
                    QMenuBar::item:selected {
                        background-color: #e6e6e6;
                        border-radius: 3px;
                    }

                    /* Стиль для выпадающего меню */
                    QMenu {
                        background-color: #ffffff;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 5px;
                        padding: 5px;
                    }

                    /* Стиль для пунктов в выпадающем меню */
                    QMenu::item {
                        padding: 5px 20px 5px 20px;
                        border-radius: 3px;
                    }

                    /* Стиль для пунктов в выпадающем меню при наведении */
                    QMenu::item:selected {
                        background-color: #3498db;
                        color: #ffffff;
                    }

                    /* Стиль для кнопок */
                    QPushButton {
                        background-color: #ffffff;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 5px;
                        padding: 8px 15px;
                        font-weight: bold;
                    }

                    /* Стиль для кнопок при наведении мышки */
                    QPushButton:hover {
                        background-color: #3498db;
                        color: #ffffff;
                        border: 1px solid #2980b9;
                        border-radius: 5px;
                    }

                    /* Стиль для кнопок при клике мышки */
                    QPushButton:pressed {
                        background-color: #2980b9;
                        border: 1px solid #1f618d;
                        border-radius: 5px;
                    }

                    /* Стиль для disabled кнопок */
                    QPushButton:disabled {
                        background-color: #f8f9fa;
                        color: #6c757d;
                        border: 1px solid #dee2e6;
                    }

                    /* Дополнительные стили для других виджетов */
                    QLabel {
                        color: #333333;
                        font-size: 13px;
                    }

                    QLineEdit {
                        background-color: #ffffff;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 3px;
                        padding: 5px;
                        font-size: 13px;
                    }

                    QLineEdit:focus {
                        border: 1px solid #3498db;
                    }

                    QScrollBar:vertical {
                        background-color: #f8f9fa;
                        width: 15px;
                        margin: 0px;
                    }

                    QScrollBar::handle:vertical {
                        background-color: #cccccc;
                        border-radius: 7px;
                        min-height: 20px;
                    }

                    QScrollBar::handle:vertical:hover {
                        background-color: #aaaaaa;
                    }
                """
        # Желтая тема
        self.stylesheet_yellow = """
            QMainWindow {
                background-color: #fdf6e3; /* Solarized base3 — тёплый, немигрирующий */
            }

            QTextBrowser,
            QPlainTextEdit {
                background-color: #fefcf9; /* Чистый, но не белый */
                color: #584a37;            /* Тёмно-коричневый — контраст 12.1:1 ✅ */
                border: 1px solid #d7c9b1;
                border-radius: 4px;
                padding: 6px;
                font-size: 15px;
                font-family: "Cascadia Code", "Courier New", monospace;
                font-weight: 500;
                selection-background-color: #f5c27a;  /* Тёплый оранжево-жёлтый */
                selection-color: #2d261e;
            }

            QMenuBar {
                background-color: #fdf6e3;
                color: #584a37;
                border-bottom: 1px solid #d7c9b1;
                padding: 2px;
            }

            QMenuBar::item {
                padding: 6px 12px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #f5c27a;
                color: #2d261e;
            }

            QMenu {
                background-color: #fdf6e3;
                color: #584a37;
                border: 1px solid #d7c9b1;
                border-radius: 4px;
                padding: 4px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 3px;
            }

            QMenu::item:selected {
                background-color: #f5c27a;
                color: #2d261e;
            }

            QPushButton {
                background-color: #fdf6e3;
                color: #584a37;
                border: 1px solid #d7c9b1;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
                min-height: 26px;
            }

            QPushButton:hover {
                background-color: #f5c27a;
                color: #2d261e;
                border: 1px solid #e0a855;
            }

            QPushButton:pressed {
                background-color: #d99e4c;
                color: #ffffff;
                border: 1px solid #b8860b;
            }

            QPushButton:disabled {
                background-color: #f3eadf;
                color: #a0907c;
                border: 1px solid #d7c9b1;
            }

            QLabel {
                color: #584a37;
                font-size: 14px;
                font-weight: 500;
            }

            QLineEdit {
                background-color: #fefcf9;
                color: #584a37;
                border: 1px solid #d7c9b1;
                border-radius: 4px;
                padding: 6px;
            }

            QLineEdit:focus {
                border: 1px solid #e0a855;
                background-color: #ffffff;
            }

            QScrollBar:vertical {
                background-color: #f7efdb;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #d7c9b1;
                border-radius: 6px;
                min-height: 24px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #c2a98a;
            }
        """

        # Устанавливаем светлую тему по умолчанию
        self.setStyleSheet(self.stylesheet_light)
        # Подключаем кнопочки
        open_action.triggered.connect(self.open_file)
        save_action.triggered.connect(self.save_file)

        st_light.triggered.connect(self.change_light)
        st_dark.triggered.connect(self.change_dark)
        st_yellow.triggered.connect(self.change_yellow)

    # Функция смены темы
    def change_light(self):
        # Переключаем на светлую тему
        self.setStyleSheet(self.stylesheet_light)

    def change_dark(self):
        # Переключаем на светлую тему
        self.setStyleSheet(self.stylesheet_dark)

    def change_yellow(self):
        # Переключаем на светлую тему
        self.setStyleSheet(self.stylesheet_yellow)

    def code(self):
        text = self.input_code.toPlainText()
        self.save_code(text)
        self.progress_bar()

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        def gui_input(prompt=""):
            self.tts.say("окно ввода")
            text, ok = QInputDialog.getText(None, "Ввод", str(prompt))
            if ok:
                self.tts.say(text)
                return text
            else:
                return ""

        exec_globals = {
            '__builtins__': {
                **(__builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)),
                'input': gui_input,  # подменяем input
            }
        }
        try:
            exec(text, exec_globals)
            output = redirected_output.getvalue()
            output_escaped = html.escape(output)
            self.out_code.setHtml(f'<pre>{output_escaped}</pre>')
            self.tts.say(output_escaped)

        except Exception as e:
            error_msg = str(e)
            translated_msg = self.translate_error_message(error_msg)
            output = f"Ошибка: {translated_msg}"
            self.out_code.setHtml(output)
            self.tts.say(output)

        finally:
            sys.stdout = old_stdout

    def connect_key(
            self):  # Сюда вписываешь все связи клавишь с функциями, в функцию для озвучки клавиатуры не добовляй использующиеся клавиши они озвучены
        self.start_code.clicked.connect(self.code)
        self.help_btn.clicked.connect(self.show_help)

        self.shortcut_f5.activated.connect(self.code)
        self.shortcut_f7.activated.connect(self.load)
        self.shortcut_f1.activated.connect(self.show_help)
        self.shortcut_f6.activated.connect(self.focus_input_code)  # добавь
        self.shortcut_f4.activated.connect(self.focus_cursor)  # добавь
        self.shortcut_f2.activated.connect(self.voiceover_of_the_entire_line)

    def save_code(self, new_code):  # Сохранение кода
        with sqlite3.connect("codes.db") as con:
            cur = con.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS code_store
                        (
                            code
                            TEXT
                            NOT
                            NULL
                        )
                        """)
            cur.execute("DELETE FROM code_store")
            cur.execute("INSERT INTO code_store (code) VALUES (?)", (new_code,))

    def load_code(self):  # Загрузка кода
        with sqlite3.connect("codes.db") as con:
            cur = con.cursor()
            cur.execute("SELECT code FROM code_store LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None

    def load(self):
        code = self.load_code()
        if code:
            self.input_code.setPlainText(code)
        else:
            self.input_code.setPlainText("")

    def show_help(self):
        voice_text = """
        Эта программа - среда для выполнения Python кода с поддержкой озвучки.
        Введите код в верхнее поле, нажмите Start или F5 для выполнения.
        Также имеется клавиша f7 возвращающая прошлый введённый код.
        При нажатии на f6 ваш курсор переместиться в строку ввода.
        При нажатии на f4 озвучиться номер строки, а также в каком классе или в функции находиться курсор.
        При нажатии на f2 будет озвучена вся строка на которойнаходиться курсор.
        Можете нажать кнопку help, чтобы повторно прослушать справку о программе.
        """
        self.tts.say(voice_text)
        self.out_code.setHtml(voice_text)

    def focus_input_code(self):  # активация input_code
        self.input_code.setFocus()
        self.input_code.activateWindow()

    def focus_cursor(self):  # Определение строки, а также класса и функции
        cursor = self.input_code.textCursor()
        line_number = cursor.blockNumber() + 1
        code = self.input_code.toPlainText()
        func, cls = self.cursor_in_class_in_func(code, line_number - 1)
        print(func, cls)
        if cls:  # озвучка
            if func:
                self.tts.say(f"Курсор на строке: {line_number}, в классе {cls} и в функции {func}")
            else:
                self.tts.say(f"Курсор на строке: {line_number}, в классе {cls}")
        elif func:
            self.tts.say(f"Курсор на строке: {line_number}, в функции {func}")
        else:
            self.tts.say(f"Курсор на строке: {line_number}")

    def cursor_in_class_in_func(self, code: str,
                                line_index: int):  # Отпределение в каком классе или в функции находиться курсор
        lines = code.splitlines()
        if not lines or line_index < 0 or line_index >= len(lines):
            return None, None

        stack = []
        for i in range(line_index + 1):
            line = lines[i]
            code_part = line.split('#', 1)[0].rstrip()
            if not code_part:
                continue

            indent = len(line) - len(line.lstrip())
            stripped = code_part.lstrip()

            while stack and stack[-1][2] >= indent:
                stack.pop()

            if stripped.startswith('class '):
                match = re.match(r'class\s+(\w+)', stripped)
                if match:
                    stack.append(('class', match.group(1), indent))
            elif stripped.startswith('def '):
                match = re.match(r'def\s+(\w+)', stripped)
                if match:
                    stack.append(('def', match.group(1), indent))

            if i == line_index:
                current_class = None
                current_func = None
                for block_type, name, _ in reversed(stack):
                    if block_type == 'class':
                        current_class = name
                    elif block_type == 'def':
                        current_func = name
                return current_func, current_class

        return None, None

    def voiceover_of_the_entire_line(self):
        cursor = self.input_code.textCursor()
        line_number = cursor.blockNumber()
        code = self.input_code.toPlainText().split("\n")
        self.tts.say(code[line_number])

    def open_file(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Открыть текст", "",
                                                       "Python Files (*.py);;Text Files (*.txt);;All Files (*)")
            if file_name:  # Если выбрали файл
                with open(file_name, 'r', encoding='utf-8') as file:  # 'r' — read, как чтение книги
                    text = file.read()
                    self.input_code.setPlainText(text)
        except Exception as e:
            print(f"Ошибка: {e}")

    def save_file(self):
        # Диалог сохранения
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить текст", "",
                                                   "Python Files (*.py);;Text Files (*.txt);;All Files (*)")
        if file_name:
            text = self.input_code.toPlainText()  # Берём текст из браузера
            with open(file_name, 'w', encoding='utf-8') as file:  # 'w' — write, как запись в дневник
                file.write(text)

    def eventFilter(self, obj, event):  # автотаб после нажатия enter
        if obj == self.input_code and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                cursor = self.input_code.textCursor()
                block = cursor.block()
                line = block.text().rstrip()

                if line and line.endswith(':'):
                    raw_indent = line[:len(line) - len(line.lstrip())]
                    new_indent = raw_indent + '\t'

                    cursor.insertText(f"\n{new_indent}")

                    self.input_code.setTextCursor(cursor)
                    return True  # отмена стандартного enter

        return super().eventFilter(obj, event)

    def progress_bar(self):
        cursor = self.input_code.textCursor()
        line_number = cursor.blockNumber() + 1
        self.progressBar.setValue(line_number)

    def translate_error_message(self, error_msg: str) -> str:
        translations = {
            r"can only concatenate str \(not \"(.*)\"\) to str": "можно объединять только строки, а не '{}' со строкой",
            r"division by zero": "деление на ноль",
            r"list index out of range": "индекс списка вне диапазона",
            r"tuple index out of range": "индекс кортежа вне диапазона",
            r"string index out of range": "индекс строки вне диапазона",
            r"name '(.*)' is not defined": "имя '{}' не определено",
            r"'(.*)' object is not callable": "объект '{}' не является вызываемым",
            r"'(.*)' object has no attribute '(.*)'": "объект '{}' не имеет атрибута '{}'",
            r"unexpected EOF while parsing": "неожиданный конец файла при разборе",
            r"invalid syntax": "неверный синтаксис",
            r"expected an indented block after '(.*)'": "ожидался отступ после '{}'",
            r"unexpected indent": "неожиданный отступ",
            r"unindent does not match any outer indentation level": "уровень отступа не соответствует внешнему блоку",
            r"invalid literal for int\(\) with base 10: '(.*)'": "недопустимый литерал для int() с основанием 10: '{}'",
            r"invalid literal for float\(\): '(.*)'": "недопустимый литерал для float(): '{}'",
            r"maximum recursion depth exceeded": "превышена максимальная глубина рекурсии",
            r"dictionary changed size during iteration": "размер словаря изменился во время итерации",
            r"file not found": "файл не найден",
            r"\[Errno 2\] No such file or directory: '(.*)'": "файл не найден: '{}'",
            r"EOL while scanning string literal": "достигнут конец строки при чтении строкового литерала",
            r"EOF while scanning triple-quoted string literal": "достигнут конец файла при чтении многострочной строки",
            r"missing parentheses in call to '(.*)'": "пропущены скобки при вызове '{}'",
            r"can't assign to literal": "нельзя присвоить значение литералу",
            r"can't assign to function call": "нельзя присвоить значение вызову функции",
            r"'(.*)' is not defined": "переменная '{}' не определена",
            r"too many values to unpack \(expected (.*)\)": "слишком много значений для распаковки (ожидалось {})",
            r"not enough values to unpack \(expected (.*)\)": "недостаточно значений для распаковки (ожидалось {})",
            r"attempt to assign to subscripted .*": "попытка присвоить значение элементу, не поддерживающему запись",
        }

        import re
        for pattern, translation in translations.items():
            match = re.fullmatch(pattern, error_msg)
            if match:
                if '{}' in translation:
                    # Подставляем захваченные группы или оригинал
                    groups = match.groups()
                    if groups:
                        return translation.format(*groups)
                    else:
                        return translation.format(error_msg)
                return translation
        return error_msg


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Idle()
    ex.show()
    sys.exit(app.exec())