import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import time

# --- Config ---
API_KEY    = "PKMNZNC3C3GPVP03LE7MIKZDS47"
SECRET_KEY = "GPkaZFqzAiv7fhwmXnaG7A6YtnxNIgGt2CFJCAwCoJgR"
BASE_URL   = "https://paper-api.alpaca.markets"
DATA_URL   = "https://data.alpaca.markets"
HEADERS    = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY
}

st.set_page_config(page_title="SHREE AUTO TRADING BOT", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; }
.metric-box {
    background: #1e2130;
    border-radius: 10px;
    padding: 15px;
    text-align: center;
    border: 1px solid #2d3250;
}
.price-up { color: #00ff88; font-size: 18px; font-weight: bold; }
.price-down { color: #ff4444; font-size: 18px; font-weight: bold; }
.price-neutral { color: #ffffff; font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center; color:white;'>🤖 SHREE AUTO TRADING BOT</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if u == "Parvish" and p == "Parvish753210#":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Wrong credentials!")
    st.stop()

# --- Helper Functions ---
def get_account():
    try:
        r = requests.get(f"{BASE_URL}/v2/account", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def get_positions():
    try:
        r = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def get_orders(limit=20):
    try:
        r = requests.get(f"{BASE_URL}/v2/orders?limit={limit}&status=all", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def get_live_price(symbol):
    try:
        r = requests.get(
            f"{DATA_URL}/v2/stocks/{symbol}/trades/latest",
            headers=HEADERS,
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return float(data.get("trade", {}).get("p", 0))
    except:
        pass
    # fallback: try quotes
    try:
        r = requests.get(
            f"{DATA_URL}/v2/stocks/{symbol}/quotes/latest",
            headers=HEADERS,
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            quote = data.get("quote", {})
            ask = float(quote.get("ap", 0))
            bid = float(quote.get("bp", 0))
            if ask > 0 and bid > 0:
                return (ask + bid) / 2
    except:
        pass
    return None

def get_bars(symbol, days=7):
    try:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        r = requests.get(
            f"{DATA_URL}/v2/stocks/{symbol}/bars",
            headers=HEADERS,
            params={"timeframe": "1Day", "start": start, "limit": days},
            timeout=10
        )
        if r.status_code == 200:
            bars = r.json().get("bars", [])
            return bars
    except:
        pass
    return []

def place_order(symbol, qty, side, order_type="market", limit_price=None):
    order_data = {
        "symbol": symbol.upper(),
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": "gtc"
    }
    if order_type == "limit" and limit_price:
        order_data["limit_price"] = str(limit_price)
    try:
        r = requests.post(f"{BASE_URL}/v2/orders", json=order_data, headers=HEADERS, timeout=10)
        return r.status_code, r.json()
    except Exception as e:
        return 500, {"message": str(e)}

# --- Main Dashboard ---
st.markdown("<h1 style='color:white;'>🤖 SHREE AUTO TRADING BOT</h1>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now().strftime('%d %b %Y  %H:%M:%S')}  |  Paper Trading Mode")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💹 Live Rates", "🛒 Trade", "📋 Orders"])

# ============================================================
# TAB 1 — DASHBOARD
# ============================================================
with tab1:
    acc = get_account()
    if acc:
        equity        = float(acc.get("equity", 0))
        cash          = float(acc.get("cash", 0))
        buying_power  = float(acc.get("buying_power", 0))
        pl            = float(acc.get("unrealized_pl") or 0)
        pl_pct        = float(acc.get("unrealized_plpc") or 0) * 100
        portfolio_val = float(acc.get("portfolio_value", 0))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Portfolio Value", f"${portfolio_val:,.2f}")
        col2.metric("💵 Cash", f"${cash:,.2f}")
        col3.metric("⚡ Buying Power", f"${buying_power:,.2f}")
        col4.metric("📈 Unrealized P&L", f"${pl:,.2f}", delta=f"{pl_pct:.2f}%")
    else:
        st.error("❌ Could not connect to Alpaca. Check API keys.")

    st.divider()

    # Open Positions
    st.subheader("📊 Open Positions")
    positions = get_positions()
    if positions and isinstance(positions, list) and len(positions) > 0:
        rows = []
        for p in positions:
            sym = p.get("symbol", "")
            live = get_live_price(sym)
            live_str = f"${live:.2f}" if live else "N/A"
            rows.append({
                "Symbol": sym,
                "Qty": p.get("qty"),
                "Entry Price": f"${float(p.get('avg_entry_price', 0)):.2f}",
                "Live Price": live_str,
                "Market Value": f"${float(p.get('market_value', 0)):.2f}",
                "P&L $": f"${float(p.get('unrealized_pl', 0)):.2f}",
                "P&L %": f"{float(p.get('unrealized_plpc', 0))*100:.2f}%",
                "Side": p.get("side", "").upper()
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("📭 No open positions currently.")

# ============================================================
# TAB 2 — LIVE RATES
# ============================================================
with tab2:
    st.subheader("💹 Live Market Rates")

    # Popular stocks
    watchlist = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "SPY", "QQQ", "GOLD"]

    # Custom symbol add
    custom = st.text_input("➕ Add symbol to watchlist", placeholder="e.g. NFLX").upper().strip()
    if custom and custom not in watchlist:
        watchlist.insert(0, custom)

    st.markdown("**Fetching live prices...**")

    cols = st.columns(5)
    for i, sym in enumerate(watchlist):
        price = get_live_price(sym)
        with cols[i % 5]:
            if price and price > 0:
                st.metric(label=sym, value=f"${price:,.2f}")
            else:
                st.metric(label=sym, value="N/A")

    st.divider()

    # Price chart
    st.subheader("📈 Price Chart")
    chart_sym = st.selectbox("Select symbol for chart", watchlist)
    days = st.slider("Days of history", 3, 30, 7)

    bars = get_bars(chart_sym, days)
    if bars:
        df = pd.DataFrame(bars)
        df["t"] = pd.to_datetime(df["t"])
        fig = go.Figure(data=[go.Candlestick(
            x=df["t"],
            open=df["o"],
            high=df["h"],
            low=df["l"],
            close=df["c"],
            name=chart_sym
        )])
        fig.update_layout(
            title=f"{chart_sym} — Last {days} Days",
            paper_bgcolor="#0e1117",
            plot_bgcolor="#0e1117",
            font_color="white",
            xaxis_rangeslider_visible=False,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No chart data available for {chart_sym}. Market may be closed.")

    if st.button("🔄 Refresh Prices"):
        st.rerun()

# ============================================================
# TAB 3 — TRADE
# ============================================================
with tab3:
    st.subheader("🛒 Place Order")

    col1, col2 = st.columns(2)
    with col1:
        symbol     = st.text_input("Symbol", value="AAPL").upper()
        qty        = st.number_input("Quantity", min_value=1, max_value=10000, value=1)
        side       = st.selectbox("Side", ["buy", "sell"])
        order_type = st.selectbox("Order Type", ["market", "limit"])

    with col2:
        # Show live price for selected symbol
        if symbol:
            live = get_live_price(symbol)
            if live:
                st.metric(f"📡 Live Price — {symbol}", f"${live:,.2f}")
                est_value = live * qty
                st.metric("💰 Estimated Value", f"${est_value:,.2f}")
            else:
                st.warning("Price unavailable (market may be closed)")

        if order_type == "limit":
            limit_price = st.number_input("Limit Price ($)", min_value=0.01, value=100.0, step=0.01)
        else:
            limit_price = None

    st.divider()
    confirm = st.checkbox(f"✅ I confirm: {side.upper()} {qty} shares of {symbol}")
    if confirm:
        if st.button(f"🚀 Place {side.upper()} Order", type="primary", use_container_width=True):
            code, resp = place_order(symbol, qty, side, order_type, limit_price)
            if code in [200, 201]:
                st.success(f"✅ Order placed! {side.upper()} {qty} x {symbol}")
                st.json(resp)
            else:
                st.error(f"❌ Error: {resp.get('message', 'Unknown error')}")

# ============================================================
# TAB 4 — ORDERS
# ============================================================
with tab4:
    st.subheader("📋 Recent Orders")
    orders = get_orders(20)
    if orders and isinstance(orders, list):
        rows = []
        for o in orders:
            rows.append({
                "Symbol":   o.get("symbol"),
                "Side":     o.get("side","").upper(),
                "Qty":      o.get("qty"),
                "Type":     o.get("type"),
                "Status":   o.get("status","").upper(),
                "Filled @": f"${float(o.get('filled_avg_price') or 0):.2f}",
                "Time":     o.get("created_at","")[:16].replace("T"," ")
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No orders found.")

    if st.button("🔄 Refresh Orders"):
        st.rerun()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🤖 SHREE BOT")
    st.markdown("**Mode:** Paper Trading")
    st.markdown("**Broker:** Alpaca")
    st.markdown(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
    st.divider()
    if st.button("🔄 Refresh All"):
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()
