# =============================================================================
#  app.py  —  Mobile Store Management System
#  Entry point for the Streamlit application.
#  All page logic is delegated to dedicated modules.
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime

# ── Internal modules ──────────────────────────────────────────────────────────
from database import (
    get_connection,
    init_db,
)
from inventory import (
    load_inventory,
    add_device,
    update_device,
    delete_device,
)
from sales import (
    load_sales,
    record_sale,
    get_device_by_imei,
)
from reports import (
    sales_summary,
    inventory_summary,
    top_selling_models,
    low_stock_alert,
)

# ── Optional OCR (imported lazily inside the page to avoid hard dependency) ──
# easyocr is only used in page_sales(); the @st.cache_resource reader lives
# there so it is initialised once and never blocks other pages.


# =============================================================================
#  1.  CONFIGURATION & STYLING
# =============================================================================

def set_page_config() -> None:
    """Configure global Streamlit page settings."""
    st.set_page_config(
        page_title="Mobile Store Manager",
        page_icon="📱",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_custom_css() -> None:
    """Inject application-wide CSS overrides."""
    st.markdown(
        """
        <style>
            /* ── Sidebar ── */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            }
            [data-testid="stSidebar"] * {
                color: #e2e8f0 !important;
            }

            /* ── Radio menu items ── */
            div[role="radiogroup"] label {
                padding: 0.5rem 0.75rem;
                border-radius: 8px;
                transition: background 0.2s;
            }
            div[role="radiogroup"] label:hover {
                background: rgba(255,255,255,0.08);
            }

            /* ── Metric cards ── */
            [data-testid="stMetric"] {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 1rem 1.25rem;
            }

            /* ── Primary button ── */
            .stButton > button[kind="primary"] {
                background: #6366f1;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }
            .stButton > button[kind="primary"]:hover {
                background: #4f46e5;
            }

            /* ── Data tables ── */
            [data-testid="stDataFrame"] table {
                border-radius: 8px;
                overflow: hidden;
            }

            /* ── Section divider ── */
            hr { border-color: #e2e8f0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
#  2.  DATABASE INITIALISATION
# =============================================================================

def initialise_database() -> None:
    """
    Create all required tables if they do not yet exist.
    Wraps init_db() so a cold start never crashes the app.
    """
    try:
        init_db()
    except Exception as exc:
        st.error(f"⚠️ Database initialisation failed: {exc}")


# =============================================================================
#  3.  SIDEBAR
# =============================================================================

PAGES = {
    "🏠 لوحة التحكم":  "dashboard",
    "📦 المخزن":        "inventory",
    "💰 المبيعات":      "sales",
    "🔍 البحث الذكي":  "search",
    "📊 التقارير":      "reports",
}


def render_sidebar() -> str:
    """
    Render the navigation sidebar.

    Returns
    -------
    str
        Internal page key (e.g. 'dashboard', 'sales', …).
    """
    with st.sidebar:
        # ── Logo / brand ────────────────────────────────────────────────────
        st.markdown(
            "<h2 style='text-align:center; margin-bottom:0.25rem;'>📱</h2>"
            "<h3 style='text-align:center; margin-top:0; color:#a5b4fc;'>"
            "Mobile Store</h3>",
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Quick KPIs (safe – wrapped in try/except) ────────────────────────
        try:
            conn = get_connection()
            total_devices = pd.read_sql("SELECT COUNT(*) AS n FROM inventory", conn).iloc[0]["n"]
            today_sales   = pd.read_sql(
                "SELECT COUNT(*) AS n FROM sales WHERE DATE(sale_date) = DATE('now')",
                conn,
            ).iloc[0]["n"]
            conn.close()

            col1, col2 = st.columns(2)
            col1.metric("📦 أجهزة", int(total_devices))
            col2.metric("💳 مبيعات اليوم", int(today_sales))
        except Exception:
            # Tables may not exist yet on first run – silently skip.
            pass

        st.divider()

        # ── Navigation menu ──────────────────────────────────────────────────
        st.markdown("**القائمة الرئيسية**")
        choice_label = st.radio(
            label="",
            options=list(PAGES.keys()),
            label_visibility="collapsed",
        )

        st.divider()
        st.caption(f"📅 {date.today().strftime('%Y-%m-%d')}")

    return PAGES[choice_label]


# =============================================================================
#  4.  PAGE: DASHBOARD
# =============================================================================

def page_dashboard() -> None:
    """Render the main dashboard / overview page."""
    st.title("🏠 لوحة التحكم")
    st.markdown("مرحباً! إليك نظرة عامة على المتجر.")
    st.divider()

    try:
        inv_df   = load_inventory()
        sales_df = load_sales()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الأجهزة",   len(inv_df))
        c2.metric("إجمالي المبيعات",  len(sales_df))

        today = date.today().isoformat()
        sales_today = sales_df[sales_df["sale_date"].astype(str).str.startswith(today)] \
            if "sale_date" in sales_df.columns else pd.DataFrame()
        c3.metric("مبيعات اليوم", len(sales_today))

        revenue_today = sales_today["price"].sum() if "price" in sales_today.columns else 0
        c4.metric("إيراد اليوم (ج.م)", f"{revenue_today:,.0f}")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("⚠️ تنبيهات المخزون المنخفض")
            low = low_stock_alert()
            if low.empty:
                st.success("المخزون في مستوى جيد ✅")
            else:
                st.dataframe(low, use_container_width=True)

        with col_right:
            st.subheader("🏆 الموديلات الأكثر مبيعاً")
            top = top_selling_models()
            if top.empty:
                st.info("لا توجد بيانات مبيعات بعد.")
            else:
                st.dataframe(top, use_container_width=True)

    except Exception as exc:
        st.error(f"تعذّر تحميل بيانات لوحة التحكم: {exc}")


# =============================================================================
#  5.  PAGE: INVENTORY
# =============================================================================

def page_inventory() -> None:
    """Render the inventory management page."""
    st.title("📦 إدارة المخزن")
    st.divider()

    tab_view, tab_add, tab_edit = st.tabs(["📋 عرض المخزون", "➕ إضافة جهاز", "✏️ تعديل / حذف"])

    # ── View ─────────────────────────────────────────────────────────────────
    with tab_view:
        try:
            df = load_inventory()
            st.dataframe(df, use_container_width=True, height=420)
        except Exception as exc:
            st.error(f"تعذّر تحميل المخزون: {exc}")

    # ── Add ──────────────────────────────────────────────────────────────────
    with tab_add:
        with st.form("form_add_device", clear_on_submit=True):
            st.subheader("إضافة جهاز جديد")
            col1, col2 = st.columns(2)
            brand    = col1.text_input("الماركة *")
            model    = col2.text_input("الموديل *")
            imei     = st.text_input("رقم IMEI *", max_chars=15)
            col3, col4 = st.columns(2)
            cost     = col3.number_input("سعر الشراء (ج.م)", min_value=0.0, step=50.0)
            price    = col4.number_input("سعر البيع (ج.م)",  min_value=0.0, step=50.0)
            color    = col1.text_input("اللون")
            storage  = col2.text_input("السعة التخزينية")
            notes    = st.text_area("ملاحظات", height=80)

            submitted = st.form_submit_button("💾 حفظ الجهاز", type="primary")
            if submitted:
                if not brand or not model or not imei:
                    st.warning("الرجاء تعبئة الحقول الإلزامية (*).")
                else:
                    try:
                        add_device(
                            brand=brand, model=model, imei=imei,
                            cost=cost, price=price,
                            color=color, storage=storage, notes=notes,
                        )
                        st.success(f"✅ تم إضافة الجهاز {brand} {model} بنجاح!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"فشل الحفظ: {exc}")

    # ── Edit / Delete ─────────────────────────────────────────────────────────
    with tab_edit:
        try:
            df = load_inventory()
            if df.empty:
                st.info("لا توجد أجهزة في المخزون.")
            else:
                imei_sel = st.selectbox("اختر الجهاز بالـ IMEI", df["imei"].tolist())
                device   = df[df["imei"] == imei_sel].iloc[0]

                with st.form("form_edit_device"):
                    col1, col2 = st.columns(2)
                    new_price = col1.number_input("سعر البيع الجديد", value=float(device.get("price", 0)), step=50.0)
                    new_color = col2.text_input("اللون", value=str(device.get("color", "")))
                    new_notes = st.text_area("ملاحظات", value=str(device.get("notes", "")), height=80)

                    col_upd, col_del = st.columns(2)
                    update_btn = col_upd.form_submit_button("✏️ تحديث", type="primary")
                    delete_btn = col_del.form_submit_button("🗑️ حذف",  type="secondary")

                if update_btn:
                    try:
                        update_device(imei_sel, price=new_price, color=new_color, notes=new_notes)
                        st.success("✅ تم التحديث بنجاح!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"فشل التحديث: {exc}")

                if delete_btn:
                    try:
                        delete_device(imei_sel)
                        st.success("🗑️ تم الحذف بنجاح!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"فشل الحذف: {exc}")

        except Exception as exc:
            st.error(f"تعذّر تحميل الأجهزة: {exc}")


# =============================================================================
#  6.  PAGE: SALES
# =============================================================================

@st.cache_resource
def _get_ocr_reader():
    """
    Initialise EasyOCR reader once per session.
    Cached via @st.cache_resource so it is never re-loaded on re-runs.
    """
    import easyocr  # noqa: PLC0415 – lazy import to avoid hard dependency
    return easyocr.Reader(["en"], gpu=False)


def _extract_imei_from_image(image_bytes: bytes) -> str:
    """
    Run EasyOCR on *image_bytes* and return the first 15-digit number found,
    or an empty string if nothing is detected.
    """
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    import io

    reader  = _get_ocr_reader()
    img     = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    np_img  = np.array(img)
    results = reader.readtext(np_img, detail=0)

    for text in results:
        digits = "".join(filter(str.isdigit, text))
        if len(digits) == 15:
            return digits
    return ""


def page_sales() -> None:
    """Render the sales / point-of-sale page."""
    st.title("💰 تسجيل عملية بيع")
    st.divider()

    # ── Session state for IMEI ────────────────────────────────────────────────
    if "scanned_imei" not in st.session_state:
        st.session_state["scanned_imei"] = ""

    col_cam, col_form = st.columns([1, 1], gap="large")

    # ── Camera / OCR column ───────────────────────────────────────────────────
    with col_cam:
        st.subheader("📷 مسح الـ IMEI")
        camera_image = st.camera_input("صوّر ملصق الـ IMEI أو الجهاز")

        if camera_image is not None:
            with st.spinner("🔍 جاري معالجة الصورة…"):
                try:
                    detected = _extract_imei_from_image(camera_image.getvalue())
                    if detected:
                        st.session_state["scanned_imei"] = detected
                        st.success(f"✅ تم اكتشاف IMEI: **{detected}**")
                    else:
                        st.warning("⚠️ لم يتم اكتشاف رقم IMEI – يمكنك إدخاله يدوياً.")
                except Exception as exc:
                    st.error(f"خطأ في معالجة الصورة: {exc}")

        manual = st.text_input(
            "أو أدخل الـ IMEI يدوياً",
            value=st.session_state["scanned_imei"],
            max_chars=15,
            key="manual_imei_input",
        )
        if manual:
            st.session_state["scanned_imei"] = manual

    # ── Sale form column ──────────────────────────────────────────────────────
    with col_form:
        st.subheader("📝 تفاصيل عملية البيع")

        current_imei = st.session_state["scanned_imei"]

        # Try to prefill from inventory
        device_info = {}
        if current_imei:
            try:
                device_info = get_device_by_imei(current_imei) or {}
            except Exception:
                pass

        with st.form("form_sale", clear_on_submit=False):
            imei_display = st.text_input(
                "IMEI",
                value=current_imei,
                disabled=bool(current_imei),
            )
            col1, col2 = st.columns(2)
            brand = col1.text_input("الماركة",  value=device_info.get("brand", ""))
            model = col2.text_input("الموديل", value=device_info.get("model", ""))
            col3, col4 = st.columns(2)
            sale_price = col3.number_input(
                "سعر البيع (ج.م)",
                value=float(device_info.get("price", 0.0)),
                min_value=0.0,
                step=50.0,
            )
            payment = col4.selectbox("طريقة الدفع", ["كاش", "تحويل بنكي", "فيزا", "تقسيط"])
            customer_name  = st.text_input("اسم العميل (اختياري)")
            customer_phone = st.text_input("رقم هاتف العميل (اختياري)")
            sale_notes     = st.text_area("ملاحظات", height=70)

            confirm = st.form_submit_button("✅ تأكيد البيع", type="primary", use_container_width=True)

        if confirm:
            if not imei_display:
                st.warning("الرجاء إدخال رقم IMEI أولاً.")
            else:
                try:
                    record_sale(
                        imei=imei_display,
                        brand=brand,
                        model=model,
                        sale_price=sale_price,
                        payment_method=payment,
                        customer_name=customer_name,
                        customer_phone=customer_phone,
                        notes=sale_notes,
                        sale_date=datetime.now().isoformat(),
                    )
                    st.success(f"🎉 تم تسجيل البيع بنجاح! IMEI: {imei_display}")
                    st.session_state["scanned_imei"] = ""
                    st.rerun()
                except Exception as exc:
                    st.error(f"فشل تسجيل البيع: {exc}")

    # ── Recent sales table ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🕐 آخر المبيعات")
    try:
        recent = load_sales().tail(10).iloc[::-1]
        st.dataframe(recent, use_container_width=True)
    except Exception as exc:
        st.error(f"تعذّر تحميل المبيعات الأخيرة: {exc}")


# =============================================================================
#  7.  PAGE: SMART SEARCH
# =============================================================================

def page_search() -> None:
    """Render the smart search page."""
    st.title("🔍 البحث الذكي")
    st.divider()

    query = st.text_input("ابحث بالـ IMEI أو الماركة أو الموديل أو اللون…", placeholder="مثال: iPhone 14 أو 358…")

    if query:
        try:
            inv_df   = load_inventory()
            sales_df = load_sales()

            mask_inv = inv_df.apply(
                lambda row: row.astype(str).str.contains(query, case=False, na=False).any(),
                axis=1,
            )
            mask_sal = sales_df.apply(
                lambda row: row.astype(str).str.contains(query, case=False, na=False).any(),
                axis=1,
            )

            st.subheader(f"نتائج المخزون ({mask_inv.sum()})")
            if mask_inv.any():
                st.dataframe(inv_df[mask_inv], use_container_width=True)
            else:
                st.info("لا توجد نتائج في المخزون.")

            st.subheader(f"نتائج المبيعات ({mask_sal.sum()})")
            if mask_sal.any():
                st.dataframe(sales_df[mask_sal], use_container_width=True)
            else:
                st.info("لا توجد نتائج في المبيعات.")

        except Exception as exc:
            st.error(f"خطأ في البحث: {exc}")


# =============================================================================
#  8.  PAGE: REPORTS
# =============================================================================

def page_reports() -> None:
    """Render the reports & analytics page."""
    st.title("📊 التقارير والإحصاءات")
    st.divider()

    tab_sales, tab_inv, tab_top = st.tabs(["💰 تقرير المبيعات", "📦 تقرير المخزون", "🏆 الأكثر مبيعاً"])

    with tab_sales:
        try:
            df = sales_summary()
            if df.empty:
                st.info("لا توجد بيانات مبيعات بعد.")
            else:
                st.dataframe(df, use_container_width=True)
                if "revenue" in df.columns:
                    st.bar_chart(df.set_index(df.columns[0])["revenue"])
        except Exception as exc:
            st.error(f"تعذّر تحميل تقرير المبيعات: {exc}")

    with tab_inv:
        try:
            df = inventory_summary()
            if df.empty:
                st.info("لا توجد بيانات مخزون بعد.")
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as exc:
            st.error(f"تعذّر تحميل تقرير المخزون: {exc}")

    with tab_top:
        try:
            df = top_selling_models()
            if df.empty:
                st.info("لا توجد بيانات كافية.")
            else:
                st.dataframe(df, use_container_width=True)
                if "count" in df.columns:
                    st.bar_chart(df.set_index(df.columns[0])["count"])
        except Exception as exc:
            st.error(f"تعذّر تحميل تقرير الأكثر مبيعاً: {exc}")


# =============================================================================
#  9.  MAIN — Application entry point
# =============================================================================

def main() -> None:
    """
    Main application driver.

    Execution order
    ---------------
    1. Page config  (must be the very first Streamlit call)
    2. CSS injection
    3. Database initialisation
    4. Sidebar render  →  returns current page key
    5. Page routing   →  delegates to the appropriate page function
    """
    # ── 1. Config & styling ──────────────────────────────────────────────────
    set_page_config()
    inject_custom_css()

    # ── 2. Database ──────────────────────────────────────────────────────────
    initialise_database()

    # ── 3. Sidebar / navigation ──────────────────────────────────────────────
    current_page = render_sidebar()

    # ── 4. Page routing ──────────────────────────────────────────────────────
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
    else:
        st.error(f"صفحة غير معروفة: {current_page}")


# =============================================================================
if __name__ == "__main__":
    main()
