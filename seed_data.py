"""
seed_data.py
────────────
سكريبت لملء قاعدة البيانات ببيانات تجريبية واقعية
شغّله مرة واحدة: python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_connection
from inventory import add_device
from sales import sell_device
from datetime import date, timedelta
import random

def seed():
    init_db()
    conn = get_connection()
    print("🌱 بدء إضافة البيانات التجريبية...")

    # بيانات أجهزة تجريبية
    devices = [
        # (brand, model, color, imei, purchase_price, expected_price, days_ago)
        ("Samsung", "Galaxy S24 Ultra",  "Titanium Black", "35892012345678", 22000, 27000, 45),
        ("Samsung", "Galaxy S24 Ultra",  "Titanium Gray",  "35892012345679", 22000, 27000, 12),
        ("Samsung", "Galaxy A55",        "Iceblue",        "35892012345680", 7500,  9800,  38),
        ("Samsung", "Galaxy A35",        "Navy Blue",      "35892012345681", 5800,  7500,  5),
        ("Apple",   "iPhone 15 Pro Max", "Black Titanium", "35892012345682", 30000, 38000, 60),
        ("Apple",   "iPhone 15 Pro",     "White Titanium", "35892012345683", 26000, 32000, 20),
        ("Apple",   "iPhone 15",         "Pink",           "35892012345684", 18000, 22000, 3),
        ("Apple",   "iPhone 14",         "Midnight",       "35892012345685", 14000, 17000, 55),
        ("Xiaomi",  "14 Ultra",          "White",          "35892012345686", 18000, 22000, 8),
        ("Xiaomi",  "Redmi Note 13 Pro", "Aurora Purple",  "35892012345687", 6500,  8500,  35),
        ("OPPO",    "Find X7 Pro",       "Sepia Brown",    "35892012345688", 19000, 24000, 15),
        ("Huawei",  "Pura 70 Pro",       "White",          "35892012345689", 17000, 21000, 42),
        ("Samsung", "Galaxy Z Fold 6",   "Navy",           "35892012345690", 45000, 55000, 2),
        ("Apple",   "iPhone 15 Pro Max", "Desert Titanium","35892012345691", 30000, 37500, 10),
        ("Xiaomi",  "13T Pro",           "Black",          "35892012345692", 12000, 15000, 25),
    ]

    added_imeis = []
    for brand, model, color, imei, pp, esp, days_ago in devices:
        entry_date = str(date.today() - timedelta(days=days_ago))
        success, msg = add_device(conn, brand, model, color, imei, pp, esp, entry_date)
        if success:
            added_imeis.append((imei, pp))
            print(f"  ✅ أُضيف: {brand} {model} — {imei}")
        else:
            print(f"  ⚠️  تخطي: {msg}")

    # بيع بعض الأجهزة
    sales_data = [
        (added_imeis[0][0], added_imeis[0][1] + 4800, "محمد أحمد",  "01012345678", 40),
        (added_imeis[2][0], added_imeis[2][1] + 2100, "سارة علي",   "01098765432", 32),
        (added_imeis[4][0], added_imeis[4][1] + 7500, "خالد محمود", "01234567890", 55),
        (added_imeis[7][0], added_imeis[7][1] + 2800, "نورا حسين",  "01156789012", 48),
        (added_imeis[9][0], added_imeis[9][1] + 1800, "عمر يوسف",   "01287654321", 28),
        (added_imeis[11][0],added_imeis[11][1]+ 3900, "ليلى إبراهيم","01345678901", 38),
        (added_imeis[13][0],added_imeis[13][1]+ 7200, "أحمد السيد", "01567890123", 8),
    ]

    for imei, price, cname, cphone, days_ago in sales_data:
        sale_date = str(date.today() - timedelta(days=days_ago))
        success, msg = sell_device(conn, imei, price, cname, cphone, sale_date)
        if success:
            print(f"  💰 بيع: {imei} — {msg}")
        else:
            print(f"  ⚠️  فشل البيع: {msg}")

    conn.close()
    print("\n✨ اكتملت إضافة البيانات التجريبية بنجاح!")
    print("▶️  شغّل: streamlit run app.py")

if __name__ == "__main__":
    seed()
