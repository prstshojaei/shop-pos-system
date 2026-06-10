from copy import deepcopy
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from database import (
    delete_order,
    get_all_orders,
    get_order_by_id,
    get_order_items,
    search_orders,
    update_order,
)
from ui.end_of_day_report import EndOfDayReportDialog
from ui.receipt_printer import ReceiptPreviewDialog


class EditOrderDialog(QDialog):
    def __init__(self, order, items, parent=None):
        super().__init__(parent)

        self.order = deepcopy(order)
        self.items = deepcopy(items)

        self.setWindowTitle(f"Edit Order - {self.order['order_number']}")
        self.resize(900, 700)
        self.setup_ui()
        self.refresh_items_ui()
        self.apply_styles()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        self.setLayout(main_layout)

        title_label = QLabel(f"Edit Order - {self.order['order_number']}")
        title_label.setObjectName("dialogTitle")
        main_layout.addWidget(title_label)

        customer_card = QFrame()
        customer_card.setObjectName("card")
        customer_layout = QGridLayout()
        customer_layout.setContentsMargins(14, 14, 14, 14)
        customer_layout.setHorizontalSpacing(12)
        customer_layout.setVerticalSpacing(10)
        customer_card.setLayout(customer_layout)

        customer_name_label = QLabel("Customer Name")
        customer_name_label.setObjectName("fieldLabel")
        self.customer_name_input = QLineEdit()
        self.customer_name_input.setObjectName("fieldInput")
        self.customer_name_input.setText(self.order.get("customer_name", "") or "")

        customer_phone_label = QLabel("Phone Number")
        customer_phone_label.setObjectName("fieldLabel")
        self.customer_phone_input = QLineEdit()
        self.customer_phone_input.setObjectName("fieldInput")
        self.customer_phone_input.setText(self.order.get("customer_phone", "") or "")

        customer_layout.addWidget(customer_name_label, 0, 0)
        customer_layout.addWidget(self.customer_name_input, 0, 1)
        customer_layout.addWidget(customer_phone_label, 1, 0)
        customer_layout.addWidget(self.customer_phone_input, 1, 1)

        main_layout.addWidget(customer_card)

        add_button_row = QHBoxLayout()
        add_button_row.addStretch()

        add_item_button = QPushButton("Add Item")
        add_item_button.setObjectName("primaryButton")
        add_item_button.clicked.connect(self.handle_add_item)
        add_button_row.addWidget(add_item_button)

        main_layout.addLayout(add_button_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.scroll_content = QWidget()
        self.items_layout = QVBoxLayout()
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(12)
        self.scroll_content.setLayout(self.items_layout)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        main_layout.addWidget(self.summary_label)

        button_row = QHBoxLayout()
        button_row.addStretch()

        save_button = QPushButton("Save Changes")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.handle_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)

        button_row.addWidget(save_button)
        button_row.addWidget(cancel_button)

        main_layout.addLayout(button_row)

    def handle_add_item(self):
        self.items.append({
            "product_name": "NEW PRODUCT",
            "unit_price": 0.0,
            "quantity": 1,
            "note": "",
            "discount": 0.0,
        })
        self.refresh_items_ui()

    def handle_remove_item(self, index):
        self.items.pop(index)
        self.refresh_items_ui()

    def clear_items_layout(self):
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def refresh_items_ui(self):
        self.clear_items_layout()

        if not self.items:
            empty = QLabel("No items in this order. Add at least one item.")
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumHeight(120)
            self.items_layout.addWidget(empty)
            self.update_summary()
            return

        for index, item in enumerate(self.items):
            card = QFrame()
            card.setObjectName("card")

            layout = QGridLayout()
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setHorizontalSpacing(12)
            layout.setVerticalSpacing(10)
            card.setLayout(layout)

            product_label = QLabel("Product")
            product_label.setObjectName("fieldLabel")
            product_input = QLineEdit()
            product_input.setObjectName("fieldInput")
            product_input.setText(str(item.get("product_name", "")))
            product_input.textChanged.connect(
                lambda text, i=index: self.update_item_field(i, "product_name", text)
            )

            quantity_label = QLabel("Quantity")
            quantity_label.setObjectName("fieldLabel")
            quantity_input = QSpinBox()
            quantity_input.setMinimum(1)
            quantity_input.setMaximum(9999)
            quantity_input.setValue(int(item.get("quantity", 1)))
            quantity_input.valueChanged.connect(
                lambda value, i=index: self.update_item_field(i, "quantity", value)
            )

            unit_price_label = QLabel("Unit Price")
            unit_price_label.setObjectName("fieldLabel")
            unit_price_input = QDoubleSpinBox()
            unit_price_input.setMinimum(0.0)
            unit_price_input.setMaximum(999999.99)
            unit_price_input.setDecimals(2)
            unit_price_input.setSingleStep(0.50)
            unit_price_input.setValue(float(item.get("unit_price", 0.0)))
            unit_price_input.valueChanged.connect(
                lambda value, i=index: self.update_item_field(i, "unit_price", value)
            )

            discount_label = QLabel("Discount")
            discount_label.setObjectName("fieldLabel")
            discount_input = QDoubleSpinBox()
            discount_input.setMinimum(0.0)
            discount_input.setMaximum(999999.99)
            discount_input.setDecimals(2)
            discount_input.setSingleStep(0.50)
            discount_input.setValue(float(item.get("discount", 0.0)))
            discount_input.valueChanged.connect(
                lambda value, i=index: self.update_item_field(i, "discount", value)
            )

            note_label = QLabel("Note")
            note_label.setObjectName("fieldLabel")
            note_input = QTextEdit()
            note_input.setObjectName("noteInput")
            note_input.setFixedHeight(70)
            note_input.setPlainText(str(item.get("note", "")))
            note_input.textChanged.connect(
                lambda i=index, widget=note_input: self.update_item_field(
                    i, "note", widget.toPlainText()
                )
            )

            remove_button = QPushButton("Remove Item")
            remove_button.setObjectName("dangerButton")
            remove_button.clicked.connect(lambda _, i=index: self.handle_remove_item(i))

            line_total = max(
                float(item.get("unit_price", 0.0)) * int(item.get("quantity", 0))
                - float(item.get("discount", 0.0)),
                0.0,
            )
            line_total_label = QLabel(f"Line Total: £{line_total:.2f}")
            line_total_label.setObjectName("lineTotalLabel")

            layout.addWidget(product_label, 0, 0)
            layout.addWidget(product_input, 0, 1, 1, 3)

            layout.addWidget(quantity_label, 1, 0)
            layout.addWidget(quantity_input, 1, 1)

            layout.addWidget(unit_price_label, 1, 2)
            layout.addWidget(unit_price_input, 1, 3)

            layout.addWidget(discount_label, 2, 0)
            layout.addWidget(discount_input, 2, 1)

            layout.addWidget(line_total_label, 2, 2, 1, 2, alignment=Qt.AlignRight)

            layout.addWidget(note_label, 3, 0)
            layout.addWidget(note_input, 3, 1, 1, 3)

            layout.addWidget(remove_button, 4, 3, alignment=Qt.AlignRight)

            self.items_layout.addWidget(card)

        self.items_layout.addStretch()
        self.update_summary()

    def update_item_field(self, index, field_name, value):
        if index < 0 or index >= len(self.items):
            return

        self.items[index][field_name] = value
        self.update_summary()

    def update_summary(self):
        subtotal = 0.0
        discount = 0.0

        for item in self.items:
            subtotal += float(item.get("unit_price", 0.0)) * int(item.get("quantity", 0))
            discount += float(item.get("discount", 0.0))

        due = max(subtotal - discount, 0.0)
        self.summary_label.setText(
            f"Subtotal: £{subtotal:.2f}   |   Discount: £{discount:.2f}   |   Due: £{due:.2f}"
        )

    def handle_save(self):
        if not self.items:
            QMessageBox.warning(self, "No Items", "Please keep at least one item in the order.")
            return

        cleaned_items = []

        for item in self.items:
            product_name = str(item.get("product_name", "")).strip()
            unit_price = float(item.get("unit_price", 0.0))
            quantity = int(item.get("quantity", 0))
            note = str(item.get("note", "")).strip()
            discount = float(item.get("discount", 0.0))

            if not product_name:
                QMessageBox.warning(self, "Missing Product", "Every item must have a product name.")
                return

            if quantity <= 0:
                QMessageBox.warning(self, "Invalid Quantity", "Quantity must be at least 1.")
                return

            if unit_price < 0:
                QMessageBox.warning(self, "Invalid Price", "Unit price cannot be negative.")
                return

            if discount < 0:
                QMessageBox.warning(self, "Invalid Discount", "Discount cannot be negative.")
                return

            cleaned_items.append({
                "product_name": product_name,
                "unit_price": round(unit_price, 2),
                "quantity": quantity,
                "note": note,
                "discount": round(discount, 2),
            })

        try:
            update_order(
                order_id=self.order["id"],
                customer_name=self.customer_name_input.text().strip(),
                customer_phone=self.customer_phone_input.text().strip(),
                cart_items=cleaned_items,
            )
        except Exception as error:
            QMessageBox.critical(self, "Save Failed", f"Could not update order.\n\n{error}")
            return

        QMessageBox.information(self, "Saved", "Order updated successfully.")
        self.accept()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f6f8fc;
            }

            QLabel#dialogTitle {
                color: #24324a;
                font-size: 22px;
                font-weight: 700;
            }

            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e3eaf3;
                border-radius: 12px;
            }

            QLabel#fieldLabel {
                color: #617084;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#summaryLabel {
                color: #2f7cec;
                font-size: 15px;
                font-weight: 700;
                padding: 4px 2px;
            }

            QLabel#lineTotalLabel {
                color: #24324a;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#emptyLabel {
                color: #7c8798;
                background-color: #ffffff;
                border: 1px dashed #d9e2ee;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
            }

            QLineEdit#fieldInput,
            QSpinBox,
            QDoubleSpinBox,
            QTextEdit#noteInput {
                background-color: #f8fbff;
                border: 1px solid #dbe5f0;
                border-radius: 10px;
                padding: 10px 12px;
                color: #24324a;
                font-size: 13px;
            }

            QPushButton#primaryButton {
                background-color: #2f7cec;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#primaryButton:hover {
                background-color: #236dd4;
            }

            QPushButton#secondaryButton {
                background-color: #eef3f9;
                color: #425066;
                border: 1px solid #dbe5f0;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#dangerButton {
                background-color: #db5065;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#dangerButton:hover {
                background-color: #c84357;
            }
        """)


class OrdersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Orders")
        self.setModal(True)
        self.resize(980, 760)

        self.setup_ui()
        self.load_orders()
        self.apply_styles()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        self.setLayout(main_layout)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(12)

        title_label = QLabel("Saved Orders")
        title_label.setObjectName("dialogTitle")

        title_row.addWidget(title_label)
        title_row.addStretch()

        report_button = QPushButton("End of Day Report")
        report_button.setObjectName("reportButton")
        report_button.clicked.connect(self.open_end_of_day_report)
        title_row.addWidget(report_button)

        main_layout.addLayout(title_row)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Search by order number or date...")
        self.search_input.returnPressed.connect(self.handle_search)

        search_button = QPushButton("Search")
        search_button.setObjectName("searchButton")
        search_button.clicked.connect(self.handle_search)

        clear_button = QPushButton("Clear")
        clear_button.setObjectName("clearButton")
        clear_button.clicked.connect(self.handle_clear_search)

        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(search_button)
        search_row.addWidget(clear_button)

        main_layout.addLayout(search_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.scroll_content = QWidget()
        self.orders_layout = QVBoxLayout()
        self.orders_layout.setContentsMargins(0, 0, 0, 0)
        self.orders_layout.setSpacing(12)
        self.scroll_content.setLayout(self.orders_layout)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

    def open_end_of_day_report(self):
        dialog = EndOfDayReportDialog(parent=self)
        dialog.exec()

    def clear_orders(self):
        while self.orders_layout.count():
            item = self.orders_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def load_orders(self, orders=None):
        self.clear_orders()

        if orders is None:
            orders = get_all_orders()

        if not orders:
            empty_label = QLabel("No matching orders found.")
            empty_label.setObjectName("emptyLabel")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setMinimumHeight(160)
            self.orders_layout.addWidget(empty_label)
            return

        for order in orders:
            card = self.create_order_card(order)
            self.orders_layout.addWidget(card)

        self.orders_layout.addStretch()

    def handle_search(self):
        search_text = self.search_input.text().strip()
        results = search_orders(search_text)
        self.load_orders(results)

    def handle_clear_search(self):
        self.search_input.clear()
        self.load_orders()

    def create_order_card(self, order):
        card = QWidget()
        card.setObjectName("orderCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        card.setLayout(layout)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        order_number_label = QLabel(order["order_number"])
        order_number_label.setObjectName("orderNumberLabel")

        created_at_text = order["created_at"]
        try:
            created_at_dt = datetime.fromisoformat(created_at_text)
            created_at_text = created_at_dt.strftime("%d %b %Y %H:%M")
        except Exception:
            pass

        date_label = QLabel(created_at_text)
        date_label.setObjectName("metaLabel")

        top_row.addWidget(order_number_label)
        top_row.addStretch()
        top_row.addWidget(date_label)

        customer_name = order.get("customer_name") or "No customer name"
        customer_phone = order.get("customer_phone") or "No phone number"

        customer_label = QLabel(f"Customer: {customer_name}")
        customer_label.setObjectName("infoLabel")

        phone_label = QLabel(f"Phone: {customer_phone}")
        phone_label.setObjectName("infoLabel")

        totals_label = QLabel(
            f"Subtotal: £{order['subtotal']:.2f}   |   "
            f"Discount: £{order['total_discount']:.2f}   |   "
            f"Due: £{order['total_due']:.2f}"
        )
        totals_label.setObjectName("totalsLabel")

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)

        view_receipt_button = QPushButton("View Receipt")
        view_receipt_button.setObjectName("viewButton")
        view_receipt_button.clicked.connect(lambda: self.handle_view_receipt(order["id"]))

        edit_button = QPushButton("Edit")
        edit_button.setObjectName("editButton")
        edit_button.clicked.connect(lambda: self.handle_edit_order(order["id"]))

        delete_button = QPushButton("Delete")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(lambda: self.handle_delete_order(order["id"], order["order_number"]))

        button_row.addStretch()
        button_row.addWidget(view_receipt_button)
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)

        layout.addLayout(top_row)
        layout.addWidget(customer_label)
        layout.addWidget(phone_label)
        layout.addWidget(totals_label)
        layout.addLayout(button_row)

        return card

    def build_receipt_preview(self, order_id):
        order = get_order_by_id(order_id)
        items = get_order_items(order_id)

        if not order or not items:
            QMessageBox.warning(self, "Missing Data", "Could not load this order or its items.")
            return None

        preview = ReceiptPreviewDialog(
            order_number=order["order_number"],
            cart_items=items,
            customer_name=order.get("customer_name", ""),
            customer_phone=order.get("customer_phone", ""),
            created_at_text=order.get("created_at"),
            include_vat_number=bool(order.get("include_vat_number", 0)),
            vat_number=order.get("vat_number", ""),
            vat_amount=float(order.get("vat_amount", 0.0)),
            parent=self,
        )
        return preview

    def handle_view_receipt(self, order_id):
        preview = self.build_receipt_preview(order_id)
        if preview is not None:
            preview.exec()

    def handle_edit_order(self, order_id):
        order = get_order_by_id(order_id)
        items = get_order_items(order_id)

        if not order:
            QMessageBox.warning(self, "Missing Order", "Could not load this order.")
            return

        dialog = EditOrderDialog(order=order, items=items, parent=self)
        if dialog.exec():
            self.handle_search()

    def handle_delete_order(self, order_id, order_number):
        result = QMessageBox.question(
            self,
            "Delete Order",
            f"Are you sure you want to delete this order?\n\n{order_number}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if result != QMessageBox.Yes:
            return

        try:
            delete_order(order_id)
        except Exception as error:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete order.\n\n{error}")
            return

        QMessageBox.information(self, "Deleted", f"Order deleted:\n{order_number}")
        self.handle_search()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f6f8fc;
            }

            QLabel#dialogTitle {
                color: #24324a;
                font-size: 22px;
                font-weight: 700;
            }

            QLineEdit#searchInput {
                background-color: #ffffff;
                border: 1px solid #dbe5f0;
                border-radius: 10px;
                padding: 12px 14px;
                color: #24324a;
                font-size: 14px;
            }

            QPushButton#searchButton,
            QPushButton#clearButton,
            QPushButton#reportButton {
                border-radius: 10px;
                padding: 11px 14px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#searchButton,
            QPushButton#reportButton {
                background-color: #2f7cec;
                color: white;
                border: none;
            }

            QPushButton#searchButton:hover,
            QPushButton#reportButton:hover {
                background-color: #236dd4;
            }

            QPushButton#clearButton {
                background-color: #eef3f9;
                color: #425066;
                border: 1px solid #dbe5f0;
            }

            QLabel#emptyLabel {
                color: #7c8798;
                background-color: #ffffff;
                border: 1px dashed #d9e2ee;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
            }

            QWidget#orderCard {
                background-color: #ffffff;
                border: 1px solid #e3eaf3;
                border-radius: 12px;
            }

            QLabel#orderNumberLabel {
                color: #24324a;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#metaLabel {
                color: #7b8797;
                font-size: 12px;
                font-weight: 600;
            }

            QLabel#infoLabel {
                color: #425066;
                font-size: 13px;
                font-weight: 600;
            }

            QLabel#totalsLabel {
                color: #2f7cec;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#viewButton,
            QPushButton#editButton,
            QPushButton#deleteButton {
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#viewButton {
                background-color: #2f7cec;
            }

            QPushButton#viewButton:hover {
                background-color: #236dd4;
            }

            QPushButton#editButton {
                background-color: #f0a63b;
            }

            QPushButton#editButton:hover {
                background-color: #de9528;
            }

            QPushButton#deleteButton {
                background-color: #db5065;
            }

            QPushButton#deleteButton:hover {
                background-color: #c84357;
            }
        """)