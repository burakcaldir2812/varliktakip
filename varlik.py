import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import streamlit.components.v1 as components 

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Asset Report", page_icon="📊", layout="wide")

# GOOGLE SHEET NAME
SHEET_NAME = "Varlık Takip Verileri"

# --- GOOGLE SHEETS CONNECTION ---
def get_sheet_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

# --- COLOR PALETTE ---
COLORS = {
    "Garanti Bankası": "#2ecc71", "Akbank": "#e74c3c", "Midas": "#3498db",
    "IBKR": "#c0392b", "Binance": "#f1c40f", "Quantfury": "#00a8ff",
    "Osmanlı Yatırım": "#95a5a6", "BoFA": "#00205b", "Chase": "#117aca",
    "Sofi": "#00d5e6", "Mercury": "#333333", "Cash": "#2c3e50",
    "BES": "#e67e22", "Other": "#7f8c8d"
}

INSTITUTIONS = [
    "Garanti Bankası", "Akbank", "Midas", "IBKR", 
    "Binance", "Quantfury", "Osmanlı Yatırım",
    "BoFA", "Chase", "Sofi", "Mercury"
]

# --- SESSION STATE ---
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    for k in INSTITUTIONS:
        if f"tl_{k}" not in st.session_state: st.session_state[f"tl_{k}"] = None
        if f"usd_{k}" not in st.session_state: st.session_state[f"usd_{k}"] = None
    for i in range(1, 3):
        if f"tl_extra_{i}" not in st.session_state: st.session_state[f"tl_extra_{i}"] = None
        if f"usd_extra_{i}" not in st.session_state: st.session_state[f"usd_extra_{i}"] = None
    if "tl_bes" not in st.session_state: st.session_state.tl_bes = None
    if "usd_bes" not in st.session_state: st.session_state.usd_bes = None

# --- FUNCTIONS ---
def load_data():
    try:
        sheet = get_sheet_data()
        records = sheet.get_all_records()
        if not records:
             return pd.DataFrame(columns=["Date", "Institution", "TL Amount", "USD Amount", "USD Rate"])
        return pd.DataFrame(records)
    except:
        return pd.DataFrame(columns=["Date", "Institution", "TL Amount", "USD Amount", "USD Rate"])

def save_data_to_sheet(new_records):
    sheet = get_sheet_data()
    existing_data = sheet.get_all_records()
    df_existing = pd.DataFrame(existing_data)
    df_new = pd.DataFrame(new_records)
    
    if not df_existing.empty:
        target_date = new_records[0]["Date"]
        df_existing = df_existing[df_existing["Date"] != target_date]
        
    df_final = pd.concat([df_existing, df_new], ignore_index=True)
    sheet.clear()
    sheet.append_row(df_final.columns.tolist())
    sheet.append_rows(df_final.values.tolist())

def clear_inputs():
    for k in INSTITUTIONS:
        st.session_state[f"tl_{k}"] = None
        st.session_state[f"usd_{k}"] = None
    for i in range(1, 3):
        st.session_state[f"tl_extra_{i}"] = None
        st.session_state[f"usd_extra_{i}"] = None
    st.session_state.tl_bes = None
    st.session_state.usd_bes = None

# --- TRIGGERS ---
def rate_changed():
    new_rate = st.session_state.usd_rate_input
    if new_rate > 0:
        for k in INSTITUTIONS:
            tl_val = st.session_state.get(f"tl_{k}")
            if tl_val is not None: st.session_state[f"usd_{k}"] = tl_val / new_rate
        for i in range(1, 3):
            tl_val = st.session_state.get(f"tl_extra_{i}")
            if tl_val is not None: st.session_state[f"usd_extra_{i}"] = tl_val / new_rate
        tl_bes = st.session_state.get("tl_bes")
        if tl_bes is not None: st.session_state.usd_bes = tl_bes / new_rate

def tl_changed(key_base):
    rate = st.session_state.usd_rate_input
    tl_val = st.session_state[f"tl_{key_base}"]
    if tl_val is not None and rate > 0: st.session_state[f"usd_{key_base}"] = tl_val / rate
    else: st.session_state[f"usd_{key_base}"] = None

def usd_changed(key_base):
    rate = st.session_state.usd_rate_input
    usd_val = st.session_state[f"usd_{key_base}"]
    if usd_val is not None: st.session_state[f"tl_{key_base}"] = usd_val * rate
    else: st.session_state[f"tl_{key_base}"] = None

def tl_bes_changed():
    rate = st.session_state.usd_rate_input
    tl_val = st.session_state.tl_bes
    if tl_val is not None and rate > 0: st.session_state.usd_bes = tl_val / rate
    else: st.session_state.usd_bes = None

def usd_bes_changed():
    rate = st.session_state.usd_rate_input
    usd_val = st.session_state.usd_bes
    if usd_val is not None: st.session_state.tl_bes = usd_val * rate
    else: st.session_state.tl_bes = None

# --- SAVE BUTTON LOGIC (FIXED CALCULATION) ---
def save_and_clear(selected_date):
    rate = st.session_state.usd_rate_input
    new_records = []
    date_str = pd.to_datetime(selected_date).strftime('%Y-%m-%d')
    
    # --- HELPER TO CALCULATE VALUES CORRECTLY ---
    def get_final_values(tl_key, usd_key):
        raw_tl = st.session_state.get(tl_key)
        raw_usd = st.session_state.get(usd_key)
        
        final_tl = 0
        final_usd = 0
        
        # Priority: If TL exists, use it. If not, use USD and convert.
        if raw_tl is not None and raw_tl > 0:
            final_tl = raw_tl
            final_usd = raw_tl / rate if rate > 0 else 0
        elif raw_usd is not None and raw_usd > 0:
            final_tl = raw_usd * rate
            final_usd = raw_usd
            
        return final_tl, final_usd

    # 1. Main Institutions
    for k in INSTITUTIONS:
        f_tl, f_usd = get_final_values(f"tl_{k}", f"usd_{k}")
        if f_tl > 0:
            new_records.append({"Date": date_str, "Institution": k, "TL Amount": f_tl, "USD Amount": f_usd, "USD Rate": rate})
    
    # 2. Extras
    for i in range(1, 3):
        name = st.session_state.get(f"name_extra_{i}")
        f_tl, f_usd = get_final_values(f"tl_extra_{i}", f"usd_extra_{i}")
        if name and f_tl > 0:
            new_records.append({"Date": date_str, "Institution": name, "TL Amount": f_tl, "USD Amount": f_usd, "USD Rate": rate})

    # 3. BES
    f_tl_bes, f_usd_bes = get_final_values("tl_bes", "usd_bes")
    if f_tl_bes > 0:
        new_records.append({"Date": date_str, "Institution": "BES", "TL Amount": f_tl_bes, "USD Amount": f_usd_bes, "USD Rate": rate})

    if new_records:
        save_data_to_sheet(new_records)
        st.success("✅ Saved to Google Sheets!")
    clear_inputs()

# --- UI STARTS ---
st.title("📊 Visual Asset Report (Cloud)")

with st.expander("➕ New Entry / Edit", expanded=False):
    c1, c2 = st.columns(2)
    selected_date = c1.date_input("Date", datetime.now())
    usd_rate = c2.number_input("USD/TRY Rate", value=35.0, step=0.1, key="usd_rate_input", on_change=rate_changed)
    
    st.markdown("---")
    st.write("###### Main Assets")
    for inst in INSTITUTIONS:
        c_name, c_tl, c_usd = st.columns([1.5, 1.5, 1.5])
        c_name.write(f"**{inst}**")
        c_tl.number_input("TL", key=f"tl_{inst}", on_change=tl_changed, args=(inst,), step=1000.0, value=None, placeholder="0", label_visibility="collapsed")
        c_usd.number_input("USD", key=f"usd_{inst}", on_change=usd_changed, args=(inst,), step=100.0, value=None, placeholder="0", label_visibility="collapsed")
    
    st.markdown("---")
    st.write("###### Extra Assets")
    for i in range(1, 3):
        ec_name, ec_tl, ec_usd = st.columns([1.5, 1.5, 1.5])
        ec_name.text_input(f"Name {i}", key=f"name_extra_{i}", placeholder="e.g. Home / Gold", label_visibility="collapsed")
        ec_tl.number_input("TL", key=f"tl_extra_{i}", on_change=tl_changed, args=(f"extra_{i}",), value=None, placeholder="0", label_visibility="collapsed")
        ec_usd.number_input("USD", key=f"usd_extra_{i}", on_change=usd_changed, args=(f"extra_{i}",), value=None, placeholder="0", label_visibility="collapsed")

    st.markdown("---")
    st.write("###### ☂️ Private Pension (BES)")
    c_bes_label, c_bes_tl, c_bes_usd = st.columns([1.5, 1.5, 1.5])
    c_bes_label.write("**BES**")
    c_bes_tl.number_input("TL", key="tl_bes", on_change=tl_bes_changed, step=1000.0, value=None, placeholder="0", label_visibility="collapsed")
    c_bes_usd.number_input("USD", key="usd_bes", on_change=usd_bes_changed, step=100.0, value=None, placeholder="0", label_visibility="collapsed")

    st.markdown("---")
    st.button("💾 SAVE THIS MONTH", type="primary", use_container_width=True, on_click=save_and_clear, args=(selected_date,))

# --- CHART AREA ---
st.markdown("---")
df = load_data()

if not df.empty:
    df_main = df[df["Institution"] != "BES"]
    df_bes = df[df["Institution"] == "BES"]

    st.subheader("📈 Main Asset Growth")
    if not df_main.empty:
        daily_summary = df_main.groupby("Date")[["TL Amount", "USD Amount"]].sum().reset_index()
        tab_g1, tab_g2 = st.tabs(["₺ TL Base", "$ USD Base"])
        
        with tab_g1:
            fig_tl = px.bar(daily_summary, x="Date", y="TL Amount", color="Date", title="Total Liquid Assets (TL)", template="plotly_white")
            fig_tl.update_traces(texttemplate='<b>₺%{y:,.0f}</b>', textposition='outside', marker_line_width=1.5, marker_line_color="black")
            fig_tl.update_layout(xaxis_title="", yaxis_title="Amount (TL)", font=dict(size=12), height=400, showlegend=False)
            st.plotly_chart(fig_tl, use_container_width=True)
            
        with tab_g2:
            fig_usd = px.bar(daily_summary, x="Date", y="USD Amount", color="Date", title="Total Liquid Assets (USD)", template="plotly_white")
            fig_usd.update_traces(texttemplate='<b>$%{y:,.0f}</b>', textposition='outside', marker_line_width=1.5, marker_line_color="black")
            fig_usd.update_layout(xaxis_title="", yaxis_title="Amount ($)", font=dict(size=12), height=400, showlegend=False)
            st.plotly_chart(fig_usd, use_container_width=True)
    else:
        st.info("No main assets data.")

    if not df_bes.empty:
        st.markdown("---")
        st.subheader("☂️ BES (Pension) Monthly Tracking")
        daily_summary_bes = df_bes.groupby("Date")[["TL Amount", "USD Amount"]].sum().reset_index()
        tab_b1, tab_b2 = st.tabs(["₺ BES (TL)", "$ BES (USD)"])
        
        with tab_b1:
            fig_bes_tl = px.bar(daily_summary_bes, x="Date", y="TL Amount", title="BES Growth (TL)", template="plotly_white", color_discrete_sequence=["#e67e22"])
            fig_bes_tl.update_traces(texttemplate='<b>₺%{y:,.0f}</b>', textposition='outside', marker_line_width=1.5, marker_line_color="black")
            fig_bes_tl.update_layout(xaxis_title="", yaxis_title="TL", height=400)
            st.plotly_chart(fig_bes_tl, use_container_width=True)

        with tab_b2:
            fig_bes_usd = px.bar(daily_summary_bes, x="Date", y="USD Amount", title="BES Growth (USD)", template="plotly_white", color_discrete_sequence=["#d35400"])
            fig_bes_usd.update_traces(texttemplate='<b>$%{y:,.0f}</b>', textposition='outside', marker_line_width=1.5, marker_line_color="black")
            fig_bes_usd.update_layout(xaxis_title="", yaxis_title="USD", height=400)
            st.plotly_chart(fig_bes_usd, use_container_width=True)

# --- 3. REPORT CARDS ---
st.markdown("### 📋 Monthly Detail Cards")
if not df.empty:
    unique_dates = sorted(df["Date"].unique())
    cols = st.columns(5) 
    for idx, date_str in enumerate(unique_dates):
        col_index = idx % 5
        df_month = df[df["Date"] == date_str]
        df_month_main = df_month[df_month["Institution"] != "BES"]
        df_month_bes = df_month[df_month["Institution"] == "BES"]
        
        dt_obj = datetime.strptime(date_str, '%Y-%m-%d')
        months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
        date_header = f"1 {months[dt_obj.month-1]} {dt_obj.year}"
        
        total_tl = df_month_main["TL Amount"].sum()
        total_usd = df_month_main["USD Amount"].sum()
        bes_tl = df_month_bes["TL Amount"].sum() if not df_month_bes.empty else 0
        bes_usd = df_month_bes["USD Amount"].sum() if not df_month_bes.empty else 0

        if "USD Rate" in df_month.columns and not pd.isna(df_month["USD Rate"].iloc[0]): current_rate = df_month["USD Rate"].iloc[0]
        else: current_rate = total_tl / total_usd if total_usd > 0 else 0

        html_content = f"""
        <div style="border: 1px solid #ccc; margin-bottom: 20px; font-family: sans-serif; font-size: 12px; background-color: white; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
            <div style="background-color: white; color: black; font-weight: bold; text-align: center; padding: 6px; border-bottom: 1px solid #000; font-size: 14px;">{date_header}</div>
            <table style="width: 100%; border-collapse: collapse;">
        """
        for _, row in df_month_main.iterrows():
            inst_name = row['Institution']
            amount = f"{row['TL Amount']:,.0f}"
            color = COLORS.get(inst_name, "#95a5a6")
            text_color = "black" if color == "#f1c40f" else "white"
            html_content += f"""<tr style="border-bottom: 1px solid #eee;"><td style="background-color: {color}; color: {text_color}; padding: 4px; font-weight: bold; width: 50%; font-size: 11px;">{inst_name.upper()}</td><td style="text-align: right; padding: 4px; background-color: white; color: black; font-size: 11px;">{amount}</td></tr>"""
        
        html_content += f"""<tr><td colspan="2" style="height: 5px; border-top: 1px solid #000;"></td></tr><tr><td style="font-weight: bold; color: red; padding: 4px; font-size: 12px;">TOTAL (TL)</td><td style="text-align: right; font-weight: bold; color: red; padding: 4px; background-color: #f0f0f0; font-size: 12px;">{total_tl:,.0f}</td></tr><tr><td style="font-weight: bold; padding: 4px; border-bottom: 1px solid #000; font-size: 11px;">RATE: {current_rate:.1f}</td><td style="text-align: right; font-weight: bold; color: green; padding: 4px; background-color: #e8f8f5; border-bottom: 1px solid #000; font-size: 12px;">${total_usd:,.0f}</td></tr>"""
        
        if bes_tl > 0:
            html_content += f"""<tr><td colspan="2" style="height: 2px;"></td></tr><tr><td style="background-color: #e67e22; color: white; padding: 4px; font-weight: bold; font-size: 11px;">BES (PENSION)</td><td style="text-align: right; padding: 4px; background-color: #fcf3cf; color: #d35400; font-weight: bold; font-size: 11px;">{bes_tl:,.0f} / ${bes_usd:,.0f}</td></tr>"""

        html_content += "</table></div>"
        with cols[col_index]: components.html(html_content, height=500, scrolling=True)

    st.markdown("---")
    with st.expander("🗑️ Delete Incorrect Entry"):
        date_to_delete = st.selectbox("Select date to delete:", unique_dates)
        if st.button("🗑️ Delete Selected Date", type="primary"):
            sheet = get_sheet_data()
            all_records = sheet.get_all_records()
            df_cloud = pd.DataFrame(all_records)
            date_str_del = pd.to_datetime(date_to_delete).strftime('%Y-%m-%d')
            df_cloud = df_cloud[df_cloud["Date"] != date_str_del]
            sheet.clear()
            sheet.append_row(df_cloud.columns.tolist())
            sheet.append_rows(df_cloud.values.tolist())
            st.success("Deleted from Cloud! Refreshing...")
            st.rerun()
else: st.info("No data yet.")