"""
sales.py
────────
وحدة المبيعات — تسجيل البيع والإحصاءات والتقارير
"""

import sqlite3
import pandas as pd
from typing import Tuple, Dict, Any

from inventory import get_device_by_imei, update_device_status


def sell_device(
    conn: sqlite3.Connection,
    imei: str,
    actual_sale_price: float,
    customer_name: str,
    customer_phone: str,
    sale_date: str
) -> Tuple[bool, str]:
    """
    تسجيل عملية بيع جديدة:
    1. التحقق من وجود الجهاز وأنه متاح
    2. حساب الربح تلقائياً
    3. إضافة سجل في جدول sales
    4. تحديث حالة الجهاز في inventory إلى 'Sold'
    كل العمليات في transaction واحدة لضمان التناسق
    """
    try:
        # ── التحقق من الجهاز ────────────────────────────────
        device = get_device_by_imei(conn, imei)
        if not device:
            return False, f"الجهاز بـ IMEI '{imei}' غير موجود في النظام"

        if device['status'] == 'Sold':
            return False, "هذا الجهاز تم بيعه مسبقاً"

        # ── حساب الربح ──────────────────────────────────────
        profit = actual_sale_price - device['purchase_price']

        # ── بدء Transaction ─────────────────────────────────
        conn.execute("BEGIN")

        # إضافة سجل البيع
        conn.execute("""
            INSERT INTO sales
                (imei, actual_sale_price, profit, customer_name, customer_phone, sale_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            imei.strip(),
            actual_sale_price,
            profit,
            customer_name.strip() or "مجهول",
            customer_phone.strip() or "",
            sale_date
        ))

        # تحديث حالة الجهاز في المخزن
        conn.execute(
            "UPDATE inventory SET status = 'Sold' WHERE imei = ?",
            (imei.strip(),)
        )

        conn.commit()

        profit_msg = f"الربح: {profit:,.0f} ج.م"
        return True, profit_msg

    except Exception as e:
        conn.rollback()
        return False, f"فشل تسجيل البيع: {str(e)}"


def get_all_sales(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    جلب كل سجلات المبيعات مع معلومات الجهاز (brand, model) من inventory
    """
    query = """
        SELECT
            s.sale_id,
            i.brand,
            i.model,
            s.imei,
            s.actual_sale_price,
            s.profit,
            s.customer_name,
            s.customer_phone,
            s.sale_date
        FROM sales s
        LEFT JOIN inventory i ON s.imei = i.imei
        ORDER BY s.sale_date DESC, s.sale_id DESC
    """
    return pd.read_sql(query, conn)


def get_sales_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    إرجاع ملخص إحصائي شامل يُستخدم في لوحة التحكم (KPI Cards)
    """
    # إجمالي الأرباح وعدد المبيعات
    sales_row = conn.execute("""
        SELECT
            COALESCE(SUM(profit), 0)  AS total_profit,
            COUNT(*)                  AS total_sales
        FROM sales
    """).fetchone()

    # عدد الأجهزة المتاحة
    avail_row = conn.execute("""
        SELECT COUNT(*) AS available_devices
        FROM inventory
        WHERE status = 'Available'
    """).fetchone()

    # الماركة الأكثر مبيعاً
    top_brand_row = conn.execute("""
        SELECT i.brand, COUNT(*) AS cnt
        FROM sales s
        JOIN inventory i ON s.imei = i.imei
        GROUP BY i.brand
        ORDER BY cnt DESC
        LIMIT 1
    """).fetchone()

    return {
        "total_profit":      sales_row["total_profit"],
        "total_sales":       sales_row["total_sales"],
        "available_devices": avail_row["available_devices"],
        "top_brand":         top_brand_row["brand"] if top_brand_row else None,
    }


def get_weekly_sales(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    إرجاع عدد المبيعات مجمعة أسبوعياً — للرسم البياني
    يُظهر آخر 12 أسبوع
    """
    query = """
        SELECT
            strftime('%Y-W%W', sale_date) AS week,
            COUNT(*)                      AS sales_count,
            SUM(profit)                   AS total_profit
        FROM sales
        WHERE sale_date >= DATE('now', '-84 days')  -- آخر 12 أسبوع
        GROUP BY week
        ORDER BY week ASC
    """
    return pd.read_sql(query, conn)


def get_top_brands(conn: sqlite3.Connection, limit: int = 8) -> pd.DataFrame:
    """
    أكثر الماركات مبيعاً — للرسم البياني في لوحة التحكم
    """
    query = """
        SELECT
            i.brand,
            COUNT(*) AS count
        FROM sales s
        JOIN inventory i ON s.imei = i.imei
        GROUP BY i.brand
        ORDER BY count DESC
        LIMIT ?
    """
    return pd.read_sql(query, conn, params=[limit])


def get_profit_by_month(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    الأرباح مجمعة شهرياً — للتقارير التفصيلية
    """
    query = """
        SELECT
            strftime('%Y-%m', sale_date) AS month,
            SUM(profit)                  AS profit,
            COUNT(*)                     AS sales_count
        FROM sales
        GROUP BY month
        ORDER BY month ASC
    """
    return pd.read_sql(query, conn)
