import sqlite3
from datetime import datetime

from app_paths import DATA_DIR


DB_PATH = DATA_DIR / "shop.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            customer_name TEXT,
            customer_phone TEXT,
            subtotal REAL NOT NULL DEFAULT 0,
            total_discount REAL NOT NULL DEFAULT 0,
            total_due REAL NOT NULL DEFAULT 0,
            include_vat_number INTEGER NOT NULL DEFAULT 0,
            vat_number TEXT NOT NULL DEFAULT '',
            vat_amount REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            unit_price REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 1,
            note TEXT,
            discount REAL NOT NULL DEFAULT 0,
            line_total REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
    """)

    existing_columns = {
        row["name"]
        for row in cursor.execute("PRAGMA table_info(orders)").fetchall()
    }

    if "include_vat_number" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN include_vat_number INTEGER NOT NULL DEFAULT 0")

    if "vat_number" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN vat_number TEXT NOT NULL DEFAULT ''")

    if "vat_amount" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN vat_amount REAL NOT NULL DEFAULT 0")

    connection.commit()
    connection.close()


def generate_order_number():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT order_number
        FROM orders
        WHERE order_number LIKE 'ORD-%'
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    max_number = 0

    for row in rows:
        value = row["order_number"] or ""
        if value.startswith("ORD-"):
            suffix = value[4:]
            if suffix.isdigit():
                number = int(suffix)
                if number > max_number:
                    max_number = number

    next_number = max_number + 1
    return f"ORD-{next_number:06d}"


def calculate_order_totals(cart_items):
    subtotal = 0.0
    total_discount = 0.0

    for item in cart_items:
        unit_price = float(item.get("unit_price", 0.0))
        quantity = int(item.get("quantity", 0))
        discount = float(item.get("discount", 0.0))

        subtotal += unit_price * quantity
        total_discount += discount

    total_due = max(subtotal - total_discount, 0.0)

    return round(subtotal, 2), round(total_discount, 2), round(total_due, 2)


def save_order(
    customer_name,
    customer_phone,
    cart_items,
    include_vat_number=False,
    vat_number="",
    vat_amount=0.0,
):
    if not cart_items:
        raise ValueError("Cart is empty")

    subtotal, total_discount, total_due = calculate_order_totals(cart_items)

    order_number = generate_order_number()
    created_at = datetime.now().isoformat(timespec="seconds")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO orders (
            order_number,
            customer_name,
            customer_phone,
            subtotal,
            total_discount,
            total_due,
            include_vat_number,
            vat_number,
            vat_amount,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_number,
        customer_name.strip() if customer_name else "",
        customer_phone.strip() if customer_phone else "",
        subtotal,
        total_discount,
        total_due,
        1 if include_vat_number else 0,
        vat_number.strip() if vat_number else "",
        round(float(vat_amount or 0.0), 2),
        created_at,
    ))

    order_id = cursor.lastrowid

    for item in cart_items:
        unit_price = float(item.get("unit_price", 0.0))
        quantity = int(item.get("quantity", 0))
        discount = float(item.get("discount", 0.0))
        line_subtotal = unit_price * quantity
        line_total = max(line_subtotal - discount, 0.0)

        cursor.execute("""
            INSERT INTO order_items (
                order_id,
                product_name,
                unit_price,
                quantity,
                note,
                discount,
                line_total
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            str(item.get("product_name", "")).strip(),
            round(unit_price, 2),
            quantity,
            str(item.get("note", "")).strip(),
            round(discount, 2),
            round(line_total, 2),
        ))

    connection.commit()
    connection.close()

    return order_id, order_number


def get_all_orders():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            order_number,
            customer_name,
            customer_phone,
            subtotal,
            total_discount,
            total_due,
            include_vat_number,
            vat_number,
            vat_amount,
            created_at
        FROM orders
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def search_orders(search_text):
    value = (search_text or "").strip()

    if not value:
        return get_all_orders()

    connection = get_connection()
    cursor = connection.cursor()

    normalized = value.upper()

    cursor.execute("""
        SELECT
            id,
            order_number,
            customer_name,
            customer_phone,
            subtotal,
            total_discount,
            total_due,
            include_vat_number,
            vat_number,
            vat_amount,
            created_at
        FROM orders
        WHERE
            UPPER(order_number) LIKE ?
            OR created_at LIKE ?
        ORDER BY id DESC
    """, (
        f"%{normalized}%",
        f"%{value}%",
    ))

    rows = cursor.fetchall()
    results = [dict(row) for row in rows]

    if results:
        connection.close()
        return results

    cursor.execute("""
        SELECT
            id,
            order_number,
            customer_name,
            customer_phone,
            subtotal,
            total_discount,
            total_due,
            include_vat_number,
            vat_number,
            vat_amount,
            created_at
        FROM orders
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    matched = []
    search_lower = value.lower()

    for row in rows:
        order = dict(row)
        created_at_text = order.get("created_at", "")

        try:
            dt = datetime.fromisoformat(created_at_text)
            formatted_1 = dt.strftime("%d %b %Y").lower()
            formatted_2 = dt.strftime("%d %b %Y %H:%M").lower()
            formatted_3 = dt.strftime("%d/%m/%Y").lower()
            formatted_4 = dt.strftime("%Y-%m-%d").lower()

            if (
                search_lower in formatted_1
                or search_lower in formatted_2
                or search_lower in formatted_3
                or search_lower in formatted_4
            ):
                matched.append(order)
        except Exception:
            pass

    return matched


def get_order_by_id(order_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            order_number,
            customer_name,
            customer_phone,
            subtotal,
            total_discount,
            total_due,
            include_vat_number,
            vat_number,
            vat_amount,
            created_at
        FROM orders
        WHERE id = ?
    """, (order_id,))

    row = cursor.fetchone()
    connection.close()

    return dict(row) if row else None


def get_order_items(order_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            product_name,
            unit_price,
            quantity,
            note,
            discount,
            line_total
        FROM order_items
        WHERE order_id = ?
        ORDER BY id ASC
    """, (order_id,))

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def update_order(
    order_id,
    customer_name,
    customer_phone,
    cart_items,
    include_vat_number=None,
    vat_number=None,
    vat_amount=None,
):
    if not cart_items:
        raise ValueError("Order must contain at least one item")

    subtotal, total_discount, total_due = calculate_order_totals(cart_items)

    connection = get_connection()
    cursor = connection.cursor()

    current_order = get_order_by_id(order_id)
    if current_order is None:
        connection.close()
        raise ValueError("Order not found")

    final_include_vat_number = current_order.get("include_vat_number", 0) if include_vat_number is None else (1 if include_vat_number else 0)
    final_vat_number = current_order.get("vat_number", "") if vat_number is None else (vat_number.strip() if vat_number else "")
    final_vat_amount = current_order.get("vat_amount", 0.0) if vat_amount is None else round(float(vat_amount or 0.0), 2)

    cursor.execute("""
        UPDATE orders
        SET
            customer_name = ?,
            customer_phone = ?,
            subtotal = ?,
            total_discount = ?,
            total_due = ?,
            include_vat_number = ?,
            vat_number = ?,
            vat_amount = ?
        WHERE id = ?
    """, (
        customer_name.strip() if customer_name else "",
        customer_phone.strip() if customer_phone else "",
        subtotal,
        total_discount,
        total_due,
        final_include_vat_number,
        final_vat_number,
        final_vat_amount,
        order_id,
    ))

    cursor.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))

    for item in cart_items:
        unit_price = float(item.get("unit_price", 0.0))
        quantity = int(item.get("quantity", 0))
        discount = float(item.get("discount", 0.0))
        line_subtotal = unit_price * quantity
        line_total = max(line_subtotal - discount, 0.0)

        cursor.execute("""
            INSERT INTO order_items (
                order_id,
                product_name,
                unit_price,
                quantity,
                note,
                discount,
                line_total
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            str(item.get("product_name", "")).strip(),
            round(unit_price, 2),
            quantity,
            str(item.get("note", "")).strip(),
            round(discount, 2),
            round(line_total, 2),
        ))

    connection.commit()
    connection.close()


def delete_order(order_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    connection.commit()
    connection.close()