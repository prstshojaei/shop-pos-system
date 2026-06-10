import html
import os
import time
import subprocess
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

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from app_paths import ASSETS_DIR, RECEIPTS_DIR


LOGO_CANDIDATES = [
    ASSETS_DIR / "logo.png",
    ASSETS_DIR / "logo.jpg",
    ASSETS_DIR / "logo.jpeg",
    ASSETS_DIR / "logo.webp",
    ASSETS_DIR / "logo1.png",
    ASSETS_DIR / "logo1.jpg",
    ASSETS_DIR / "logo1.jpeg",
    ASSETS_DIR / "logo1.webp",
]

SHOP_NAME = "Electron x hub"
SHOP_PHONE = "01604 639255"
SHOP_EMAIL = "Kkkan01@hotmail.com"
SHOP_ADDRESS_LINES = [
    "75 Abington Street",
    "Northampton",
    "West Northamptonshire",
    "NN1 2BH",
]

STAFF_NAME = "fayaz"
DEVICE_NAME = "Till 1 Northampton"

THANK_YOU_TEXT = "Thanks for visiting ElectronX Hub!"

POLICY_LINES = [
    "We buy:",
    "phones, computers, tablets, consoles, games, accessories.",
    "",
    "*POLICY*",
    "12 month warranty on: phone, tablet, iPad EXEMPT physically or liquid damage.",
    "28 days warranty for all other goods. If the item becomes faulty in course of normal use:",
    "1. we do not have refund policy.",
    "2. we repair the item.",
    "3. we need 3 to 7 days to solve the problem of the item.",
    "We do not offer warranty on vapes as all our vapes are brand new.",
    "The deposit is NOT refundable.",
]

RW = 250
PAD = 20
BROWSER_W = RW + PAD * 2 + 40

W_PRODUCT = 126
W_PRICE = 52
W_QTY = 26
W_TOTAL = 66

SUMATRA_EXE = r"C:\Users\ahmad\AppData\Local\SumatraPDF\SumatraPDF.exe"
PRINTER_NAME = "POSPrinter POS80"


def get_receipt_datetime():
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("Europe/London"))
        except Exception:
            return datetime.now()
    return datetime.now()


def find_logo_path():
    for path in LOGO_CANDIDATES:
        if path.exists():
            return path
    return None


def get_logo_html():
    logo_path = find_logo_path()
    box = 'style="display:inline-block;border:1px solid #666;padding:7px 10px;"'
    wrap = '<div style="text-align:center;margin-bottom:12px;"><div {box}>{inner}</div></div>'

    if logo_path is None:
        inner = '<span style="font-size:16px;font-weight:800;letter-spacing:1px;">ELECTRON HUB</span>'
    else:
        try:
            logo_uri = logo_path.resolve().as_uri()
            inner = f'<img src="{logo_uri}" width="190">'
        except Exception:
            inner = '<span style="font-size:16px;font-weight:800;letter-spacing:1px;">ELECTRON HUB</span>'

    return wrap.format(box=box, inner=inner)


def build_policy_html():
    return "<br>".join(html.escape(line) for line in POLICY_LINES)


def _hr():
    return (
        f'<table width="{RW}" cellspacing="0" cellpadding="0" border="0">'
        f'<tr><td height="1" style="border-top:1px solid #888;font-size:1px;line-height:1px;">&nbsp;</td></tr>'
        f'</table>'
        f'<p style="margin:3px 0;font-size:1px;line-height:1px;">&nbsp;</p>'
    )


def build_item_rows(cart_items):
    rows = []
    td = "font-size:11px;vertical-align:top;padding-top:8px;padding-bottom:8px;border-bottom:1px dotted #aaa;"

    for item in cart_items:
        product_name = html.escape(str(item.get("product_name", "")))
        unit_price = float(item.get("unit_price", 0.0))
        quantity = int(item.get("quantity", 0))
        discount = float(item.get("discount", 0.0))
        note = html.escape(str(item.get("note", "")).strip())
        line_total = max(unit_price * quantity - discount, 0.0)

        product_cell = f'<b style="font-size:11px;">{product_name}</b>'
        if note:
            product_cell += f'<br><span style="font-size:10px;">&quot;{note}&quot;</span>'
        if discount > 0:
            product_cell += f'<br><span style="font-size:10px;">Discount &pound;{discount:.2f}</span>'

        rows.append(
            f'<tr>'
            f'<td width="{W_PRODUCT}" style="{td}">{product_cell}</td>'
            f'<td width="{W_PRICE}" align="right" style="{td}white-space:nowrap;">&pound;{unit_price:.2f}</td>'
            f'<td width="{W_QTY}" align="right" style="{td}white-space:nowrap;">{quantity}</td>'
            f'<td width="{W_TOTAL}" align="right" style="{td}white-space:nowrap;">&pound;{line_total:.2f}</td>'
            f'</tr>'
        )

    return "\n".join(rows)


def build_receipt_html(
    order_number,
    cart_items,
    customer_name="",
    customer_phone="",
    created_at_text=None,
    include_vat_number=False,
    vat_number="",
    vat_amount=0.0,
):
    if created_at_text:
        try:
            receipt_dt = datetime.fromisoformat(created_at_text)
        except Exception:
            receipt_dt = get_receipt_datetime()
    else:
        receipt_dt = get_receipt_datetime()

    formatted_datetime = receipt_dt.strftime("%d/%m/%Y %H:%M:%S")

    subtotal = sum(float(i.get("unit_price", 0)) * int(i.get("quantity", 0)) for i in cart_items)
    total_discount = sum(float(i.get("discount", 0)) for i in cart_items)

    vat_amount = float(vat_amount or 0.0)
    net_total = max(subtotal - total_discount, 0.0)
    total_due = net_total + vat_amount

    total_qty = sum(int(i.get("quantity", 0)) for i in cart_items)

    logo_html = get_logo_html()
    address_html = "<br>".join(html.escape(line) for line in SHOP_ADDRESS_LINES)
    item_rows = build_item_rows(cart_items)
    policy_html = build_policy_html()
    hr = _hr()

    customer_name = customer_name.strip() if customer_name else ""
    customer_phone = customer_phone.strip() if customer_phone else ""

    customer_block = ""
    if customer_name or customer_phone:
        customer_block = f"""
        {hr}
        <table width="{RW}" cellspacing="0" cellpadding="0" style="font-size:12px;">
          <tr>
            <td width="160" style="padding:4px 0;">Customer</td>
            <td width="110" align="right" style="padding:4px 0;white-space:nowrap;">{html.escape(customer_name or '-')}</td>
          </tr>
          <tr>
            <td width="160" style="padding:4px 0;">Phone</td>
            <td width="110" align="right" style="padding:4px 0;white-space:nowrap;">{html.escape(customer_phone or '-')}</td>
          </tr>
        </table>
        """

    vat_header_block = ""
    if include_vat_number and vat_number.strip():
        vat_header_block = (
            f'<p style="text-align:center;font-size:11px;font-weight:700;margin:0 0 6px 0;">'
            f'VAT Number: {html.escape(vat_number.strip())}</p>'
        )

    vat_rows = ""
    if include_vat_number:
        vat_rows += f"""
        <tr>
          <td width="160" style="padding:2px 0;">VAT</td>
          <td width="110" align="right" style="padding:2px 0;white-space:nowrap;">&pound;{vat_amount:.2f}</td>
        </tr>
        """
        if vat_number.strip():
            vat_rows += f"""
            <tr>
              <td width="160" style="padding:2px 0;">VAT Number</td>
              <td width="110" align="right" style="padding:2px 0;white-space:nowrap;">{html.escape(vat_number.strip())}</td>
            </tr>
            """

    th = "font-size:11px;font-weight:700;padding-bottom:8px;border-bottom:1px solid #666;"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    padding: 0;
    background: white;
    color: #000;
    font-family: Arial, Helvetica, sans-serif;
  }}
  body {{
    width: 100%;
  }}
  .wrap {{
    width: {RW}px;
    margin: 0 auto;
    padding: 10px 0 20px 0;
  }}
</style>
</head>
<body>
<div class="wrap">

  {logo_html}

  <p style="text-align:center;font-size:26px;font-weight:900;letter-spacing:1px;margin:8px 0;">
    {html.escape(SHOP_PHONE)}
  </p>

  <p style="text-align:center;font-size:12px;line-height:1.4;margin:0 0 10px 0;">
    {html.escape(SHOP_NAME)}<br>
    {address_html}<br>
    {html.escape(SHOP_EMAIL)}
  </p>

  <p style="text-align:center;font-size:11px;font-weight:700;letter-spacing:1px;margin:6px 0 4px 0;">ORDER NUMBER</p>
  <p style="text-align:center;font-size:24px;font-weight:900;margin:0 0 7px 0;">{html.escape(order_number)}</p>

  {vat_header_block}
  {hr}

  <table width="{RW}" cellspacing="0" cellpadding="0" style="font-size:12px;">
    <tr>
      <td width="160" style="padding:4px 0;font-weight:700;">Order Details (Inc Tax)</td>
      <td width="110" align="right" style="padding:4px 0;white-space:nowrap;">{formatted_datetime}</td>
    </tr>
    <tr>
      <td width="160" style="padding:4px 0;">Staff</td>
      <td width="110" align="right" style="padding:4px 0;white-space:nowrap;">{html.escape(STAFF_NAME)}</td>
    </tr>
    <tr>
      <td width="160" style="padding:4px 0;">Device</td>
      <td width="110" align="right" style="padding:4px 0;white-space:nowrap;">{html.escape(DEVICE_NAME)}</td>
    </tr>
  </table>

  {customer_block}
  {hr}

  <table width="{RW}" cellspacing="0" cellpadding="0">
    <thead>
      <tr>
        <th width="{W_PRODUCT}" align="left" style="{th}">PRODUCT</th>
        <th width="{W_PRICE}" align="right" style="{th}">PRICE</th>
        <th width="{W_QTY}" align="right" style="{th}">QTY</th>
        <th width="{W_TOTAL}" align="right" style="{th}">TOTAL</th>
      </tr>
    </thead>
    <tbody>
      {item_rows}
    </tbody>
  </table>

  <table width="{RW}" cellspacing="0" cellpadding="0" style="margin-top:8px;font-size:12px;">
    <tr>
      <td width="160"></td>
      <td width="60" align="right" style="font-weight:700;padding-right:8px;white-space:nowrap;">Total Qty</td>
      <td width="50" align="right" style="font-weight:700;white-space:nowrap;">{total_qty}</td>
    </tr>
  </table>

  {hr}

  <table width="{RW}" cellspacing="0" cellpadding="0" style="font-size:12px;">
    <tr>
      <td width="160" style="padding:2px 0;">Sub Total</td>
      <td width="110" align="right" style="padding:2px 0;white-space:nowrap;">&pound;{subtotal:.2f}</td>
    </tr>
    <tr>
      <td width="160" style="padding:2px 0;">Discount</td>
      <td width="110" align="right" style="padding:2px 0;white-space:nowrap;">&pound;{total_discount:.2f}</td>
    </tr>
    {vat_rows}
    <tr>
      <td width="160" style="padding:2px 0;">Total</td>
      <td width="110" align="right" style="padding:2px 0;white-space:nowrap;">&pound;{total_due:.2f}</td>
    </tr>
    <tr>
      <td width="160" style="padding-top:8px;font-size:15px;font-weight:700;">Amount Due</td>
      <td width="110" align="right" style="padding-top:8px;font-size:26px;font-weight:900;white-space:nowrap;">
        &pound;{total_due:.2f}
      </td>
    </tr>
  </table>

  {hr}

  <p style="text-align:center;font-size:13px;font-weight:800;margin:0 0 8px 0;">{html.escape(THANK_YOU_TEXT)}</p>
  <p style="text-align:center;font-size:10px;line-height:1.18;margin:0;">{policy_html}</p>

</div>
</body>
</html>"""


class ReceiptPreviewDialog(QDialog):
    def __init__(
        self,
        order_number,
        cart_items,
        customer_name="",
        customer_phone="",
        created_at_text=None,
        include_vat_number=False,
        vat_number="",
        vat_amount=0.0,
        parent=None,
    ):
        super().__init__(parent)

        self.order_number = order_number
        self.cart_items = cart_items
        self.customer_name = customer_name
        self.customer_phone = customer_phone
        self.created_at_text = created_at_text
        self.include_vat_number = include_vat_number
        self.vat_number = vat_number
        self.vat_amount = float(vat_amount or 0.0)

        self.receipt_html = build_receipt_html(
            order_number=order_number,
            cart_items=cart_items,
            customer_name=customer_name,
            customer_phone=customer_phone,
            created_at_text=created_at_text,
            include_vat_number=include_vat_number,
            vat_number=vat_number,
            vat_amount=self.vat_amount,
        )

        self.setWindowTitle(f"Receipt Preview - {order_number}")
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
        self.browser.setHtml(self.receipt_html)
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
        pdf_path = RECEIPTS_DIR / f"{self.order_number}.pdf"

        if HAS_WEBENGINE:
            self._save_pdf_webengine(str(pdf_path))
        else:
            self._save_pdf_textdoc(str(pdf_path))

        return pdf_path

    def _save_pdf_webengine(self, output_path: str):
        loop = QEventLoop()

        page = QWebEnginePage()
        page.setHtml(self.receipt_html, QUrl("file:///"))

        def on_load_finished(ok):
            if not ok:
                loop.quit()
                return
            page.runJavaScript(
                "document.documentElement.scrollHeight",
                lambda h: _do_print(h)
            )

        def _do_print(height_px):
            height_mm = max(float(height_px or 400) * 0.2646 + 8, 50)
            layout = QPageLayout(
                QPageSize(QSizeF(80, height_mm), QPageSize.Unit.Millimeter),
                QPageLayout.Orientation.Portrait,
                QMarginsF(5, 4, 5, 4),
                QPageLayout.Unit.Millimeter,
            )
            page.printToPdf(output_path, layout)
            QTimer.singleShot(800, loop.quit)

        page.loadFinished.connect(on_load_finished)
        loop.exec()

    def _save_pdf_textdoc(self, output_path: str):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(output_path)

        margins = QMarginsF(5, 4, 5, 4)

        size1 = QPageSize(QSizeF(80, 600), QPageSize.Unit.Millimeter, "T80")
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
        doc.setHtml(self.receipt_html)
        doc.setTextWidth(printer.pageRect(QPrinter.Unit.Point).width())

        content_mm = (doc.size().height() / 72.0) * 25.4 + 8
        size2 = QPageSize(QSizeF(80, content_mm), QPageSize.Unit.Millimeter, "T80f")
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
            QMessageBox.information(self, "PDF Saved", f"Receipt saved:\n{path}")
        except Exception as error:
            QMessageBox.critical(self, "PDF Error", f"Could not save PDF.\n\n{error}")

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
                "-print-settings", "fit,portrait",
                "-silent",
                str(pdf_path)
            ])

            QMessageBox.information(self, "Print Sent", "Receipt sent to printer successfully.")

        except Exception as error:
            QMessageBox.critical(self, "Print Error", f"Could not print receipt.\n\n{error}")

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