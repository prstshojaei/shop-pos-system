from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QSizePolicy,
)


class PriceDialog(QDialog):
    def __init__(self, product_name, parent=None):
        super().__init__(parent)

        self.product_name = product_name
        self.price_value = None

        self.setWindowTitle("Set Price per Unit")
        self.setModal(True)
        self.setFixedSize(360, 520)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        self.setLayout(main_layout)

        title_label = QLabel("Set Price per Unit")
        title_label.setObjectName("dialogTitle")

        product_label = QLabel(self.product_name)
        product_label.setObjectName("productLabel")
        product_label.setWordWrap(True)

        self.price_input = QLineEdit()
        self.price_input.setObjectName("displayInput")
        self.price_input.setPlaceholderText("0.00")
        self.price_input.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.price_input.returnPressed.connect(self.handle_submit)
        self.price_input.setFocus()

        main_layout.addWidget(title_label)
        main_layout.addWidget(product_label)
        main_layout.addWidget(self.price_input)

        keypad_wrapper = QWidget()
        keypad_layout = QGridLayout()
        keypad_layout.setContentsMargins(0, 0, 0, 0)
        keypad_layout.setHorizontalSpacing(8)
        keypad_layout.setVerticalSpacing(8)
        keypad_wrapper.setLayout(keypad_layout)

        buttons = [
            ("1", 0, 0),
            ("2", 0, 1),
            ("3", 0, 2),
            ("4", 1, 0),
            ("5", 1, 1),
            ("6", 1, 2),
            ("7", 2, 0),
            ("8", 2, 1),
            ("9", 2, 2),
            (".", 3, 0),
            ("0", 3, 1),
            ("⌫", 3, 2),
        ]

        for text, row, col in buttons:
            button = QPushButton(text)
            button.setObjectName("keypadButton")
            button.setFocusPolicy(Qt.NoFocus)
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.setMinimumSize(90, 80)
            button.setMaximumSize(90, 80)

            if text == "⌫":
                button.clicked.connect(self.handle_backspace)
            elif text == ".":
                button.clicked.connect(self.handle_dot)
            else:
                button.clicked.connect(lambda _, v=text: self.handle_digit(v))

            keypad_layout.addWidget(button, row, col, alignment=Qt.AlignCenter)

        for row in range(4):
            keypad_layout.setRowStretch(row, 1)

        for col in range(3):
            keypad_layout.setColumnStretch(col, 1)

        main_layout.addWidget(keypad_wrapper)

        submit_btn = QPushButton("SET PRICE")
        submit_btn.setObjectName("submitButton")
        submit_btn.setFocusPolicy(Qt.NoFocus)
        submit_btn.setMinimumHeight(52)
        submit_btn.clicked.connect(self.handle_submit)

        main_layout.addWidget(submit_btn)

    def handle_digit(self, value):
        current = self.price_input.text()
        self.price_input.setText(current + value)
        self.price_input.setFocus()

    def handle_dot(self):
        current = self.price_input.text()

        if not current:
            self.price_input.setText("0.")
        elif "." not in current:
            self.price_input.setText(current + ".")

        self.price_input.setFocus()

    def handle_backspace(self):
        current = self.price_input.text()
        self.price_input.setText(current[:-1])
        self.price_input.setFocus()

    def handle_submit(self):
        raw = self.price_input.text().strip()

        if not raw:
            QMessageBox.warning(self, "Error", "Enter a price")
            return

        if raw == ".":
            QMessageBox.warning(self, "Error", "Invalid number")
            return

        try:
            value = float(raw)
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid number")
            return

        if value <= 0:
            QMessageBox.warning(self, "Error", "Price must be > 0")
            return

        self.price_value = round(value, 2)
        self.accept()

    def get_price(self):
        return self.price_value

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }

            QLabel#dialogTitle {
                font-size: 18px;
                font-weight: 700;
                color: #24324a;
            }

            QLabel#productLabel {
                font-size: 14px;
                color: #6b7280;
                font-weight: 600;
            }

            QLineEdit#displayInput {
                background-color: #f8fbff;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                padding: 14px 16px;
                font-size: 26px;
                font-weight: 700;
                color: #24324a;
                min-height: 52px;
            }

            QLineEdit#displayInput:focus {
                background-color: #ffffff;
                border: 1px solid #2f7cec;
            }

            QPushButton#keypadButton {
                background-color: #ffffff;
                color: #2f3c4f;
                border: 1px solid #d6e2f1;
                border-radius: 10px;
                font-size: 20px;
                font-weight: 600;
                padding: 8px;
                margin: 0px;
            }

            QPushButton#keypadButton:hover {
                background-color: #f4f8fd;
            }

            QPushButton#keypadButton:pressed {
                background-color: #e6f0fb;
                border: 1px solid #2f7cec;
            }

            QPushButton#submitButton {
                background-color: #2f7cec;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#submitButton:hover {
                background-color: #236dd4;
            }

            QPushButton#submitButton:pressed {
                background-color: #1d5fbc;
            }
        """)