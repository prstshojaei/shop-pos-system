from functools import partial
from datetime import datetime
import win32print

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app_icon import get_app_icon
from database import save_order
from data.menu_data import CATEGORIES, PRODUCTS_BY_CATEGORY
from ui.discount_dialog import DiscountDialog
from ui.note_dialog import NoteDialog
from ui.orders_dialog import OrdersDialog
from ui.price_dialog import PriceDialog
from ui.receipt_printer import ReceiptPreviewDialog
from ui.vat_dialog import VatDialog

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.setWindowTitle("Shop POS")
        self.setMinimumSize(1500, 900)

        self.current_view = "home"
        self.current_category = None
        self.search_mode = False
        self.search_text = ""

        self.categories = CATEGORIES
        self.products_by_category = PRODUCTS_BY_CATEGORY

        self.cart_items = []

        self.include_vat_number = False
        self.vat_number = "GB123456789"
        self.vat_amount = 0.0

        self.setup_ui()
        self.setup_clock()
        self.show_home_view()
        self.refresh_order_panel()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(12)
        central_widget.setLayout(root_layout)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.left_panel.setLayout(left_layout)

        self.build_left_header(left_layout)
        self.build_category_area(left_layout)

        self.right_panel = QFrame()
        self.right_panel.setObjectName("rightPanel")
        self.right_panel.setFixedWidth(500)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.right_panel.setLayout(right_layout)

        self.build_right_header(right_layout)
        self.build_customer_section(right_layout)
        self.build_order_area(right_layout)
        self.build_summary_area(right_layout)
        self.build_action_buttons(right_layout)

        root_layout.addWidget(self.left_panel, 4)
        root_layout.addWidget(self.right_panel, 0)

        self.apply_styles()

    def setup_clock(self):
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_header_time)
        self.clock_timer.start(1000)
        self.update_header_time()

    def update_header_time(self):
        if ZoneInfo is not None:
            try:
                now_uk = datetime.now(ZoneInfo("Europe/London"))
            except Exception:
                now_uk = datetime.now()
        else:
            now_uk = datetime.now()

        formatted_time = now_uk.strftime("%d %b %H:%M")
        self.shop_info.setText(f"Till 1 | Northampton | {formatted_time}")

    def build_left_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setObjectName("leftHeader")
        header_frame.setFixedHeight(95)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(24, 18, 24, 18)
        header_layout.setSpacing(12)
        header_frame.setLayout(header_layout)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        shop_name = QLabel("fayaz")
        shop_name.setObjectName("shopName")

        self.shop_info = QLabel("Till 1 | Northampton | --")
        self.shop_info.setObjectName("shopInfo")

        title_layout.addWidget(shop_name)
        title_layout.addWidget(self.shop_info)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("headerSearchInput")
        self.search_input.setPlaceholderText("Search product...")
        self.search_input.setFixedWidth(240)
        self.search_input.returnPressed.connect(self.handle_search)
        self.search_input.hide()

        search_button = QPushButton("⌕")
        search_button.setObjectName("iconButton")
        search_button.setFixedSize(42, 42)
        search_button.clicked.connect(self.toggle_search)

        home_button = QPushButton("⌂")
        home_button.setObjectName("iconButton")
        home_button.setFixedSize(42, 42)
        home_button.clicked.connect(self.show_home_view)

        header_layout.addWidget(self.search_input)
        header_layout.addWidget(search_button)
        header_layout.addWidget(home_button)

        parent_layout.addWidget(header_frame)

    def build_category_area(self, parent_layout):
        content_frame = QFrame()
        content_frame.setObjectName("leftContent")

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(22, 20, 22, 22)
        content_layout.setSpacing(14)
        content_frame.setLayout(content_layout)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(12)

        self.section_title = QLabel("HOME")
        self.section_title.setObjectName("leftSectionTitle")

        self.back_button = QPushButton("‹ BACK")
        self.back_button.setObjectName("backButton")
        self.back_button.setFixedHeight(34)
        self.back_button.clicked.connect(self.show_home_view)
        self.back_button.hide()

        top_bar_layout.addWidget(self.section_title)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.back_button)

        content_layout.addLayout(top_bar_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("categoryScroll")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContentWidget")
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(14)
        self.grid_layout.setVerticalSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_content.setLayout(self.grid_layout)

        self.scroll_area.setWidget(self.scroll_content)
        content_layout.addWidget(self.scroll_area)

        parent_layout.addWidget(content_frame)

    def build_right_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setObjectName("rightHeader")
        header_frame.setFixedHeight(86)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_frame.setLayout(header_layout)

        products_tab = QPushButton("PRODUCTS")
        products_tab.setObjectName("topTab")
        products_tab.setProperty("active", True)

        orders_tab = QPushButton("ORDERS")
        orders_tab.setObjectName("topTab")
        orders_tab.clicked.connect(self.open_orders_dialog)

        for button in (products_tab, orders_tab):
            button.setCursor(Qt.PointingHandCursor)
            header_layout.addWidget(button)

        parent_layout.addWidget(header_frame)

    def build_customer_section(self, parent_layout):
        customer_frame = QFrame()
        customer_frame.setObjectName("customerFrame")

        customer_layout = QVBoxLayout()
        customer_layout.setContentsMargins(18, 14, 18, 14)
        customer_layout.setSpacing(10)
        customer_frame.setLayout(customer_layout)

        title_label = QLabel("CUSTOMER")
        title_label.setObjectName("customerSectionTitle")

        self.customer_name_input = QLineEdit()
        self.customer_name_input.setObjectName("customerInput")
        self.customer_name_input.setPlaceholderText("Customer name")

        self.customer_phone_input = QLineEdit()
        self.customer_phone_input.setObjectName("customerInput")
        self.customer_phone_input.setPlaceholderText("Phone number")

        customer_layout.addWidget(title_label)
        customer_layout.addWidget(self.customer_name_input)
        customer_layout.addWidget(self.customer_phone_input)

        parent_layout.addWidget(customer_frame)

    def build_order_area(self, parent_layout):
        self.order_frame = QFrame()
        self.order_frame.setObjectName("orderFrame")
        self.order_frame.setFixedHeight(360)

        order_layout = QVBoxLayout()
        order_layout.setContentsMargins(18, 16, 18, 16)
        order_layout.setSpacing(10)
        self.order_frame.setLayout(order_layout)

        header_row = QFrame()
        header_row.setObjectName("orderTableHeader")
        header_row_layout = QHBoxLayout()
        header_row_layout.setContentsMargins(12, 8, 12, 8)
        header_row_layout.setSpacing(8)
        header_row.setLayout(header_row_layout)

        product_header = QLabel("Product")
        qty_header = QLabel("Qty")
        each_header = QLabel("Each")
        total_header = QLabel("Total")

        product_header.setObjectName("tableHeaderLabel")
        qty_header.setObjectName("tableHeaderLabel")
        each_header.setObjectName("tableHeaderLabel")
        total_header.setObjectName("tableHeaderLabel")

        header_row_layout.addWidget(product_header, 4)
        header_row_layout.addWidget(qty_header, 1, alignment=Qt.AlignCenter)
        header_row_layout.addWidget(each_header, 2, alignment=Qt.AlignCenter)
        header_row_layout.addWidget(total_header, 2, alignment=Qt.AlignCenter)

        order_layout.addWidget(header_row)

        self.order_scroll_area = QScrollArea()
        self.order_scroll_area.setObjectName("orderItemsScroll")
        self.order_scroll_area.setWidgetResizable(True)
        self.order_scroll_area.setFrameShape(QFrame.NoFrame)
        self.order_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.order_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.order_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.order_items_container = QWidget()
        self.order_items_container.setObjectName("orderItemsContainer")
        self.order_items_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.order_items_layout = QVBoxLayout()
        self.order_items_layout.setContentsMargins(0, 0, 8, 14)
        self.order_items_layout.setSpacing(10)
        self.order_items_layout.setAlignment(Qt.AlignTop)
        self.order_items_container.setLayout(self.order_items_layout)

        self.order_scroll_area.setWidget(self.order_items_container)
        order_layout.addWidget(self.order_scroll_area)

        parent_layout.addWidget(self.order_frame)

    def build_summary_area(self, parent_layout):
        summary_frame = QFrame()
        summary_frame.setObjectName("summaryFrame")
        summary_frame.setFixedHeight(165)

        summary_layout = QHBoxLayout()
        summary_layout.setContentsMargins(18, 16, 18, 16)
        summary_layout.setSpacing(14)
        summary_frame.setLayout(summary_layout)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        items_label = QLabel("ITEMS")
        items_label.setObjectName("summaryLabelSmall")
        self.items_value_label = QLabel("0")
        self.items_value_label.setObjectName("summaryValueSmall")

        discount_label = QLabel("TOTAL DISCOUNT")
        discount_label.setObjectName("summaryLabelSmall")
        self.discount_value_label = QLabel("£0.00")
        self.discount_value_label.setObjectName("summaryValueSmall")

        left_col.addWidget(items_label)
        left_col.addWidget(self.items_value_label)
        left_col.addSpacing(8)
        left_col.addWidget(discount_label)
        left_col.addWidget(self.discount_value_label)
        left_col.addStretch()

        divider = QFrame()
        divider.setObjectName("summaryDivider")
        divider.setFixedWidth(1)

        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        total_row = QHBoxLayout()
        due_row = QHBoxLayout()
        tax_row = QHBoxLayout()

        total_label = QLabel("TOTAL")
        total_label.setObjectName("summaryLabel")
        self.total_value_label = QLabel("£0.00")
        self.total_value_label.setObjectName("summaryNumber")
        total_row.addWidget(total_label)
        total_row.addStretch()
        total_row.addWidget(self.total_value_label)

        due_label = QLabel("DUE")
        due_label.setObjectName("summaryLabel")
        self.due_value_label = QLabel("£0.00")
        self.due_value_label.setObjectName("summaryNumber")
        self.due_value_label.setProperty("highlight", True)
        due_row.addWidget(due_label)
        due_row.addStretch()
        due_row.addWidget(self.due_value_label)

        tax_label = QLabel("TAX")
        tax_label.setObjectName("summaryLabel")
        self.tax_value_label = QLabel("£0.00")
        self.tax_value_label.setObjectName("summaryNumber")
        tax_row.addWidget(tax_label)
        tax_row.addStretch()
        tax_row.addWidget(self.tax_value_label)

        right_col.addLayout(total_row)
        right_col.addLayout(due_row)
        right_col.addLayout(tax_row)
        right_col.addStretch()

        summary_layout.addLayout(left_col, 1)
        summary_layout.addWidget(divider)
        summary_layout.addLayout(right_col, 1)

        parent_layout.addWidget(summary_frame)

    def build_action_buttons(self, parent_layout):
        actions_frame = QFrame()
        actions_frame.setObjectName("actionsFrame")

        actions_layout = QGridLayout()
        actions_layout.setContentsMargins(18, 14, 18, 18)
        actions_layout.setHorizontalSpacing(12)
        actions_layout.setVerticalSpacing(12)
        actions_frame.setLayout(actions_layout)

        buttons = [
            ("⊕", "MISC PRODUCT", ""),
            ("🖨", "PRINT", "primary"),
            ("↯", "NO SALE", ""),
            ("#", "VAT NUMBER", "vat"),
            ("🏷", "QUICK ADD", ""),
            ("▣", "PETTY CASH", ""),
            ("↔", "ADJUST FLOAT", ""),
            ("", "CLEAR", "danger"),
        ]

        positions = [
            (0, 0), (0, 1), (0, 2), (0, 3),
            (1, 0), (1, 1), (1, 2), (1, 3),
        ]

        for (icon_text, label_text, style_type), (row, col) in zip(buttons, positions):
            button = QPushButton()
            button.setObjectName("actionButton")
            button.setMinimumSize(0, 92)
            button.setCursor(Qt.PointingHandCursor)

            if label_text == "CLEAR":
                button.setText("CLEAR")
            else:
                button.setText(f"{icon_text}\n{label_text}")

            if label_text == "CLEAR":
                button.clicked.connect(self.clear_cart)

            if label_text == "PRINT":
                button.clicked.connect(self.handle_print_order)
                
            if label_text == "NO SALE":
                button.clicked.connect(self.handle_no_sale)     

            if label_text == "VAT NUMBER":
                self.vat_toggle_button = button
                button.clicked.connect(self.open_vat_dialog)

            if style_type == "primary":
                button.setProperty("primary", True)

            if style_type == "danger":
                button.setProperty("danger", True)

            button.style().unpolish(button)
            button.style().polish(button)

            actions_layout.addWidget(button, row, col)

        for i in range(4):
            actions_layout.setColumnStretch(i, 1)

        self.update_vat_button_style()
        parent_layout.addWidget(actions_frame)

    def open_cash_drawer(self):
        printer_name = win32print.GetDefaultPrinter()

        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(hPrinter, 1, ("Open Drawer", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)

            # ESC/POS drawer kick command
            command = b'\x1b\x70\x00\x19\xfa'

            win32print.WritePrinter(hPrinter, command)

            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)

    def handle_no_sale(self):
        try:
            self.open_cash_drawer()
        except Exception as error:
            QMessageBox.warning(
                self,
                "Drawer Error",
                f"Could not open the cash drawer.\n\n{error}"
            )



    def open_vat_dialog(self):
        dialog = VatDialog(
            current_vat_number=self.vat_number,
            current_vat_amount=self.vat_amount,
            parent=self,
        )

        if dialog.exec():
            self.vat_number = dialog.get_vat_number()
            self.vat_amount = dialog.get_vat_amount()
            self.include_vat_number = bool(self.vat_number.strip() or self.vat_amount > 0)
            self.update_vat_button_style()
            self.refresh_order_panel()

    def update_vat_button_style(self):
        if hasattr(self, "vat_toggle_button"):
            self.vat_toggle_button.setProperty("activeVat", self.include_vat_number)
            self.vat_toggle_button.style().unpolish(self.vat_toggle_button)
            self.vat_toggle_button.style().polish(self.vat_toggle_button)

    def toggle_search(self):
        if self.search_input.isVisible():
            current_text = self.search_input.text().strip()

            if current_text:
                self.handle_search()
                return

            self.search_input.hide()
            self.search_input.clear()
            self.search_mode = False
            self.search_text = ""
            self.show_home_view()
        else:
            self.search_input.show()
            self.search_input.setFocus()

    def handle_search(self):
        text = self.search_input.text().strip()
        if not text:
            self.search_mode = False
            self.search_text = ""
            self.show_home_view()
            return

        self.search_mode = True
        self.search_text = text
        self.show_search_results(text)

    def show_search_results(self, search_text):
        self.current_view = "search"
        self.current_category = None

        self.section_title.setText(f"SEARCH: {search_text.upper()}")
        self.back_button.show()

        self.clear_grid()

        all_products = []
        for products in self.products_by_category.values():
            all_products.extend(products)

        filtered_products = []
        seen = set()

        for product_name in all_products:
            key = product_name.lower().strip()
            if search_text.lower() in key and key not in seen:
                filtered_products.append(product_name)
                seen.add(key)

        row = 0
        col = 0

        for product_name in filtered_products:
            tile = self.create_product_tile(product_name)
            self.grid_layout.addWidget(tile, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1

        if not filtered_products:
            no_results = QLabel("No matching products found")
            no_results.setObjectName("searchEmptyLabel")
            no_results.setAlignment(Qt.AlignCenter)
            no_results.setMinimumHeight(120)
            self.grid_layout.addWidget(no_results, 0, 0, 1, 4)

        for i in range(4):
            self.grid_layout.setColumnStretch(i, 1)

    def open_orders_dialog(self):
        dialog = OrdersDialog(self)
        dialog.exec()

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def clear_order_items_layout(self):
        while self.order_items_layout.count():
            item = self.order_items_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
    def scroll_order_to_bottom(self):
        scrollbar = self.order_scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())             

    def show_home_view(self):
        self.current_view = "home"
        self.current_category = None

        self.section_title.setText("HOME")
        self.back_button.hide()

        if self.search_input.isVisible() and not self.search_input.text().strip():
            self.search_input.hide()

        self.clear_grid()

        row = 0
        col = 0

        for category_name, tile_type in self.categories:
            tile = self.create_category_tile(category_name, tile_type)
            self.grid_layout.addWidget(tile, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1

        for i in range(4):
            self.grid_layout.setColumnStretch(i, 1)

    def show_products_view(self, category_name):
        self.current_view = "products"
        self.current_category = category_name

        self.section_title.setText(category_name)
        self.back_button.show()

        self.clear_grid()

        products = self.products_by_category.get(category_name, [])

        row = 0
        col = 0

        for product_name in products:
            tile = self.create_product_tile(product_name)
            self.grid_layout.addWidget(tile, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1

        for i in range(4):
            self.grid_layout.setColumnStretch(i, 1)

    def handle_category_click(self, category_name, tile_type):
        if tile_type == "light":
            return
        self.show_products_view(category_name)

    def handle_product_click(self, product_name):
        dialog = PriceDialog(product_name, self)

        if dialog.exec():
            selected_price = dialog.get_price()
            self.add_product_to_cart(product_name, selected_price)

    def handle_note_click(self, index):
        item = self.cart_items[index]
        dialog = NoteDialog(item["product_name"], item.get("note", ""), self)

        if dialog.exec():
            self.cart_items[index]["note"] = dialog.get_note()
            self.refresh_order_panel()

    def handle_discount_click(self, index):
        item = self.cart_items[index]
        dialog = DiscountDialog(item["product_name"], item.get("discount", 0.0), self)

        if dialog.exec():
            self.cart_items[index]["discount"] = dialog.get_discount()
            self.refresh_order_panel()

    def handle_print_order(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty Order", "Please add at least one item before saving.")
            return

        customer_name = self.customer_name_input.text().strip()
        customer_phone = self.customer_phone_input.text().strip()

        items_to_save = []
        for item in self.cart_items:
            items_to_save.append({
                "product_name": item["product_name"],
                "unit_price": item["unit_price"],
                "quantity": item["quantity"],
                "note": item.get("note", ""),
                "discount": item.get("discount", 0.0),
            })

        try:
            _, order_number = save_order(
                customer_name=customer_name,
                customer_phone=customer_phone,
                cart_items=items_to_save,
                include_vat_number=self.include_vat_number,
                vat_number=self.vat_number,
                vat_amount=self.vat_amount,
            )
        except Exception as error:
            QMessageBox.critical(self, "Save Failed", f"Could not save order.\n\n{error}")
            return

        try:
            preview = ReceiptPreviewDialog(
                order_number=order_number,
                cart_items=items_to_save,
                customer_name=customer_name,
                customer_phone=customer_phone,
                include_vat_number=self.include_vat_number,
                vat_number=self.vat_number,
                vat_amount=self.vat_amount,
                parent=self,
            )
        except Exception as error:
            QMessageBox.critical(self, "Receipt Error", f"Could not build receipt preview.\n\n{error}")
            return

        try:
            preview.save_as_pdf()
        except Exception as error:
            QMessageBox.warning(self, "PDF Warning", f"Receipt preview will open, but PDF backup failed.\n\n{error}")

        preview.exec()

        self.clear_cart()
        self.customer_name_input.clear()
        self.customer_phone_input.clear()

    def add_product_to_cart(self, product_name, price):
        for item in self.cart_items:
            if item["product_name"] == product_name and item["unit_price"] == price:
                item["quantity"] += 1
                self.refresh_order_panel()
                return

        self.cart_items.append({
            "product_name": product_name,
            "unit_price": price,
            "quantity": 1,
            "note": "",
            "discount": 0.0,
        })
        self.refresh_order_panel()

    def increase_quantity(self, index):
        self.cart_items[index]["quantity"] += 1
        self.refresh_order_panel()

    def decrease_quantity(self, index):
        self.cart_items[index]["quantity"] -= 1

        if self.cart_items[index]["quantity"] <= 0:
            self.cart_items.pop(index)

        self.refresh_order_panel()

    def remove_item(self, index):
        self.cart_items.pop(index)
        self.refresh_order_panel()

    def clear_cart(self):
        self.cart_items = []
        self.include_vat_number = False
        self.vat_amount = 0.0
        self.update_vat_button_style()
        self.refresh_order_panel()

    def refresh_order_panel(self):
        self.clear_order_items_layout()

        if self.cart_items:
            for index, item in enumerate(self.cart_items):
                item_card = self.create_order_item_card(index, item)
                self.order_items_layout.addWidget(item_card)

            # bottom spacing so the last item is fully visible
            self.order_items_layout.addSpacing(12)
            self.order_items_layout.addStretch()
        else:
            empty_label = QLabel("No items in order yet")
            empty_label.setObjectName("emptyOrderLabel")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setMinimumHeight(100)
            self.order_items_layout.addWidget(empty_label)
            self.order_items_layout.addStretch()

        total_items = sum(item["quantity"] for item in self.cart_items)
        total_discount = sum(item.get("discount", 0.0) for item in self.cart_items)

        subtotal_amount = sum(item["unit_price"] * item["quantity"] for item in self.cart_items)
        net_total = max(subtotal_amount - total_discount, 0.0)
        total_amount = net_total + (self.vat_amount if self.include_vat_number else 0.0)

        self.items_value_label.setText(str(total_items))
        self.discount_value_label.setText(f"£{total_discount:.2f}")
        self.total_value_label.setText(f"£{total_amount:.2f}")
        self.due_value_label.setText(f"£{total_amount:.2f}")
        self.tax_value_label.setText(
            f"£{self.vat_amount:.2f}" if self.include_vat_number else "£0.00"
        )

        self.due_value_label.style().unpolish(self.due_value_label)
        self.due_value_label.style().polish(self.due_value_label)

        # auto scroll to the newest item
        QTimer.singleShot(0, self.scroll_order_to_bottom)

    def create_order_item_card(self, index, item):
        item_card = QFrame()
        item_card.setObjectName("orderItemCard")

        item_layout = QVBoxLayout()
        item_layout.setContentsMargins(12, 10, 12, 10)
        item_layout.setSpacing(8)
        item_card.setLayout(item_layout)

        line_subtotal = item["unit_price"] * item["quantity"]
        line_discount = item.get("discount", 0.0)
        line_total = max(line_subtotal - line_discount, 0.0)

        item_top_row = QHBoxLayout()
        item_top_row.setContentsMargins(0, 0, 0, 0)
        item_top_row.setSpacing(8)

        name_layout = QVBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(4)

        item_name = QLabel(item["product_name"])
        item_name.setObjectName("itemName")
        item_name.setWordWrap(True)
        name_layout.addWidget(item_name)

        note_text = item.get("note", "").strip()
        if note_text:
            note_label = QLabel(note_text)
            note_label.setObjectName("itemNoteLabel")
            note_label.setWordWrap(True)
            name_layout.addWidget(note_label)

        if line_discount > 0:
            discount_label = QLabel(f"Discount: £{line_discount:.2f}")
            discount_label.setObjectName("itemDiscountLabel")
            name_layout.addWidget(discount_label)

        qty_value = QLabel(str(item["quantity"]))
        qty_value.setObjectName("itemValue")

        each_value = QLabel(f"£{item['unit_price']:.2f}")
        each_value.setObjectName("itemValue")

        total_value = QLabel(f"£{line_total:.2f}")
        total_value.setObjectName("itemValue")

        item_top_row.addLayout(name_layout, 4)
        item_top_row.addWidget(qty_value, 1, alignment=Qt.AlignCenter)
        item_top_row.addWidget(each_value, 2, alignment=Qt.AlignCenter)
        item_top_row.addWidget(total_value, 2, alignment=Qt.AlignCenter)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)

        note_button = QPushButton("NOTE")
        note_button.setObjectName("itemActionButton")
        note_button.clicked.connect(partial(self.handle_note_click, index))

        discount_button = QPushButton("DISCOUNT")
        discount_button.setObjectName("itemActionButton")
        discount_button.clicked.connect(partial(self.handle_discount_click, index))

        minus_button = QPushButton("−")
        minus_button.setObjectName("circleButton")
        minus_button.clicked.connect(partial(self.decrease_quantity, index))

        plus_button = QPushButton("+")
        plus_button.setObjectName("circleButton")
        plus_button.clicked.connect(partial(self.increase_quantity, index))

        delete_button = QPushButton("DELETE")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(partial(self.remove_item, index))

        for button in (note_button, discount_button, minus_button, plus_button, delete_button):
            button.setCursor(Qt.PointingHandCursor)

        action_row.addWidget(note_button)
        action_row.addWidget(discount_button)
        action_row.addStretch()
        action_row.addWidget(minus_button)
        action_row.addWidget(plus_button)
        action_row.addWidget(delete_button)

        item_layout.addLayout(item_top_row)
        item_layout.addLayout(action_row)

        return item_card

    def create_category_tile(self, title_text, tile_type="standard"):
        tile = QFrame()
        tile.setObjectName("categoryTileFrame")
        tile.setProperty("tileType", tile_type)
        tile.setMinimumSize(220, 120)
        tile.setMaximumHeight(120)

        tile_layout = QVBoxLayout()
        tile_layout.setContentsMargins(14, 12, 14, 12)
        tile_layout.setSpacing(6)
        tile.setLayout(tile_layout)

        display_text = title_text
        if title_text == "DESKTOP COMPUTERS":
            display_text = "DESKTOP\nCOMPUTERS"

        button = QPushButton(display_text)
        button.setObjectName("categoryTileButton")
        button.setProperty("tileType", tile_type)
        button.setCursor(Qt.PointingHandCursor)
        button.setFlat(True)
        button.clicked.connect(partial(self.handle_category_click, title_text, tile_type))

        if tile_type == "light":
            button.setProperty("alignTopLeft", True)

        button.style().unpolish(button)
        button.style().polish(button)

        tile_layout.addWidget(button)

        if tile_type == "light":
            price_label = QLabel("£0.00")
            price_label.setObjectName("tilePriceLabel")
            tile_layout.addStretch()
            tile_layout.addWidget(price_label, alignment=Qt.AlignLeft)

        return tile

    def create_product_tile(self, product_name):
        tile = QFrame()
        tile.setObjectName("productTileFrame")
        tile.setMinimumSize(220, 120)
        tile.setMaximumHeight(120)
        tile.setAutoFillBackground(True)

        tile_layout = QVBoxLayout()
        tile_layout.setContentsMargins(14, 12, 14, 12)
        tile_layout.setSpacing(4)
        tile.setLayout(tile_layout)

        product_button = QPushButton(product_name)
        product_button.setObjectName("productTileButton")
        product_button.setCursor(Qt.PointingHandCursor)
        product_button.setFlat(True)
        product_button.clicked.connect(partial(self.handle_product_click, product_name))

        price_label = QLabel("£0.00")
        price_label.setObjectName("productPriceLabel")

        tile_layout.addWidget(product_button, alignment=Qt.AlignTop)
        tile_layout.addStretch()
        tile_layout.addWidget(price_label, alignment=Qt.AlignLeft)

        return tile

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f1f4f9;
            }

            QFrame#leftPanel,
            QFrame#rightPanel {
                border-radius: 16px;
            }

            QFrame#leftPanel {
                background-color: #1d6fe0;
            }

            QFrame#rightPanel {
                background-color: #ffffff;
            }

            QFrame#leftHeader {
                background-color: #1a67d3;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }

            QFrame#leftContent {
                background-color: #1d6fe0;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }

            QWidget#scrollContentWidget {
                background-color: transparent;
            }

            QLabel#shopName {
                color: white;
                font-size: 26px;
                font-weight: 700;
            }

            QLabel#shopInfo {
                color: rgba(255, 255, 255, 0.85);
                font-size: 13px;
                font-weight: 500;
            }

            QLabel#leftSectionTitle {
                color: rgba(255, 255, 255, 0.92);
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            QLineEdit#headerSearchInput {
                background-color: rgba(255, 255, 255, 0.14);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 13px;
            }

            QLineEdit#headerSearchInput::placeholder {
                color: rgba(255, 255, 255, 0.72);
            }

            QPushButton#backButton {
                background-color: rgba(255, 255, 255, 0.14);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 14px;
            }

            QPushButton#backButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }

            QPushButton#iconButton {
                background-color: rgba(255, 255, 255, 0.12);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 700;
            }

            QPushButton#iconButton:hover {
                background-color: rgba(255, 255, 255, 0.20);
            }

            QPushButton#iconButton:pressed {
                background-color: rgba(255, 255, 255, 0.26);
            }

            QFrame#categoryTileFrame {
                border-radius: 8px;
            }

            QFrame#categoryTileFrame[tileType="standard"] {
                background-color: #8ec2ff;
            }

            QFrame#categoryTileFrame[tileType="selected"] {
                background-color: #1f2c3f;
            }

            QFrame#categoryTileFrame[tileType="warning"] {
                background-color: #cc5063;
            }

            QFrame#categoryTileFrame[tileType="light"] {
                background-color: #ffffff;
            }

            QPushButton#categoryTileButton {
                background-color: transparent;
                color: white;
                border: none;
                text-align: center;
                font-size: 18px;
                font-weight: 700;
                padding: 10px;
                line-height: 1.25em;
            }

            QPushButton#categoryTileButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }

            QPushButton#categoryTileButton:pressed {
                background-color: rgba(0, 0, 0, 0.06);
                border-radius: 6px;
            }

            QPushButton#categoryTileButton[tileType="light"] {
                color: #4a4f58;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 4px 2px;
            }

            QPushButton#categoryTileButton[alignTopLeft="true"] {
                text-align: left;
            }

            QLabel#tilePriceLabel {
                color: #6a707b;
                font-size: 15px;
                font-weight: 600;
                padding-left: 2px;
                padding-bottom: 2px;
            }

            QFrame#productTileFrame {
                background-color: rgb(255, 255, 255);
                border-radius: 6px;
                border: none;
            }

            QPushButton#productTileButton {
                background-color: transparent;
                color: #5a5f69;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 600;
                padding: 2px 2px;
            }

            QPushButton#productTileButton:hover {
                background-color: rgba(0, 0, 0, 0.02);
                border-radius: 4px;
            }

            QLabel#productPriceLabel {
                background-color: transparent;
                color: #666d78;
                font-size: 14px;
                font-weight: 600;
                padding-left: 2px;
                padding-bottom: 2px;
            }

            QLabel#searchEmptyLabel {
                color: rgba(255, 255, 255, 0.92);
                font-size: 18px;
                font-weight: 700;
                padding: 30px;
            }

            QFrame#rightHeader {
                background-color: #fbfcff;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid #e6ebf2;
            }

            QPushButton#topTab {
                background-color: transparent;
                color: #8b97a8;
                border: none;
                font-size: 15px;
                font-weight: 700;
                padding: 20px 10px;
            }

            QPushButton#topTab[active="true"] {
                color: #2a6fdf;
                background-color: white;
            }

            QPushButton#topTab:hover {
                background-color: #f5f8fd;
            }

            QFrame#customerFrame {
                background-color: #ffffff;
                border-bottom: 1px solid #edf1f7;
            }

            QLabel#customerSectionTitle {
                color: #8893a3;
                font-size: 12px;
                font-weight: 700;
            }

            QLineEdit#customerInput {
                background-color: #f8fbff;
                border: 1px solid #dbe5f0;
                border-radius: 10px;
                padding: 10px 12px;
                color: #24324a;
                font-size: 14px;
            }

            QLineEdit#customerInput:focus {
                background-color: #ffffff;
                border: 1px solid #2f7cec;
            }

            QFrame#orderFrame {
                background-color: white;
            }

            QFrame#orderTableHeader {
                background-color: white;
                border-bottom: 1px solid #e7edf5;
            }

            QLabel#tableHeaderLabel {
                color: #7a8596;
                font-size: 13px;
                font-weight: 700;
            }

            QScrollArea#orderItemsScroll {
                background: white;
                border: none;
            }

            QWidget#orderItemsContainer {
                background: white;
            }

            QScrollArea#orderItemsScroll QScrollBar:vertical {
                background: #eef3f9;
                width: 10px;
                margin: 2px 2px 2px 2px;
                border-radius: 5px;
            }

            QScrollArea#orderItemsScroll QScrollBar::handle:vertical {
                background: #8ea3bf;
                min-height: 40px;
                border-radius: 5px;
            }

            QScrollArea#orderItemsScroll QScrollBar::handle:vertical:hover {
                background: #6f88aa;
            }

            QScrollArea#orderItemsScroll QScrollBar::handle:vertical:pressed {
                background: #5d7698;
            }

            QScrollArea#orderItemsScroll QScrollBar::add-line:vertical,
            QScrollArea#orderItemsScroll QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }

            QScrollArea#orderItemsScroll QScrollBar::add-page:vertical,
            QScrollArea#orderItemsScroll QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QLabel#emptyOrderLabel {
                color: #7c8798;
                font-size: 14px;
                font-weight: 600;
                padding: 16px;
            }

            QFrame#orderItemCard {
                background-color: #3c82eb;
                border-radius: 12px;
            }

            QLabel#itemName,
            QLabel#itemValue {
                color: white;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#itemNoteLabel {
                color: rgba(255, 255, 255, 0.88);
                font-size: 12px;
                font-weight: 500;
            }

            QLabel#itemDiscountLabel {
                color: rgba(255, 255, 255, 0.92);
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton#itemActionButton {
                background-color: rgba(255, 255, 255, 0.14);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                padding: 10px 14px;
            }

            QPushButton#itemActionButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }

            QPushButton#circleButton {
                background-color: rgba(255, 255, 255, 0.12);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.50);
                border-radius: 22px;
                font-size: 18px;
                font-weight: 700;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
            }

            QPushButton#circleButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }

            QPushButton#deleteButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 12px;
                font-weight: 700;
                padding: 10px 10px;
            }

            QPushButton#deleteButton:hover {
                color: #e6efff;
            }

            QFrame#summaryFrame {
                background-color: white;
                border-top: 1px solid #edf1f7;
                border-bottom: 1px solid #edf1f7;
            }

            QFrame#summaryDivider {
                background-color: #e7edf5;
            }

            QLabel#summaryLabelSmall {
                color: #97a1af;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#summaryValueSmall {
                color: #2a3442;
                font-size: 24px;
                font-weight: 700;
            }

            QLabel#summaryLabel {
                color: #8893a3;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#summaryNumber {
                color: #2a3442;
                font-size: 18px;
                font-weight: 700;
            }

            QLabel#summaryNumber[highlight="true"] {
                color: #d34a5f;
            }

            QFrame#actionsFrame {
                background-color: white;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }

            QPushButton#actionButton {
                background-color: #ffffff;
                color: #5b6573;
                border: 1px solid #dde5ef;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 800;
                padding: 10px 8px;
                text-align: center;
                line-height: 1.25em;
            }

            QPushButton#actionButton:hover {
                background-color: #f4f8fd;
            }

            QPushButton#actionButton:pressed {
                background-color: #e9f0f8;
            }

            QPushButton#actionButton[primary="true"] {
                background-color: #2f7cec;
                color: white;
                border: none;
            }

            QPushButton#actionButton[primary="true"]:hover {
                background-color: #236dd4;
            }

            QPushButton#actionButton[danger="true"] {
                background-color: #db5065;
                color: white;
                border: none;
                font-size: 16px;
                font-weight: 800;
            }

            QPushButton#actionButton[danger="true"]:hover {
                background-color: #c84357;
            }

            QPushButton#actionButton[activeVat="true"] {
                background-color: #14a44d;
                color: white;
                border: none;
            }

            QPushButton#actionButton[activeVat="true"]:hover {
                background-color: #119142;
            }

            QScrollArea#categoryScroll {
                background: transparent;
                border: none;
            }

            QScrollArea#categoryScroll > QWidget > QWidget {
                background: transparent;
            }
        """)