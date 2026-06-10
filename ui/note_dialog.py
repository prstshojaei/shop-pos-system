from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class NoteDialog(QDialog):
    def __init__(self, product_name, current_note="", parent=None):
        super().__init__(parent)

        self.product_name = product_name
        self.note_value = current_note.strip()

        self.setWindowTitle("Add Note")
        self.setModal(True)
        self.setFixedSize(420, 320)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        """
        Build the note dialog UI.
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        self.setLayout(layout)

        title_label = QLabel("Add Note")
        title_label.setObjectName("dialogTitle")

        product_label = QLabel(self.product_name)
        product_label.setObjectName("productLabel")

        self.note_input = QTextEdit()
        self.note_input.setObjectName("noteInput")
        self.note_input.setPlaceholderText("Write a note for this item...")
        self.note_input.setPlainText(self.note_value)

        done_button = QPushButton("DONE")
        done_button.setObjectName("doneButton")
        done_button.clicked.connect(self.handle_submit)

        layout.addWidget(title_label)
        layout.addWidget(product_label)
        layout.addWidget(self.note_input)
        layout.addWidget(done_button)

    def handle_submit(self):
        """
        Save the entered note and close the dialog.
        """
        note_text = self.note_input.toPlainText().strip()

        if len(note_text) > 250:
            QMessageBox.warning(
                self,
                "Note Too Long",
                "Please keep the note under 250 characters.",
            )
            return

        self.note_value = note_text
        self.accept()

    def get_note(self):
        """
        Return the saved note text.
        """
        return self.note_value

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

            QTextEdit#noteInput {
                background-color: #f8fbff;
                border: 1px solid #dbe5f0;
                border-radius: 12px;
                padding: 10px;
                color: #24324a;
                font-size: 14px;
            }

            QTextEdit#noteInput:focus {
                border: 1px solid #2f7cec;
                background-color: white;
            }

            QPushButton#doneButton {
                background-color: #2f7cec;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 700;
                padding: 12px;
            }

            QPushButton#doneButton:hover {
                background-color: #236dd4;
            }

            QPushButton#doneButton:pressed {
                background-color: #1d5fbc;
            }
        """)