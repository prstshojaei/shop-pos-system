import html
import os
import time
import subprocess
from collections import defaultdict
from datetime import datetime

from PySide6.QtCore import QSizeF, QMarginsF, QTimer, QEventLoop, QUrl
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QSizePolicy,
    QMessageBox,
)
from PySide6.QtPrintSupport import QPrinter

try:
    from PySide6.QtWebEngineCore import QWebEnginePage
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

from app_paths import RECEIPTS_DIR
from data.menu_data import PRODUCTS_BY_CATEGORY
from database import get_all_orders, get_order_items


SHOP_NAME = "Electron x hub"
DEVICE_NAME = "Till 1 Northampton"
STAFF_NAME = "fayaz"

SUMATRA_EXE = r"C:\Users\ahmad\AppData\Local\SumatraPDF\SumatraPDF.exe"
PRINTER_NAME = "POSPrinter POS80"

# -----------------------------
# IMPORTANT PRINT SETTINGS
# -----------------------------
# برای رول 80mm خیلی از چاپگرها printable width واقعی‌شان نزدیک 72mm است
# پس PDF را با 72mm می‌سازیم که دیگر Sumatra مجبور به کوچک‌کردن نشود
PAPER_WIDTH_MM = 72.0

# عرض محتوای HTML - باید تقریباً تمام عرض رول را پر کند
RW = 270

PAD = 16
BROWSER_W = RW + PAD * 2 + 40

W_NAME = 142
W_QTY = 24
W_TAX = 44
W_TOTAL = 60


def _today_date():
    return datetime.now().date()


def _safe_dt(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _fmt_money(value):
    return f"&pound;{float(value):.2f}"


def _fmt_dt(dt_obj):
    if not dt_obj:
        return "-"
    return dt_obj.strftime("%d/%m/%y %H:%M")


def _hr():
    return (
        f'<table width="{RW}" cellspacing="0" cellpadding="0" border="0" '
        f'style="border-collapse:collapse;">'
        f'<tr><td height="1" style="border-top:1px solid #888;font-size:1px;line-height:1px;">&nbsp;</td></tr>'
        f'</table>'
        f'<p style="margin:2px 0;font-size:1px;line-height:1px;">&nbsp;</p>'
    )


def _build_product_category_lookup():
    lookup = {}
    for category_name, products in PRODUCTS_BY_CATEGORY.items():
        for product_name in products:
            lookup[product_name.strip().upper()] = category_name
    return lookup


def build_end_of_day_data(target_date=None):
    if target_date is None:
        target_date = _today_date()

    product_to_category = _build_product_category_lookup()
    all_orders = get_all_orders()

    day_orders = []
    for order in all_orders:
        dt = _safe_dt(order.get("created_at", ""))
        if dt and dt.date() == target_date:
            day_orders.append(order)

    total_orders = len(day_orders)
    total_items_qty = 0
    total_subtotal = 0.0
    total_discount = 0.0
    total_vat = 0.0
    total_due = 0.0

    sales_by_product = defaultdict(lambda: {"qty": 0, "net": 0.0, "tax": 0.0, "total": 0.0})
    sales_by_category = defaultdict(lambda: {"qty": 0, "net": 0.0, "tax": 0.0, "total": 0.0})

    opened_at = None
    closed_at = None

    for order in day_orders:
        order_dt = _safe_dt(order.get("created_at", ""))
        if order_dt is not None:
            if opened_at is None or order_dt < opened_at:
                opened_at = order_dt
            if closed_at is None or order_dt > closed_at:
                closed_at = order_dt

        subtotal = float(order.get("subtotal", 0.0))
        discount = float(order.get("total_discount", 0.0))
        vat_amount = float(order.get("vat_amount", 0.0))
        due = float(order.get("total_due", 0.0))

        total_subtotal += subtotal
        total_discount += discount
        total_vat += vat_amount
        total_due += due

        items = get_order_items(order["id"])
        item_count_for_order = 0

        for item in items:
            product_name = str(item.get("product_name", "")).strip()
            quantity = int(item.get("quantity", 0))
            line_total = float(item.get("line_total", 0.0))
            item_count_for_order += quantity

            order_net = max(subtotal - discount, 0.0)
            order_total_with_vat = due if due > 0 else order_net
            tax_share_ratio = vat_amount / order_total_with_vat if order_total_with_vat > 0 else 0.0

            line_tax = round(line_total * tax_share_ratio, 2) if vat_amount > 0 else 0.0
            line_net = max(line_total - line_tax, 0.0)

            sales_by_product[product_name]["qty"] += quantity
            sales_by_product[product_name]["net"] += line_net
            sales_by_product[product_name]["tax"] += line_tax
            sales_by_product[product_name]["total"] += line_total

            category_name = product_to_category.get(product_name.upper(), "UNCATEGORISED")
            sales_by_category[category_name]["qty"] += quantity
            sales_by_category[category_name]["net"] += line_net
            sales_by_category[category_name]["tax"] += line_tax
            sales_by_category[category_name]["total"] += line_total

        total_items_qty += item_count_for_order

    return {
        "target_date": target_date,
        "orders": day_orders,
        "total_orders": total_orders,
        "total_items_qty": total_items_qty,
        "total_subtotal": round(total_subtotal, 2),
        "total_discount": round(total_discount, 2),
        "total_vat": round(total_vat, 2),
        "total_due": round(total_due, 2),
        "sales_by_product": dict(sales_by_product),
        "sales_by_category": dict(sales_by_category),
        "opened_at": opened_at,
        "closed_at": closed_at,
    }


def _summary_rows(data):
    return f"""
    <tr>
      <td width="170" style="padding:2px 0;">Transactions</td>
      <td width="100" align="right" style="padding:2px 0;white-space:nowrap;">{data['total_orders']}</td>
    </tr>
    <tr>
      <td width="170" style="padding:2px 0;">Items Sold</td>
      <td width="100" align="right" style="padding:2px 0;white-space:nowrap;">{data['total_items_qty']}</td>
    </tr>
    <tr>
      <td width="170" style="padding:2px 0;">Sub Total</td>
      <td width="100" align="right" style="padding:2px 0;white-space:nowrap;">{_fmt_money(data['total_subtotal'])}</td>
    </tr>
    <tr>
      <td width="170" style="padding:2px 0;">Discount</td>
      <td width="100" align="right" style="padding:2px 0;white-space:nowrap;">{_fmt_money(data['total_discount'])}</td>
    </tr>
    <tr>
      <td width="170" style="padding:2px 0;">VAT</td>
      <td width="100" align="right" style="padding:2px 0;white-space:nowrap;">{_fmt_money(data['total_vat'])}</td>
    </tr>
    <tr>
      <td width="170" style="padding-top:6px;font-weight:700;">Total Sales</td>
      <td width="100" align="right" style="padding-top:6px;font-weight:700;white-space:nowrap;">{_fmt_money(data['total_due'])}</td>
    </tr>
    """


def _product_rows(data):
    rows = []
    td = (
        "font-size:10px;vertical-align:top;padding-top:6px;padding-bottom:6px;"
        "border-bottom:1px dotted #aaa;"
    )

    items = sorted(
        data["sales_by_product"].items(),
        key=lambda x: (-x[1]["total"], x[0])
    )

    if not items:
        return f'<tr><td colspan="4" style="{td}text-align:center;">No product sales for this day</td></tr>'

    for product_name, values in items:
        rows.append(
            f'<tr>'
            f'<td width="{W_NAME}" style="{td}word-break:break-word;">{html.escape(product_name)}</td>'
            f'<td width="{W_QTY}" align="right" style="{td}white-space:nowrap;">{values["qty"]}</td>'
            f'<td width="{W_TAX}" align="right" style="{td}white-space:nowrap;">{_fmt_money(values["tax"])}</td>'
            f'<td width="{W_TOTAL}" align="right" style="{td}white-space:nowrap;">{_fmt_money(values["total"])}</td>'
            f'</tr>'
        )

    return "\n".join(rows)


def _category_rows(data):
    rows = []
    td = (
        "font-size:10px;vertical-align:top;padding-top:6px;padding-bottom:6px;"
        "border-bottom:1px dotted #aaa;"
    )

    items = sorted(
        data["sales_by_category"].items(),
        key=lambda x: (-x[1]["total"], x[0])
    )

    if not items:
        return f'<tr><td colspan="4" style="{td}text-align:center;">No category sales for this day</td></tr>'

    for category_name, values in items:
        rows.append(
            f'<tr>'
            f'<td width="{W_NAME}" style="{td}word-break:break-word;">{html.escape(category_name)}</td>'
            f'<td width="{W_QTY}" align="right" style="{td}white-space:nowrap;">{values["qty"]}</td>'
            f'<td width="{W_TAX}" align="right" style="{td}white-space:nowrap;">{_fmt_money(values["tax"])}</td>'
            f'<td width="{W_TOTAL}" align="right" style="{td}white-space:nowrap;">{_fmt_money(values["total"])}</td>'
            f'</tr>'
        )

    return "\n".join(rows)


def build_end_of_day_html(target_date=None):
    data = build_end_of_day_data(target_date)
    hr = _hr()

    report_date = data["target_date"].strftime("%d/%m/%Y")
    opened_text = _fmt_dt(data["opened_at"])
    closed_text = _fmt_dt(data["closed_at"])

    summary_rows = _summary_rows(data)
    product_rows = _product_rows(data)
    category_rows = _category_rows(data)

    th = "font-size:10px;font-weight:700;padding-bottom:6px;border-bottom:1px solid #666;"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{
    box-sizing: border-box;
  }}

  html, body {{
    margin: 0;
    padding: 0;
    background: white;
    color: #000;
    font-family: Arial, Helvetica, sans-serif;
  }}

  body {{
    width: 100%;
    font-size: 11px;
  }}

  .wrap {{
    width: {RW}px;
    margin: 0 auto;
    padding: 4px 0 10px 0;
  }}

  table {{
    border-collapse: collapse;
    table-layout: fixed;
  }}

  td, th {{
    overflow-wrap: break-word;
    word-wrap: break-word;
  }}
</style>
</head>
<body>
<div class="wrap">

  <p style="text-align:center;font-size:21px;font-weight:900;margin:0 0 6px 0;">
    End of Day Report
  </p>

  <p style="text-align:center;font-size:11px;line-height:1.35;margin:0 0 8px 0;">
    {html.escape(SHOP_NAME)}<br>
    {html.escape(DEVICE_NAME)}<br>
    Date: {report_date}
  </p>

  {hr}

  <table width="{RW}" cellspacing="0" cellpadding="0" style="font-size:11px;">
    <tr>
      <td width="118" style="padding:3px 0;">Till Name</td>
      <td width="152" align="right" style="padding:3px 0;">{html.escape(DEVICE_NAME)}</td>
    </tr>
    <tr>
      <td width="118" style="padding:3px 0;">Opened by</td>
      <td width="152" align="right" style="padding:3px 0;">{html.escape(STAFF_NAME)}</td>
    </tr>
    <tr>
      <td width="118" style="padding:3px 0;">Opened at</td>
      <td width="152" align="right" style="padding:3px 0;">{html.escape(opened_text)}</td>
    </tr>
    <tr>
      <td width="118" style="padding:3px 0;">Closed by</td>
      <td width="152" align="right" style="padding:3px 0;">{html.escape(STAFF_NAME)}</td>
    </tr>
    <tr>
      <td width="118" style="padding:3px 0;">Closed at</td>
      <td width="152" align="right" style="padding:3px 0;">{html.escape(closed_text)}</td>
    </tr>
  </table>

  {hr}

  <p style="font-size:13px;font-weight:800;margin:0 0 5px 0;">Sales Summary</p>
  <table width="{RW}" cellspacing="0" cellpadding="0" style="font-size:11px;">
    {summary_rows}
  </table>

  {hr}

  <p style="font-size:13px;font-weight:800;margin:0 0 5px 0;">Sales by Product</p>
  <table width="{RW}" cellspacing="0" cellpadding="0">
    <thead>
      <tr>
        <th width="{W_NAME}" align="left" style="{th}">PRODUCT</th>
        <th width="{W_QTY}" align="right" style="{th}">QTY</th>
        <th width="{W_TAX}" align="right" style="{th}">TAX</th>
        <th width="{W_TOTAL}" align="right" style="{th}">TOTAL</th>
      </tr>
    </thead>
    <tbody>
      {product_rows}
    </tbody>
  </table>

  {hr}

  <p style="font-size:13px;font-weight:800;margin:0 0 5px 0;">Sales by Category</p>
  <table width="{RW}" cellspacing="0" cellpadding="0">
    <thead>
      <tr>
        <th width="{W_NAME}" align="left" style="{th}">CATEGORY</th>
        <th width="{W_QTY}" align="right" style="{th}">QTY</th>
        <th width="{W_TAX}" align="right" style="{th}">TAX</th>
        <th width="{W_TOTAL}" align="right" style="{th}">TOTAL</th>
      </tr>
    </thead>
    <tbody>
      {category_rows}
    </tbody>
  </table>

  {hr}

  <p style="text-align:center;font-size:11px;font-weight:700;margin:6px 0 0 0;">
    End of day report generated successfully
  </p>

</div>
</body>
</html>"""


class EndOfDayReportDialog(QDialog):
    def __init__(self, target_date=None, parent=None):
        super().__init__(parent)

        self.target_date = target_date or _today_date()
        self.report_html = build_end_of_day_html(self.target_date)
        self.report_name = f"end_of_day_{self.target_date.strftime('%Y%m%d')}"

        self.setWindowTitle("End of Day Report")
        self.resize(500, 780)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        self.browser.setOpenExternalLinks(False)
        self.browser.setHtml(self.report_html)
        self.browser.setFixedWidth(BROWSER_W)
        self.browser.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        browser_row = QHBoxLayout()
        browser_row.addStretch()
        browser_row.addWidget(self.browser)
        browser_row.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.save_pdf_button = QPushButton("Save PDF")
        self.save_pdf_button.clicked.connect(self._on_save_pdf)

        self.print_button = QPushButton("Print")
        self.print_button.clicked.connect(self.handle_print)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        button_row.addWidget(self.save_pdf_button)
        button_row.addWidget(self.print_button)
        button_row.addWidget(self.close_button)

        layout.addLayout(browser_row, 1)
        layout.addLayout(button_row, 0)

    def save_as_pdf(self):
        pdf_path = RECEIPTS_DIR / f"{self.report_name}.pdf"

        if HAS_WEBENGINE:
            self._save_pdf_webengine(str(pdf_path))
        else:
            self._save_pdf_textdoc(str(pdf_path))

        return pdf_path

    def _save_pdf_webengine(self, output_path: str):
        loop = QEventLoop()

        page = QWebEnginePage()
        page.setHtml(self.report_html, QUrl("file:///"))

        def on_load_finished(ok):
            if not ok:
                loop.quit()
                return
            page.runJavaScript(
                "document.documentElement.scrollHeight",
                lambda h: _do_print(h)
            )

        def _do_print(height_px):
            height_mm = max(float(height_px or 400) * 0.2646 + 4, 50)
            layout = QPageLayout(
                QPageSize(QSizeF(PAPER_WIDTH_MM, height_mm), QPageSize.Unit.Millimeter),
                QPageLayout.Orientation.Portrait,
                QMarginsF(0, 0, 0, 0),
                QPageLayout.Unit.Millimeter,
            )
            page.printToPdf(output_path, layout)
            QTimer.singleShot(900, loop.quit)

        page.loadFinished.connect(on_load_finished)
        loop.exec()

    def _save_pdf_textdoc(self, output_path: str):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(output_path)

        margins = QMarginsF(0, 0, 0, 0)

        size1 = QPageSize(QSizeF(PAPER_WIDTH_MM, 600), QPageSize.Unit.Millimeter, "T80")
        printer.setPageLayout(
            QPageLayout(
                size1,
                QPageLayout.Orientation.Portrait,
                margins,
                QPageLayout.Unit.Millimeter,
            )
        )

        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setHtml(self.report_html)
        doc.setTextWidth(printer.pageRect(QPrinter.Unit.Point).width())

        content_mm = (doc.size().height() / 72.0) * 25.4 + 4
        size2 = QPageSize(QSizeF(PAPER_WIDTH_MM, content_mm), QPageSize.Unit.Millimeter, "T80f")
        printer.setPageLayout(
            QPageLayout(
                size2,
                QPageLayout.Orientation.Portrait,
                margins,
                QPageLayout.Unit.Millimeter,
            )
        )
        doc.setTextWidth(printer.pageRect(QPrinter.Unit.Point).width())
        doc.print_(printer)

    def _on_save_pdf(self):
        try:
            path = self.save_as_pdf()
            QMessageBox.information(self, "PDF Saved", f"Report saved:\n{path}")
        except Exception as error:
            QMessageBox.critical(self, "PDF Error", f"Could not save report PDF.\n\n{error}")

    def handle_print(self):
        try:
            pdf_path = self.save_as_pdf()

            for _ in range(50):
                if pdf_path.exists() and pdf_path.stat().st_size > 500:
                    break
                time.sleep(0.1)

            if not pdf_path.exists() or pdf_path.stat().st_size < 100:
                raise FileNotFoundError("PDF file was not created properly.")

            if os.name != "nt":
                raise RuntimeError("Print is only supported on Windows.")

            if not os.path.exists(SUMATRA_EXE):
                raise FileNotFoundError(f"SumatraPDF not found at:\n{SUMATRA_EXE}")

            subprocess.Popen([
                SUMATRA_EXE,
                "-print-to", PRINTER_NAME,
                "-print-settings", "noscale,portrait",
                "-silent",
                str(pdf_path)
            ])

            QMessageBox.information(self, "Print Sent", "End of day report sent to printer successfully.")

        except Exception as error:
            QMessageBox.critical(self, "Print Error", f"Could not print the end of day report.\n\n{error}")

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f2f8;
            }
            QTextBrowser {
                background-color: white;
                border: 1px solid #dfe6ef;
                border-radius: 10px;
                padding: 6px;
            }
            QPushButton {
                background-color: #2f7cec;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 700;
                min-width: 88px;
            }
            QPushButton:hover {
                background-color: #236dd4;
            }
        """)