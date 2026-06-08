import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sqlalchemy import create_engine

# Database Connection config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/clv_db")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Setup database helper for fast queries
@st.cache_resource
def get_db_engine():
    try:
        engine = create_engine(DATABASE_URL)
        # Check connection
        with engine.connect() as conn:
            pass
        return engine, False
    except Exception as e:
        # Fallback to local SQLite if Postgres is unavailable
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sqlite_db_path = os.path.join(PROJECT_ROOT, "outputs", "local_platform.db")
        fallback_url = f"sqlite:///{sqlite_db_path}"
        engine = create_engine(fallback_url)
        return engine, True

engine, is_sqlite = get_db_engine()

# --- Page Config ---
st.set_page_config(
    page_title="SaaS CLV Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling: Premium modern HSL styling with soft colors, card designs, and gradients
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Background Gradients */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(246, 249, 252, 1) 0%, rgba(239, 244, 249, 1) 90.1%);
    }
    
    /* KPI Card styling */
    .kpi-card {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        backdrop-filter: blur(10px);
        margin-bottom: 15px;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }
    .kpi-label {
        font-size: 14px;
        font-weight: 600;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: #1A365D;
    }
    .kpi-trend {
        font-size: 12px;
        font-weight: 600;
        margin-top: 8px;
    }
    .trend-up { color: #38A169; }
    .trend-neutral { color: #4A5568; }
    
    /* Title styling */
    .dashboard-title {
        background: linear-gradient(135deg, #1A365D 0%, #2B6CB0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 38px;
        margin-bottom: 5px;
    }
    
    /* Tier styling */
    .tier-badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
    }
    .tier-platinum { background-color: #E2E8F0; color: #4A5568; border: 1px solid #CBD5E0; }
    .tier-gold { background-color: #FEFCBF; color: #B7791F; border: 1px solid #F6E05E; }
    .tier-silver { background-color: #E2E8F0; color: #4A5568; }
    .tier-bronze { background-color: #FFD2D2; color: #9B2C2C; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State for Authentication
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

def api_request(method, endpoint, headers=None, **kwargs):
    """Utility helper to make authenticated HTTP calls to API."""
    url = f"{API_URL}{endpoint}"
    if not headers:
        headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    try:
        response = requests.request(method, url, headers=headers, timeout=120, **kwargs)
        return response
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return None

# --- AUTHENTICATION SCREEN ---
if not st.session_state.access_token:
    st.write("")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #1A365D;'>SaaS CLV Analytics login</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #718096;'>Log in using your JWT credentials</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email Address", value="admin@clv.com")
            password = st.text_input("Password", type="password", value="admin123")
            submitted = st.form_submit_form("Sign In")
            
            if submitted:
                # Call Token endpoint
                resp = api_request("POST", "/api/v1/auth/token", json={"email": email, "password": password})
                if resp and resp.status_code == 200:
                    data = resp.json()
                    st.session_state.access_token = data["access_token"]
                    st.session_state.user_role = data["role"]
                    st.session_state.user_email = email
                    st.success("Successfully logged in!")
                    st.rerun()
                else:
                    st.error("Invalid email or password. Please try again.")
    st.stop()

# --- SIDEBAR LOGOUT & USER INFO ---
with st.sidebar:
    st.markdown(f"**Logged in as:** `{st.session_state.user_email}`")
    st.markdown(f"**Role:** `{st.session_state.user_role}`")
    if st.button("Log Out"):
        st.session_state.access_token = None
        st.session_state.user_role = None
        st.session_state.user_email = None
        st.rerun()
    st.markdown("---")

# --- MULTI-PAGE ROUTING ---
page = st.sidebar.radio(
    "Navigation Menu",
    ["Executive Dashboard", "Customer Explorer", "Advanced Analytics", "Top Customer Directory", "Data & Operations Management"]
)

# Fetch global metrics for rendering dashboards
def query_db(query, params=None):
    try:
        return pd.read_sql(query, engine, params=params)
    except Exception as e:
        st.error(f"Database Query Error: {e}")
        return pd.DataFrame()

# -------------------------------------------------------------
# PAGE 1: EXECUTIVE DASHBOARD
# -------------------------------------------------------------
if page == "Executive Dashboard":
    st.markdown("<h1 class='dashboard-title'>Executive CLV Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #4A5568;'>Summary metrics and customer portfolio values</p>", unsafe_allow_html=True)
    st.write("")

    # Query metrics
    cust_count_df = query_db("SELECT COUNT(*) as cnt FROM customers")
    total_customers = cust_count_df["cnt"].iloc[0] if not cust_count_df.empty else 0

    pred_stats_df = query_db("""
        SELECT 
            AVG(predicted_clv_6months) as avg_clv, 
            SUM(predicted_clv_6months) as total_revenue,
            AVG(churn_risk_score) as avg_churn
        FROM customer_clv_predictions
    """)
    
    avg_clv = pred_stats_df["avg_clv"].iloc[0] or 0.0 if not pred_stats_df.empty else 0.0
    total_revenue = pred_stats_df["total_revenue"].iloc[0] or 0.0 if not pred_stats_df.empty else 0.0
    avg_churn = pred_stats_df["avg_churn"].iloc[0] or 0.0 if not pred_stats_df.empty else 0.0

    # Churn risk summary
    churn_df = query_db("""
        SELECT churn_risk_tier, COUNT(*) as cnt 
        FROM customer_clv_predictions 
        GROUP BY churn_risk_tier
    """)
    churn_counts = {row["churn_risk_tier"]: row["cnt"] for _, row in churn_df.iterrows()}

    # Render KPI Cards in a grid
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>Total Customers</div>
            <div class='kpi-value'>{total_customers:,}</div>
            <div class='kpi-trend trend-up'>🟢 Portfolio Active</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>Avg 6-Month CLV</div>
            <div class='kpi-value'>£{avg_clv:.2f}</div>
            <div class='kpi-trend trend-up'>📈 Target Value</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>Predicted Revenue (6m)</div>
            <div class='kpi-value'>£{total_revenue:,.2f}</div>
            <div class='kpi-trend trend-up'>💰 Pipeline Value</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>Avg Churn Risk</div>
            <div class='kpi-value'>{avg_churn*100:.1f}%</div>
            <div class='kpi-trend trend-neutral'>⚠️ Portfolio Risk</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.subheader("Strategic CLV Tier Distribution")
        # Query segment counts
        seg_counts_df = query_db("""
            SELECT recommendation_tier, COUNT(*) as customer_count, AVG(predicted_clv_6months) as avg_value
            FROM customer_clv_predictions
            GROUP BY recommendation_tier
        """)
        
        if not seg_counts_df.empty:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            colors_list = ["#E2E8F0", "#ECC94B", "#CBD5E0", "#FEB2B2"] # Platinum, Gold, Silver, Bronze matches
            # Let's map values cleanly
            sns.barplot(x="recommendation_tier", y="customer_count", data=seg_counts_df, palette="Blues_d", ax=ax)
            ax.set_xlabel("CLV Tiers")
            ax.set_ylabel("Customers")
            ax.set_title("Customer Share per Strategic Tier")
            st.pyplot(fig)
        else:
            st.info("No predictions found in the database. Run predictions refresh in Data Management page.")

    with col_right:
        st.subheader("Churn Risk Breakdown")
        if churn_counts:
            fig, ax = plt.subplots(figsize=(5, 5))
            labels = list(churn_counts.keys())
            sizes = list(churn_counts.values())
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=["#3182CE", "#ED8936", "#E53E3E"])
            ax.axis('equal')
            st.pyplot(fig)
        else:
            st.info("No churn risk counts available.")

# -------------------------------------------------------------
# PAGE 2: CUSTOMER EXPLORER
# -------------------------------------------------------------
elif page == "Customer Explorer":
    st.markdown("<h1 class='dashboard-title'>Customer Profile Explorer</h1>", unsafe_allow_html=True)
    st.write("")
    
    search_id = st.text_input("Enter Customer ID to search:", value="18139")
    
    if search_id:
        # Fetch profile from FastAPI (secure, handles recommendations on-the-fly)
        resp = api_request("GET", f"/api/v1/customers/{search_id}")
        if resp and resp.status_code == 200:
            profile = resp.json()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Customer ID:** `{profile['customer_id']}`")
                st.markdown(f"**Country:** `{profile['country']}`")
            with c2:
                tier = profile.get('recommendation_tier', 'Bronze')
                st.markdown(f"**CLV Strategic Tier:** `{tier}`")
                st.markdown(f"**Predicted 6-Month CLV:** `£{profile.get('predicted_clv_6months') or 0.0:.2f}`")
            with c3:
                st.markdown(f"**Expected Purchases (6m):** `{profile.get('expected_purchases_6m') or 0.0:.1f}`")
                st.markdown(f"**Churn Risk Level:** `{profile.get('churn_risk_tier') or 'Medium'} ({profile.get('churn_risk_score', 0.5)*100:.1f}%)`")
                
            st.write("")
            st.subheader("Actionable Business Recommendation")
            st.info(profile.get("recommendation_details") or "N/A")
            
            st.write("")
            st.subheader("Customer Transaction History")
            txns_list = profile.get("transactions", [])
            if txns_list:
                df_tx = pd.DataFrame(txns_list)
                df_tx["invoice_date"] = pd.to_datetime(df_tx["invoice_date"])
                st.dataframe(df_tx[["invoice_no", "stock_code", "description", "quantity", "price", "invoice_date", "revenue"]])
            else:
                st.warning("No transactions found for this customer.")
        else:
            st.error("Customer ID not found in database.")

# -------------------------------------------------------------
# PAGE 3: ADVANCED ANALYTICS
# -------------------------------------------------------------
elif page == "Advanced Analytics":
    st.markdown("<h1 class='dashboard-title'>Advanced Portfolio Analytics</h1>", unsafe_allow_html=True)
    st.write("")
    
    # Let's show CLV distribution plot
    clv_dist = query_db("SELECT predicted_clv_6months FROM customer_clv_predictions")
    if not clv_dist.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.histplot(clv_dist["predicted_clv_6months"], bins=50, kde=True, ax=ax, color="#2B6CB0")
        ax.set_title("Customer Lifetime Value (6-Month Horizon) Distribution")
        ax.set_xlabel("Predicted CLV (GBP)")
        ax.set_xlim(0, float(clv_dist["predicted_clv_6months"].quantile(0.95))) # cap at 95th percentile for chart clarity
        st.pyplot(fig)
    else:
        st.info("No CLV prediction data available.")

    # RFM Segment behaviors
    st.subheader("RFM Feature Tiers Performance")
    rfm_segments = query_db("""
        SELECT segment_name, AVG(recency) as avg_recency, AVG(frequency) as avg_frequency, AVG(monetary) as avg_monetary
        FROM customer_segments
        GROUP BY segment_name
    """)
    if not rfm_segments.empty:
        st.dataframe(rfm_segments.rename(columns={
            "segment_name": "CLV Segment",
            "avg_recency": "Avg Recency (days)",
            "avg_frequency": "Avg Frequency (repeat txns)",
            "avg_monetary": "Avg Monetary (mean purchase value)"
        }))
    else:
        st.info("No segment analysis records exist in database.")

# -------------------------------------------------------------
# PAGE 4: TOP CUSTOMER DIRECTORY
# -------------------------------------------------------------
elif page == "Top Customer Directory":
    st.markdown("<h1 class='dashboard-title'>Top Customers Strategic Directory</h1>", unsafe_allow_html=True)
    st.write("")
    
    st.subheader("Top Spenders (Predicted highest 6-Month CLV)")
    top_custs = query_db("""
        SELECT customer_id, predicted_clv_6months, churn_risk_score, churn_risk_tier, recommendation_tier 
        FROM customer_clv_predictions 
        ORDER BY predicted_clv_6months DESC 
        LIMIT 50
    """)
    if not top_custs.empty:
        st.dataframe(top_custs)
    else:
        st.info("No predictions found. Refresh prediction database.")

    st.subheader("High-Value Customers At Churn Risk")
    at_risk = query_db("""
        SELECT customer_id, predicted_clv_6months, churn_risk_score, recommendation_tier 
        FROM customer_clv_predictions 
        WHERE churn_risk_tier = 'High'
        ORDER BY predicted_clv_6months DESC 
        LIMIT 50
    """)
    if not at_risk.empty:
        st.dataframe(at_risk)
    else:
        st.success("No high-value customers identified as high churn risk!")

# -------------------------------------------------------------
# PAGE 5: DATA & OPERATIONS MANAGEMENT
# -------------------------------------------------------------
elif page == "Data & Operations Management":
    st.markdown("<h1 class='dashboard-title'>Platform Data Management</h1>", unsafe_allow_html=True)
    st.write("")
    
    # 1. Download Reporting Services
    st.subheader("Download Executive PDF & Excel Reports")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate Executive PDF Report"):
            resp = api_request("GET", "/api/v1/reports/pdf")
            if resp and resp.status_code == 200:
                st.download_button(
                    label="📥 Download PDF Summary Report",
                    data=resp.content,
                    file_name="CLV_Executive_Report.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Failed to generate PDF.")
    with c2:
        if st.button("Generate Excel Dataset Export"):
            resp = api_request("GET", "/api/v1/reports/excel")
            if resp and resp.status_code == 200:
                st.download_button(
                    label="📥 Download Multi-Sheet Excel Dataset",
                    data=resp.content,
                    file_name="CLV_Platform_Dataset.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Failed to generate Excel sheet.")

    st.write("---")
    
    # 2. Upload CSV Data
    st.subheader("Ingest Clean Transaction Datasets (CSV Upload)")
    uploaded_file = st.file_uploader("Choose a CSV transaction file:", type=["csv"])
    if uploaded_file is not None:
        if st.button("Ingest Transactions"):
            with st.spinner("Processing CSV file and uploading to database..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                resp = api_request("POST", "/api/v1/management/upload-csv", files=files)
                if resp and resp.status_code == 200:
                    st.success("Transactions successfully cleaned and written to database!")
                    st.json(resp.json()["metrics"])
                else:
                    st.error("Ingestion failed. Check that column names map correctly.")

    st.write("---")

    # 3. Pipelines Operations Triggers
    st.subheader("Background Pipeline Management Triggers")
    c_ref, c_train = st.columns(2)
    with c_ref:
        st.markdown("**Recalculate Predictions**")
        st.write("Ensembles models and clusters customers with current database transactions.")
        if st.button("Refresh Prediction Database"):
            with st.spinner("Refreshing segmentations and ensembled CLVs..."):
                resp = api_request("POST", "/api/v1/predictions/refresh")
                if resp and resp.status_code == 200:
                    st.success("Database predictions successfully updated!")
                else:
                    st.error("Failed prediction refresh.")
                    
    with c_train:
        st.markdown("**Weekly Models Retraining**")
        st.write("Triggers complete background refitting of BG/NBD and XGBoost regression models.")
        if st.button("Retrain Models (Background Tasks)"):
            resp = api_request("POST", "/api/v1/management/retrain")
            if resp and resp.status_code == 200:
                st.info("Retraining pipeline successfully started in background! Check terminal logs.")
            else:
                st.error("Failed to start retraining pipeline.")
