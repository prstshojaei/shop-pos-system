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
)


class DiscountDialog(QDialog):
    def __init__(self, product_name, current_discount=0.0, parent=None):
        super().__init__(parent)

        self.product_name = product_name
        self.discount_value = current_discount

        self.setWindowTitle("Set Discount")
        self.setModal(True)
        self.setFixedSize(360, 500)

        self.setup_ui()
        self.apply_styles()

        if current_discount > 0:
            self.discount_input.setText(f"{current_discount:.2f}")

    def setup_ui(self):
        """
        Build the discount dialog UI.
        """
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        self.setLayout(main_layout)

        title_label = QLabel("Set Discount")
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignLeft)

        product_label = QLabel(self.product_name)
        product_label.setObjectName("productLabel")
        product_label.setAlignment(Qt.AlignLeft)

        self.discount_input = QLineEdit()
        self.discount_input.setObjectName("displayInput")
        self.discount_input.setPlaceholderText("0.00")
        self.discount_input.setAlignment(Qt.AlignRight)
        self.discount_input.returnPressed.connect(self.handle_submit)
        self.discount_input.setFocus()

        main_layout.addWidget(title_label)
        main_layout.addWidget(product_label)
        main_layout.addWidget(self.discount_input)

        keypad_wrapper = QWidget()
        keypad_layout = QGridLayout()
        keypad_layout.setContentsMargins(0, 0, 0, 0)
        keypad_layout.setHorizontalSpacing(10)
        keypad_layout.setVerticalSpacing(10)
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
            ("00", 3, 0),
            ("0", 3, 1),
            ("⌫", 3, 2),
        ]

        for text, row, col in buttons:
            button = QPushButton(text)
            button.setObjectName("keypadButton")
            button.setMinimumHeight(70)

            if text == "⌫":
                button.clicked.connect(self.handle_backspace)
            else:
                button.clicked.connect(lambda _, value=text: self.handle_digit(value))

            keypad_layout.addWidget(button, row, col)

        main_layout.addWidget(keypad_wrapper)

        set_discount_button = QPushButton("SET DISCOUNT")
        set_discount_button.setObjectName("submitButton")
        set_discount_button.setMinimumHeight(52)
        set_discount_button.clicked.connect(self.handle_submit)

        clear_button = QPushButton("CLEAR DISCOUNT")
        clear_button.setObjectName("clearButton")
        clear_button.setMinimumHeight(46)
        clear_button.clicked.connect(self.handle_clear)

        main_layout.addWidget(set_discount_button)
        main_layout.addWidget(clear_button)

    def handle_digit(self, value):
        """
        Insert digits into the shared input box.
        """
        current_text = self.discount_input.text()
        self.discount_input.setText(current_text + value)
        self.discount_input.setFocus()

    def handle_backspace(self):
        """
        Remove the last character from the shared input box.
        """
        current_text = self.discount_input.text()
        self.discount_input.setText(current_text[:-1])
        self.discount_input.setFocus()

    def handle_clear(self):
        """
        Clear the current discount.
        """
        self.discount_value = 0.0
        self.accept()

    def handle_submit(self):
        """
        Confirm the selected discount.
        """
        raw_value = self.discount_input.text().strip().replace("£", "").replace(",", "")

        if not raw_value:
            QMessageBox.warning(self, "Missing Discount", "Please enter a discount.")
            return

        try:
            amount = float(raw_value)
        except ValueError:
            QMessageBox.warning(self, "Invalid Discount", "Please enter a valid number.")
            return

        if amount < 0:
            QMessageBox.warning(self, "Invalid Discount", "Discount cannot be negative.")
            return

        self.discount_value = round(amount, 2)
        self.accept()

    def get_discount(self):
        """
        Return the confirmed discount.
        """
        return self.discount_value

    def apply_styles(self):
        """
        Apply dialog styles.
        """
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }

            QLabel#dialogTitle {
                color: #24324a;
                font-size: 18px;
                font-weight: 700;
            }

            QLabel#productLabel {
                color: #6b7280;
                font-size: 14px;
                font-weight: 600;
            }

            QLineEdit#displayInput {
                background-color: #f8fbff;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                padding: 16px;
                color: #24324a;
                font-size: 28px;
                font-weight: 700;
            }

            QLineEdit#displayInput:focus {
                border: 1px solid #2f7cec;
                background-color: #ffffff;
            }

            QPushButton#keypadButton {
                background-color: #ffffff;
                color: #2f3c4f;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                font-size: 22px;
                font-weight: 700;
            }

            QPushButton#keypadButton:hover {
                background-color: #f3f8fe;
            }

            QPushButton#keypadButton:pressed {
                background-color: #e6f0fb;
            }

            QPushButton#submitButton {
                background-color: #2f7cec;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#submitButton:hover {
                background-color: #236dd4;
            }

            QPushButton#submitButton:pressed {
                background-color: #1d5fbc;
            }

            QPushButton#clearButton {
                background-color: #f3f6fa;
                color: #4b5563;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton#clearButton:hover {
                background-color: #e9eff7;
            }
        """)