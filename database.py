"""
database.py
───────────
وحدة قاعدة البيانات — تهيئة SQLite وإنشاء الجداول
"""

import sqlite3
import os

# مسار قاعدة البيانات
DB_PATH = os.path.join(os.path.dirname(__file__), "mobile_suite.db")


def get_connection() -> sqlite3.Connection:
    """
    إنشاء وإرجاع اتصال بقاعدة البيانات مع دعم row_factory
    لتسهيل تحويل النتائج إلى Dictionary
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # يتيح الوصول للأعمدة بالاسم
    conn.execute("PRAGMA journal_mode=WAL")  # أداء أفضل مع القراءة المتزامنة
    conn.execute("PRAGMA foreign_keys=ON")   # تفعيل Foreign Keys
    return conn


def init_db():
    """
    تهيئة قاعدة البيانات وإنشاء الجداول إن لم تكن موجودة
    يتم استدعاؤها عند بدء تشغيل التطبيق
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ── جدول المخزن (Inventory) ─────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            brand               TEXT NOT NULL,
            model               TEXT NOT NULL,
            color               TEXT DEFAULT 'Unknown',
            imei                TEXT UNIQUE NOT NULL,    -- IMEI فريد لكل جهاز
            purchase_price      REAL NOT NULL DEFAULT 0,
            expected_sale_price REAL NOT NULL DEFAULT 0,
            status              TEXT NOT NULL DEFAULT 'Available'
                                CHECK(status IN ('Available', 'Sold')),
            entry_date          TEXT NOT NULL            -- تاريخ إدخال الجهاز بالمخزن
        )
    """)

    # ── جدول المبيعات (Sales) ────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            imei            TEXT NOT NULL,
            actual_sale_price REAL NOT NULL,
            profit          REAL NOT NULL,              -- يُحسب تلقائياً عند البيع
            customer_name   TEXT DEFAULT 'مجهول',
            customer_phone  TEXT DEFAULT '',
            sale_date       TEXT NOT NULL,
            FOREIGN KEY (imei) REFERENCES inventory(imei)
        )
    """)

    # ── فهارس لتسريع البحث ──────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_imei   ON inventory(imei)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_brand  ON inventory(brand)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_imei       ON sales(imei)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date       ON sales(sale_date)")

    conn.commit()
    conn.close()
