"""
inventory.py
────────────
وحدة إدارة المخزن — العمليات CRUD على جدول inventory
"""

import sqlite3
import pandas as pd
from typing import Tuple, Optional


def add_device(
    conn: sqlite3.Connection,
    brand: str,
    model: str,
    color: str,
    imei: str,
    purchase_price: float,
    expected_sale_price: float,
    entry_date: str
) -> Tuple[bool, str]:
    """
    إضافة جهاز جديد للمخزن
    Returns: (success: bool, message: str)
    """
    try:
        # التحقق من أن الـ IMEI غير موجود مسبقاً
        existing = conn.execute(
            "SELECT id FROM inventory WHERE imei = ?", (imei.strip(),)
        ).fetchone()

        if existing:
            return False, f"الـ IMEI '{imei}' مسجل مسبقاً في النظام"

        conn.execute("""
            INSERT INTO inventory
                (brand, model, color, imei, purchase_price, expected_sale_price, status, entry_date)
            VALUES (?, ?, ?, ?, ?, ?, 'Available', ?)
        """, (
            brand.strip(), model.strip(), color.strip() or "Unknown",
            imei.strip(), purchase_price, expected_sale_price, entry_date
        ))
        conn.commit()
        return True, "تمت الإضافة بنجاح"

    except sqlite3.IntegrityError as e:
        return False, f"خطأ في البيانات: {str(e)}"
    except Exception as e:
        return False, f"خطأ غير متوقع: {str(e)}"


def get_all_devices(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    جلب كل الأجهزة مع حساب عدد أيام الوجود في المخزن
    """
    query = """
        SELECT
            id,
            brand,
            model,
            color,
            imei,
            purchase_price,
            expected_sale_price,
            status,
            entry_date,
            -- حساب الأيام في المخزن للأجهزة المتاحة فقط
            CASE
                WHEN status = 'Available'
                THEN CAST(julianday('now') - julianday(entry_date) AS INTEGER)
                ELSE NULL
            END AS days_in_stock
        FROM inventory
        ORDER BY entry_date DESC
    """
    return pd.read_sql(query, conn)


def get_available_devices(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    جلب الأجهزة المتاحة للبيع فقط
    """
    query = """
        SELECT *,
            CAST(julianday('now') - julianday(entry_date) AS INTEGER) AS days_in_stock
        FROM inventory
        WHERE status = 'Available'
        ORDER BY entry_date ASC
    """
    return pd.read_sql(query, conn)


def get_device_by_imei(conn: sqlite3.Connection, imei: str) -> Optional[dict]:
    """
    البحث عن جهاز بالـ IMEI — يُستخدم عند تسجيل البيع
    Returns: dict or None
    """
    row = conn.execute("""
        SELECT *,
            CAST(julianday('now') - julianday(entry_date) AS INTEGER) AS days_in_stock
        FROM inventory
        WHERE imei = ?
    """, (imei.strip(),)).fetchone()

    return dict(row) if row else None


def search_devices(
    conn: sqlite3.Connection,
    query: str,
    brand: Optional[str] = None
) -> pd.DataFrame:
    """
    البحث الذكي في المخزن — يبحث في الموديل واللون والـ IMEI والماركة
    يدعم البحث الجزئي (LIKE)
    """
    conditions = []
    params = []

    if query and query.strip():
        q = f"%{query.strip()}%"
        conditions.append("""
            (brand LIKE ? OR model LIKE ? OR color LIKE ?
             OR imei LIKE ? OR status LIKE ?)
        """)
        params.extend([q, q, q, q, q])

    if brand:
        conditions.append("brand = ?")
        params.append(brand)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT *,
            CAST(julianday('now') - julianday(entry_date) AS INTEGER) AS days_in_stock
        FROM inventory
        {where_clause}
        ORDER BY entry_date DESC
    """
    return pd.read_sql(sql, conn, params=params)


def get_aging_devices(conn: sqlite3.Connection, days_threshold: int = 30) -> pd.DataFrame:
    """
    جلب الأجهزة التي مر عليها أكثر من `days_threshold` يوم في المخزن
    تُستخدم لنظام التنبيهات في لوحة التحكم
    """
    query = """
        SELECT *,
            CAST(julianday('now') - julianday(entry_date) AS INTEGER) AS days_in_stock
        FROM inventory
        WHERE status = 'Available'
          AND CAST(julianday('now') - julianday(entry_date) AS INTEGER) > ?
        ORDER BY days_in_stock DESC
    """
    return pd.read_sql(query, conn, params=[days_threshold])


def update_device_status(conn: sqlite3.Connection, imei: str, new_status: str) -> bool:
    """
    تحديث حالة الجهاز (Available / Sold)
    يُستخدم داخلياً عند إتمام عملية البيع
    """
    try:
        conn.execute(
            "UPDATE inventory SET status = ? WHERE imei = ?",
            (new_status, imei)
        )
        conn.commit()
        return True
    except Exception:
        return False
