"""
╔══════════════════════════════════════════════════════════════╗
║         Mobile Inventory & Sales Suite                       ║
║         نظام إدارة مخازن ومبيعات الهواتف الذكية             ║
║         Built with Python + Streamlit + SQLite               ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import easyocr
import numpy as np
from PIL import Image

# تعريف القارئ مرة واحدة عشان ميبطأش البرنامج
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()
import pandas as pd
from datetime import datetime, date
import io

# ─── استيراد الوحدات الداخلية ───────────────────────────────
from database import init_db, get_connection
from inventory import (
    add_device, get_all_devices, get_available_devices,
    search_devices, get_aging_devices, get_device_by_imei
)
from sales import (
    sell_device, get_all_sales, get_sales_summary,
    get_weekly_sales, get_top_brands
)
from reports import export_inventory_excel, export_sales_excel

# ─── إعداد الصفحة ───────────────────────────────────────────
st.set_page_config(
    page_title="Mobile Suite | نظام المخازن",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── تحميل CSS المخصص ───────────────────────────────────────
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

    :root {
        --bg-primary: #0a0e1a;
        --bg-card: #111827;
        --bg-card-hover: #1a2435;
        --accent-cyan: #00d4ff;
        --accent-green: #00ff88;
        --accent-orange: #ff6b35;
        --accent-red: #ff3366;
        --accent-purple: #7c3aed;
        --text-primary: #f0f4ff;
        --text-secondary: #8892a4;
        --border: rgba(0, 212, 255, 0.15);
        --glow: 0 0 20px rgba(0, 212, 255, 0.3);
    }

    /* ── الخلفية العامة ── */
    .stApp {
        background: var(--bg-primary);
        background-image:
            radial-gradient(ellipse at 10% 20%, rgba(0, 212, 255, 0.05) 0%, transparent 60%),
            radial-gradient(ellipse at 90% 80%, rgba(0, 255, 136, 0.03) 0%, transparent 60%);
        font-family: 'Cairo', sans-serif;
    }

    /* ── الشريط الجانبي ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1421 0%, #111827 100%);
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--accent-cyan) !important;
    }

    /* ── بطاقات KPI ── */
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 24px 20px;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--accent-color, var(--accent-cyan));
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--glow);
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 900;
        color: var(--accent-color, var(--accent-cyan));
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 6px;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .kpi-icon {
        font-size: 1.8rem;
        margin-bottom: 8px;
    }

    /* ── تنبيهات الأجهزة القديمة ── */
    .aging-alert {
        background: linear-gradient(135deg, rgba(255, 107, 53, 0.15), rgba(255, 51, 102, 0.1));
        border: 1px solid rgba(255, 107, 53, 0.4);
        border-left: 4px solid var(--accent-orange);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 8px 0;
        direction: rtl;
    }
    .aging-alert-title {
        color: var(--accent-orange);
        font-weight: 700;
        font-size: 1rem;
    }
    .aging-alert-body {
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-top: 4px;
    }

    /* ── الجداول ── */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        overflow: hidden;
    }

    /* ── عناوين الأقسام ── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 24px 0 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
        direction: rtl;
    }
    .section-header h2 {
        color: var(--text-primary);
        font-size: 1.4rem;
        font-weight: 700;
        margin: 0;
    }
    .section-accent {
        width: 4px;
        height: 28px;
        background: var(--accent-cyan);
        border-radius: 2px;
    }

    /* ── باج الحالة ── */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .badge-available {
        background: rgba(0, 255, 136, 0.15);
        color: var(--accent-green);
        border: 1px solid rgba(0, 255, 136, 0.3);
    }
    .badge-sold {
        background: rgba(255, 51, 102, 0.15);
        color: var(--accent-red);
        border: 1px solid rgba(255, 51, 102, 0.3);
    }
    .badge-aging {
        background: rgba(255, 107, 53, 0.15);
        color: var(--accent-orange);
        border: 1px solid rgba(255, 107, 53, 0.3);
    }

    /* ── أزرار مخصصة ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-cyan), #0099cc);
        color: #0a0e1a;
        font-family: 'Cairo', sans-serif;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 8px 20px;
        transition: all 0.2s;
        letter-spacing: 0.03em;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(0, 212, 255, 0.4);
    }

    /* ── Logo / Brand ── */
    .brand-logo {
        text-align: center;
        padding: 20px 0 30px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
    }
    .brand-logo .logo-icon { font-size: 2.5rem; }
    .brand-logo .logo-title {
        font-size: 1.1rem;
        font-weight: 900;
        color: var(--accent-cyan);
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    .brand-logo .logo-sub {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 4px;
    }

    /* ── صندوق البحث بالسكانر ── */
    .scanner-box {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.08), rgba(0, 255, 136, 0.05));
        border: 1px dashed rgba(0, 212, 255, 0.4);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-bottom: 20px;
    }
    .scanner-icon { font-size: 2rem; margin-bottom: 8px; }
    .scanner-hint { color: var(--text-secondary); font-size: 0.85rem; }

    /* ── الخطوط العربية ── */
    h1, h2, h3, p, label, .stMarkdown {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    /* ── إخفاء عناصر Streamlit الافتراضية ── */
   

    /* ── input fields ── */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        font-family: 'Cairo', sans-serif !important;
    }
    .stTextInput input:focus {
        border-color: var(--accent-cyan) !important;
        box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ─── دالة مساعدة لعرض KPI Card ────────────────────────────
def kpi_card(icon, value, label, color="var(--accent-cyan)"):
    st.markdown(f"""
    <div class="kpi-card" style="--accent-color: {color}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── دالة مساعدة لعرض عنوان قسم ───────────────────────────
def section_header(title, icon=""):
    st.markdown(f"""
    <div class="section-header">
        <div class="section-accent"></div>
        <h2>{icon} {title}</h2>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# الشريط الجانبي للتنقل
# ══════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # الشعار
        st.markdown("""
        <div class="brand-logo">
            <div class="logo-icon">📱</div>
            <div class="logo-title">Mobile Suite</div>
            <div class="logo-sub">نظام إدارة المخازن والمبيعات</div>
        </div>
        """, unsafe_allow_html=True)

        # قائمة التنقل
        st.markdown("### 🗂️ القائمة الرئيسية")
        pages = {
            "📊 لوحة التحكم": "dashboard",
            "📦 المخزن": "inventory",
            "💰 المبيعات": "sales",
            "🔍 البحث الذكي": "search",
            "📈 التقارير": "reports",
        }
        selected = st.radio(
            "اختر القسم",
            list(pages.keys()),
            label_visibility="collapsed"
        )

        # إحصاءات سريعة في الشريط الجانبي
        st.markdown("---")
        conn = get_connection()
        total = pd.read_sql("SELECT COUNT(*) as n FROM inventory", conn).iloc[0]['n']
        available = pd.read_sql("SELECT COUNT(*) as n FROM inventory WHERE status='Available'", conn).iloc[0]['n']
        sold_today = pd.read_sql(
            "SELECT COUNT(*) as n FROM sales WHERE DATE(sale_date)=DATE('now')", conn
        ).iloc[0]['n']
        conn.close()

        st.markdown("### 📌 إحصاء سريع")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("إجمالي", total)
            st.metric("متاح", available)
        with col2:
            st.metric("مبيع", total - available)
            st.metric("اليوم", sold_today)

        st.markdown("---")
        st.markdown(f"<small style='color:#8892a4'>آخر تحديث: {datetime.now().strftime('%H:%M')}</small>",
                    unsafe_allow_html=True)

        return pages[selected]

# ══════════════════════════════════════════════════════════════
# صفحة: لوحة التحكم (Dashboard)
# ══════════════════════════════════════════════════════════════
def page_dashboard():
    section_header("لوحة التحكم التحليلية", "📊")

    conn = get_connection()
    summary = get_sales_summary(conn)
    conn.close()

    # ── KPI Cards ────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("💵", f"{summary['total_profit']:,.0f} ج", "إجمالي الأرباح", "var(--accent-green)")
    with c2:
        kpi_card("📦", str(summary['available_devices']), "أجهزة متاحة", "var(--accent-cyan)")
    with c3:
        kpi_card("🏆", summary['top_brand'] or "—", "الماركة الأكثر مبيعاً", "var(--accent-orange)")
    with c4:
        kpi_card("🛒", str(summary['total_sales']), "إجمالي المبيعات", "var(--accent-purple)")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── الرسوم البيانية ──────────────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        section_header("نمو المبيعات الأسبوعي", "📈")
        conn = get_connection()
        weekly = get_weekly_sales(conn)
        conn.close()
        if not weekly.empty:
            st.bar_chart(
                weekly.set_index('week')['sales_count'],
                color="#00d4ff",
                use_container_width=True
            )
        else:
            st.info("لا توجد بيانات مبيعات حتى الآن")

    with col_right:
        section_header("المبيعات حسب الماركة", "🏷️")
        conn = get_connection()
        brands = get_top_brands(conn)
        conn.close()
        if not brands.empty:
            st.bar_chart(
                brands.set_index('brand')['count'],
                color="#00ff88",
                use_container_width=True
            )
        else:
            st.info("لا توجد بيانات حتى الآن")

    # ── تنبيهات الأجهزة القديمة (Aging Stock) ───────────────
    section_header("⚠️ تنبيهات المخزن القديم (أكثر من 30 يوم)", "🔔")
    conn = get_connection()
    aging = get_aging_devices(conn)
    conn.close()

    if not aging.empty:
        st.markdown(f"""
        <div class="aging-alert">
            <div class="aging-alert-title">⚠️ تحذير: {len(aging)} جهاز في المخزن أكثر من 30 يوم</div>
            <div class="aging-alert-body">هذه الأجهزة تحتاج إلى مراجعة السعر أو عرض خصم لتسريع المبيع</div>
        </div>
        """, unsafe_allow_html=True)

        # تلوين الأجهزة القديمة
        aging['⚠️ أيام في المخزن'] = aging['days_in_stock']
        display_cols = ['brand', 'model', 'color', 'imei', 'expected_sale_price', '⚠️ أيام في المخزن']
        rename_map = {
            'brand': 'الماركة', 'model': 'الموديل', 'color': 'اللون',
            'imei': 'IMEI', 'expected_sale_price': 'سعر البيع المتوقع'
        }
        st.dataframe(
            aging[display_cols].rename(columns=rename_map),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ لا توجد أجهزة قديمة في المخزن — المخزن في وضع جيد!")

# ══════════════════════════════════════════════════════════════
# صفحة: المخزن (Inventory)
# ══════════════════════════════════════════════════════════════
def page_inventory():
    section_header("إدارة المخزن", "📦")

    tab1, tab2 = st.tabs(["➕ إضافة جهاز جديد", "📋 قائمة المخزن"])

    # ── تبويب: إضافة جهاز ───────────────────────────────────
    with tab1:
        # صندوق السكانر
        st.markdown("""
        <div class="scanner-box">
            <div class="scanner-icon">📷</div>
            <div style="color: var(--accent-cyan); font-weight: 700; font-size: 1rem;">
                إدخال IMEI بالسكانر أو الكتابة اليدوية
            </div>
            <div class="scanner-hint">
                وجّه السكانر نحو الباركود أو اكتب الـ IMEI يدوياً — يدعم auto-focus
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("add_device_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                brand = st.selectbox("🏷️ الماركة", [
                    "Samsung", "Apple", "Huawei", "Xiaomi", "OPPO",
                    "Vivo", "OnePlus", "Realme", "Nokia", "Sony", "Other"
                ])
                model = st.text_input("📱 الموديل", placeholder="مثال: Galaxy S24 Ultra")
                color = st.text_input("🎨 اللون", placeholder="مثال: Phantom Black")

            with col2:
                # حقل IMEI مع auto-focus hint
                imei = st.text_input(
                    "🔢 IMEI / Serial Number *",
                    placeholder="امسح البار كود أو اكتب الـ IMEI هنا...",
                    help="يمكنك استخدام السكانر مباشرةً في هذا الحقل — الحقل جاهز للاستقبال"
                )
                purchase_price = st.number_input("💸 سعر الشراء (ج.م)", min_value=0.0, step=50.0)
                expected_sale_price = st.number_input("🎯 سعر البيع المتوقع (ج.م)", min_value=0.0, step=50.0)

            with col3:
                entry_date = st.date_input("📅 تاريخ الإدخال", value=date.today())
                st.markdown("<br>", unsafe_allow_html=True)
                # معاينة الربح المتوقع
                expected_profit = expected_sale_price - purchase_price
                profit_color = "#00ff88" if expected_profit > 0 else "#ff3366"
                st.markdown(f"""
                <div style="background: var(--bg-card); border: 1px solid var(--border);
                     border-radius: 10px; padding: 16px; text-align: center;">
                    <div style="color: var(--text-secondary); font-size: 0.8rem;">الربح المتوقع</div>
                    <div style="color: {profit_color}; font-size: 1.8rem; font-weight: 900;
                         font-family: 'JetBrains Mono', monospace;">
                        {expected_profit:,.0f} ج
                    </div>
                </div>
                """, unsafe_allow_html=True)

            submit = st.form_submit_button("✅ إضافة الجهاز للمخزن", use_container_width=True)

            if submit:
                if not imei or not model:
                    st.error("❌ الرجاء إدخال الموديل والـ IMEI على الأقل")
                else:
                    conn = get_connection()
                    success, msg = add_device(
                        conn, brand, model, color, imei,
                        purchase_price, expected_sale_price, str(entry_date)
                    )
                    conn.close()
                    if success:
                        st.success(f"✅ تم إضافة {brand} {model} بنجاح!")
                        st.balloons()
                    else:
                        st.error(f"❌ خطأ: {msg}")

    # ── تبويب: قائمة المخزن ──────────────────────────────────
    with tab2:
        conn = get_connection()
        devices = get_all_devices(conn)
        conn.close()

        if devices.empty:
            st.info("📭 المخزن فارغ حالياً — ابدأ بإضافة أجهزة")
        else:
            # فلتر الحالة
            status_filter = st.selectbox(
                "فلتر الحالة",
                ["الكل", "Available - متاح", "Sold - مباع"],
                label_visibility="visible"
            )

            if "Available" in status_filter:
                devices = devices[devices['status'] == 'Available']
            elif "Sold" in status_filter:
                devices = devices[devices['status'] == 'Sold']

            # إعادة تسمية الأعمدة للعربية
            rename_map = {
                'id': '#', 'brand': 'الماركة', 'model': 'الموديل',
                'color': 'اللون', 'imei': 'IMEI',
                'purchase_price': 'سعر الشراء', 'expected_sale_price': 'سعر البيع',
                'status': 'الحالة', 'entry_date': 'تاريخ الإدخال',
                'days_in_stock': 'أيام بالمخزن'
            }
            display = devices.rename(columns=rename_map)

            st.dataframe(display, use_container_width=True, hide_index=True)
            st.caption(f"إجمالي: {len(devices)} جهاز")

# ══════════════════════════════════════════════════════════════
# صفحة: المبيعات (Sales)
# ══════════════════════════════════════════════════════════════
def page_sales():
    section_header("تسجيل المبيعات", "💰")

    tab1, tab2 = st.tabs(["💳 تسجيل عملية بيع", "📋 سجل المبيعات"])

    with tab1:
        # صندوق السكانر للبيع
        st.markdown("""
        <div class="scanner-box">
            <div class="scanner-icon">🔍</div>
            <div style="color: var(--accent-green); font-weight: 700;">ابحث عن الجهاز بالـ IMEI</div>
            <div class="scanner-hint">استخدم السكانر أو اكتب الـ IMEI للعثور على الجهاز</div>
        </div>
        """, unsafe_allow_html=True)

        # البحث عن الجهاز أولاً
        # إضافة كاميرا الموبايل للمسح
       # 1. الكاميرا للمسح
img_file = st.camera_input("📷 امسح السيريال نمبر (IMEI) من علبة الموبايل")

detected_imei = ""

# 2. تحليل الصورة لو المستخدم صور
if img_file:
    image = Image.open(img_file)
    img_array = np.array(image)
    
    with st.spinner('جاري استخراج السيريال...'):
        try:
            # استخدام الـ reader اللي عرفناه فوق خالص
            result = reader.readtext(img_array)
            for (bbox, text, prob) in result:
                clean_text = "".join(text.split())
                # التأكد إن الرقم 15 خانة (نظام الـ IMEI)
                if len(clean_text) == 15 and clean_text.isdigit():
                    detected_imei = clean_text
                    st.success(f"✅ تم التقاط السيريال: {detected_imei}")
                    break
        except Exception as e:
            st.error("حدث خطأ في القراءة، حاول تقرب الكاميرا من الرقم")

# 3. خانة الإدخال (تاخد القيمة أوتوماتيك من المتغير detected_imei)
search_imei = st.text_input("🔢 IMEI / Serial", value=detected_imei, key="sale_imei_search")

device_info = None
if search_imei:
    conn = get_connection()
    device_info = get_device_by_imei(conn, search_imei)
    conn.close()

if device_info:
    if device_info['status'] == 'Sold':
        st.error(f"❌ هذا الجهاز تم بيعه مسبقاً")
        device_info = None
    else:
        st.success(f"✅ تم العثور على الجهاز: {device_info['brand']} {device_info['model']} — {device_info['color']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("سعر الشراء", f"{device_info['purchase_price']:,.0f} ج")
        with col2:
            st.metric("السعر المتوقع", f"{device_info['expected_sale_price']:,.0f} ج")
        with col3:
            st.metric("أيام بالمخزن", device_info.get('days_in_stock', 0))
else:
    st.warning("⚠️ لم يتم العثور على الجهاز — تحقق من الـ IMEI")

st.markdown("---")

# --- المحرك الرئيسي للتنقل ---
# نادى على الـ Sidebar أولاً وخزن الاختيار في متغير
selected = render_sidebar()

# قاموس لربط الأسماء العربية بالوظائف البرمجية
pages_map = {
    "لوحة التحكم": "dashboard",
    "المخزن": "inventory",
    "المبيعات": "sales",
    "البحث الذكي": "search",
    "التقارير": "reports"
}

# التنفيذ بناءً على الصفحة المختارة
if selected in pages_map:
    page = pages_map[selected]
    
    if page == "inventory":
        from inventory import render_inventory_page
        render_inventory_page()
    elif page == "sales":
        # هنا هتحط كود صفحة المبيعات كله (بما فيه الـ Form اللي في صورة 17d761)
        st.header("🛒 قسم المبيعات")
        # استدعاء دالة المبيعات اللي فيها الكاميرا
        render_sales_page() 
    elif page == "reports":
        from reports import render_reports_page
        render_reports_page()

with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        sale_imei = st.text_input(
            "🔢 IMEI المؤكد",
            value=search_imei if device_info else "",
            placeholder="IMEI الجهاز"
        )
        customer_name = st.text_input("👤 اسم العميل", placeholder="الاسم الكامل")
        customer_phone = st.text_input("📞 رقم الهاتف", placeholder="01xxxxxxxxx")

    with col2:
        default_price = device_info['expected_sale_price'] if device_info else 0.0
        actual_price = st.number_input(
            "💵 سعر البيع الفعلي (ج.م)",
            min_value=0.0,
            value=float(default_price),
            step=50.0
        )
        sale_date = st.date_input("📅 تاريخ البيع", value=date.today())

        # معاينة الربح
        if device_info:
            profit = actual_price - device_info['purchase_price']
            profit_color = "#00ff88" if profit > 0 else "#ff3366"
            st.markdown(f"""
            <div style="background: var(--bg-card); border: 1px solid var(--border);
                    border-radius: 10px; padding: 16px; text-align: center; margin-top: 8px;">
                <div style="color: var(--text-secondary); font-size: 0.8rem;">الربح المتوقع</div>
                <div style="color: {profit_color}; font-size: 1.8rem; font-weight: 900;
                        font-family: 'JetBrains Mono', monospace;">
                    {profit:,.0f} ج
                </div>
            </div>
            """, unsafe_allow_html=True)

    submit_sale = st.form_submit_button("✅ تأكيد البيع", use_container_width=True)

    if submit_sale:
        if not sale_imei:
            st.error("❌ الرجاء إدخال الـ IMEI")
        else:
            conn = get_connection()
            success, msg = sell_device(
                conn, sale_imei, actual_price,
                customer_name, customer_phone, str(sale_date)
            )
            conn.close()
            if success:
                st.success(f"🎉 تم تسجيل البيع بنجاح! {msg}")
                st.balloons()
            else:
                st.error(f"❌ {msg}")

with tab2:
    conn = get_connection()
sales = get_all_sales(conn)
conn.close()

if sales.empty:
    st.info("📭 لا توجد مبيعات مسجلة حتى الآن")
else:
    rename_map = {
        'sale_id': '#', 'brand': 'الماركة', 'model': 'الموديل',
        'imei': 'IMEI', 'actual_sale_price': 'سعر البيع',
        'profit': 'الربح', 'customer_name': 'العميل',
        'customer_phone': 'الهاتف', 'sale_date': 'تاريخ البيع'
    }
    st.dataframe(
        sales.rename(columns=rename_map),
        use_container_width=True,
        hide_index=True
    )

    # إجمالي الأرباح
    total_profit = sales['profit'].sum()
    st.markdown(f"""
    <div style="text-align: center; padding: 16px; margin-top: 12px;
            background: rgba(0,255,136,0.1); border-radius: 12px; border: 1px solid rgba(0,255,136,0.3);">
        <span style="color: #8892a4;">إجمالي الأرباح: </span>
        <span style="color: #00ff88; font-size: 1.5rem; font-weight: 900;
                font-family: 'JetBrains Mono';">{total_profit:,.0f} ج.م</span>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# صفحة: البحث الذكي (Smart Search)
# ══════════════════════════════════════════════════════════════
def page_search():
    section_header("البحث الذكي", "🔍")

st.markdown("""
<div class="scanner-box">
<div class="scanner-icon">🔎</div>
<div style="color: var(--accent-cyan); font-weight: 700;">
    ابحث بأي معلومة — الموديل أو IMEI أو اللون أو الماركة
</div>
<div class="scanner-hint">البحث فوري ومباشر بدون الضغط على Enter</div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    query = st.text_input(
    "🔍 ابحث هنا...",
    placeholder="اكتب الموديل أو الـ IMEI أو اللون...",
    label_visibility="collapsed",
    key="smart_search"
)
with col2:
    search_in = st.selectbox("البحث في", ["الكل", "المخزن فقط", "المبيعات فقط"],
                            label_visibility="collapsed")
with col3:
    brand_filter = st.selectbox("الماركة", [
    "الكل", "Samsung", "Apple", "Huawei", "Xiaomi", "OPPO", "Other"
], label_visibility="collapsed")

if query or brand_filter != "الكل":
    conn = get_connection()
results = search_devices(conn, query, brand_filter if brand_filter != "الكل" else None)
conn.close()

if "المبيعات فقط" in search_in:
    results = results[results['status'] == 'Sold']
elif "المخزن فقط" in search_in:
    results = results[results['status'] == 'Available']

st.markdown(f"**{len(results)} نتيجة**")

if not results.empty:
    # تلوين الأجهزة حسب الحالة
    def highlight_status(row):
        if row['status'] == 'Sold':
            return ['background-color: rgba(255,51,102,0.08)'] * len(row)
        elif row.get('days_in_stock', 0) > 30:
            return ['background-color: rgba(255,107,53,0.08)'] * len(row)
        return [''] * len(row)

    rename_map = {
        'brand': 'الماركة', 'model': 'الموديل', 'color': 'اللون',
        'imei': 'IMEI', 'purchase_price': 'سعر الشراء',
        'expected_sale_price': 'سعر البيع', 'status': 'الحالة',
        'entry_date': 'تاريخ الإدخال', 'days_in_stock': 'أيام بالمخزن'
    }
    st.dataframe(
        results.rename(columns=rename_map),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("لا توجد نتائج مطابقة")

# ══════════════════════════════════════════════════════════════
# صفحة: التقارير والتصدير (Reports)
# ══════════════════════════════════════════════════════════════
def page_reports():
    section_header("التقارير والتصدير", "📈")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📦 تقرير المخزن")
        conn = get_connection()
        inv_data = get_all_devices(conn)
        conn.close()

        if not inv_data.empty:
            # إحصاءات المخزن
            total_val_purchase = inv_data['purchase_price'].sum()
            total_val_expected = inv_data[inv_data['status']=='Available']['expected_sale_price'].sum()
            available_count = len(inv_data[inv_data['status']=='Available'])

            m1, m2, m3 = st.columns(3)
            m1.metric("متاح", available_count)
            m2.metric("قيمة الشراء", f"{total_val_purchase:,.0f}")
            m3.metric("قيمة البيع المتوقعة", f"{total_val_expected:,.0f}")

            # تصدير Excel
            excel_inv = export_inventory_excel(inv_data)
            st.download_button(
                label="📥 تصدير المخزن — Excel",
                data=excel_inv,
                file_name=f"inventory_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # تصدير CSV
            csv_inv = inv_data.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📄 تصدير المخزن — CSV",
                data=csv_inv,
                file_name=f"inventory_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col2:
        st.markdown("#### 💰 تقرير المبيعات")
        conn = get_connection()
        sales_data = get_all_sales(conn)
        conn.close()

        if not sales_data.empty:
            total_revenue = sales_data['actual_sale_price'].sum()
            total_profit = sales_data['profit'].sum()
            avg_profit = sales_data['profit'].mean()

            m1, m2, m3 = st.columns(3)
            m1.metric("إجمالي المبيعات", len(sales_data))
            m2.metric("إجمالي الإيرادات", f"{total_revenue:,.0f}")
            m3.metric("صافي الربح", f"{total_profit:,.0f}")

            # تصدير Excel
            excel_sales = export_sales_excel(sales_data)
            st.download_button(
                label="📥 تصدير المبيعات — Excel",
                data=excel_sales,
                file_name=f"sales_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # تصدير CSV
            csv_sales = sales_data.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📄 تصدير المبيعات — CSV",
                data=csv_sales,
                file_name=f"sales_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("لا توجد مبيعات لتصديرها")

    # ── تقرير شامل ──────────────────────────────────────────
    st.markdown("---")
    section_header("التحليل التفصيلي", "📊")

    conn = get_connection()
    inv_data = get_all_devices(conn)
    sales_data = get_all_sales(conn)
    conn.close()

    if not inv_data.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**توزيع المخزن حسب الماركة**")
            brand_dist = inv_data.groupby('brand').size().reset_index(name='عدد')
            st.bar_chart(brand_dist.set_index('brand')['عدد'], color="#00d4ff")

        with col_b:
            if not sales_data.empty:
                st.markdown("**أعلى الموديلات مبيعاً**")
                top_models = sales_data.merge(
                    inv_data[['imei', 'model', 'brand']], on='imei', how='left'
                ).groupby('model').size().sort_values(ascending=False).head(8)
                st.bar_chart(top_models, color="#00ff88")

# ══════════════════════════════════════════════════════════════
# نقطة الدخول الرئيسية
# ══════════════════════════════════════════════════════════════
def main():
    # تهيئة قاعدة البيانات
    init_db()

    # تحميل CSS
    load_css()

    # الشريط الجانبي والتنقل
    current_page = render_sidebar()

    # توجيه الصفحات
    if current_page == "dashboard":
        page_dashboard()
    elif current_page == "inventory":
        page_inventory()
    elif current_page == "sales":
        page_sales()
    elif current_page == "search":
        page_search()
    elif current_page == "reports":
        page_reports()

if __name__ == "__main__":
    main()
# --- سطر 911: نقطة الدخول الرئيسية ---
def main():
    # 1. تهيئة قاعدة البيانات والـ CSS
    init_db()
    load_css()
    
    # 2. استدعاء الستارة الجانبية وحفظ الاختيار في متغير
    # تأكد أن دالة render_sidebar ترجع قيمة (return selected) في نهايتها
    current_page = render_sidebar() 
    
    # 3. توجيه الصفحات (المحرك)
    if current_page == "لوحة التحكم":
        page_dashboard()
    elif current_page == "المخزن":
        page_inventory()
    elif current_page == "المبيعات":
        page_sales() # الدالة اللي صلحنا فيها الـ Tabs والكاميرا
    elif current_page == "البحث الذكي":
        page_search()
    elif current_page == "التقارير":
        page_reports()

# سطر 933: تشغيل التطبيق
if __name__ == "__main__":
    main()