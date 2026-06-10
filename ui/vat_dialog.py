from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
)


class VatDialog(QDialog):
    def __init__(self, current_vat_number="", current_vat_amount=0.0, parent=None):
        super().__init__(parent)

        self.vat_number_value = current_vat_number.strip()
        self.vat_amount_value = float(current_vat_amount or 0.0)

        self.setWindowTitle("VAT Details")
        self.setModal(True)
        self.setFixedSize(520, 340)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        self.setLayout(main_layout)

        title_label = QLabel("VAT Details")
        title_label.setObjectName("dialogTitle")
        main_layout.addWidget(title_label)

        vat_number_label = QLabel("VAT Number")
        vat_number_label.setObjectName("fieldLabel")
        main_layout.addWidget(vat_number_label)

        self.vat_number_input = QLineEdit()
        self.vat_number_input.setObjectName("fieldInput")
        self.vat_number_input.setPlaceholderText("Example: GB123456789")
        self.vat_number_input.setText(self.vat_number_value)
        self.vat_number_input.setMinimumHeight(48)
        self.vat_number_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.vat_number_input)

        vat_amount_label = QLabel("VAT Amount")
        vat_amount_label.setObjectName("fieldLabel")
        main_layout.addWidget(vat_amount_label)

        self.vat_amount_input = QLineEdit()
        self.vat_amount_input.setObjectName("fieldInput")
        self.vat_amount_input.setPlaceholderText("0.00")
        if self.vat_amount_value > 0:
            self.vat_amount_input.setText(f"{self.vat_amount_value:.2f}")
        self.vat_amount_input.setMinimumHeight(48)
        self.vat_amount_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.vat_amount_input)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        save_button = QPushButton("SAVE VAT")
        save_button.setObjectName("saveButton")
        save_button.setMinimumHeight(48)
        save_button.clicked.connect(self.handle_submit)

        clear_button = QPushButton("CLEAR VAT")
        clear_button.setObjectName("clearButton")
        clear_button.setMinimumHeight(48)
        clear_button.clicked.connect(self.handle_clear)

        button_row.addWidget(save_button)
        button_row.addWidget(clear_button)

        main_layout.addSpacing(4)
        main_layout.addLayout(button_row)

    def handle_submit(self):
        vat_number = self.vat_number_input.text().strip()
        raw_amount = self.vat_amount_input.text().strip().replace("£", "").replace(",", "")

        if raw_amount:
            try:
                amount = float(raw_amount)
            except ValueError:
                QMessageBox.warning(self, "Invalid VAT", "Please enter a valid VAT amount.")
                return

            if amount < 0:
                QMessageBox.warning(self, "Invalid VAT", "VAT amount cannot be negative.")
                return
        else:
            amount = 0.0

        self.vat_number_value = vat_number
        self.vat_amount_value = round(amount, 2)
        self.accept()

    def handle_clear(self):
        self.vat_number_value = ""
        self.vat_amount_value = 0.0
        self.accept()

    def get_vat_number(self):
        return self.vat_number_value

    def get_vat_amount(self):
        return self.vat_amount_value

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }

            QLabel#dialogTitle {
                color: #24324a;
                font-size: 20px;
                font-weight: 700;
                margin-bottom: 4px;
            }

            QLabel#fieldLabel {
                color: #617084;
                font-size: 13px;
                font-weight: 700;
                margin-top: 2px;
            }

            QLineEdit#fieldInput {
                background-color: #f8fbff;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                padding: 12px 14px;
                color: #24324a;
                font-size: 14px;
            }

            QLineEdit#fieldInput:focus {
                background-color: #ffffff;
                border: 1px solid #2f7cec;
            }

            QPushButton#saveButton {
                background-color: #2f7cec;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton#saveButton:hover {
                background-color: #236dd4;
            }

            QPushButton#clearButton {
                background-color: #eef3f9;
                color: #425066;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton#clearButton:hover {
                background-color: #e3ebf5;
            }
        """)