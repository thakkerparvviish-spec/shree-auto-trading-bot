import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone
import requests
import time
import random
import math
import concurrent.futures

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY    = "PKMZNC3C3GPVPO3LE7MIKZDS47"
SECRET_KEY = "GPkmZFqzAiv7fhweXnaG7A6YtnxN1gGt2CFJCAwCojgB"
BASE_URL   = "https://paper-api.alpaca.markets"
HEADERS    = {"APCA-API-KEY-ID": API_KEY, "APCA-API-SECRET-KEY": SECRET_KEY}
IST        = timezone(timedelta(hours=5, minutes=30))
ALPHA_KEY  = "N3V3KTDZ3U1QLP2F"

ADMIN = {"username": "Parvish", "password": "Parvish753210#"}

if "clients" not in st.session_state:
    st.session_state.clients = {
        "client1": {"name":"Client 1","username":"client1","password":"Client1@123","active":True, "mode":"Paper","strategy":"Strategy 1","quantity":1,"trades":[],"balance":10000},
        "client2": {"name":"Client 2","username":"client2","password":"Client2@123","active":True, "mode":"Paper","strategy":"Strategy 1","quantity":1,"trades":[],"balance":10000},
        "client3": {"name":"Client 3","username":"client3","password":"Client3@123","active":True, "mode":"Paper","strategy":"Strategy 1","quantity":1,"trades":[],"balance":10000},
        "client4": {"name":"Client 4","username":"client4","password":"Client4@123","active":False,"mode":"Paper","strategy":"Strategy 1","quantity":1,"trades":[],"balance":10000},
        "client5": {"name":"Client 5","username":"client5","password":"Client5@123","active":False,"mode":"Paper","strategy":"Strategy 1","quantity":1,"trades":[],"balance":10000},
    }

STRATEGIES = {
    "Strategy 1": "EMA Crossover",
    "Strategy 2": "4-Confluence",
    "Strategy 3": "Empty Slot",
    "Strategy 4": "Empty Slot",
    "Strategy 5": "Empty Slot",
}

# =========================================================================
# PRICE FUNCTIONS
# =========================================================================
def fetch_btc():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=3)
        d = r.json()
        return {"price":float(d["lastPrice"]),"change_pct":float(d["priceChangePercent"]),"high":float(d["highPrice"]),"low":float(d["lowPrice"])}
    except:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=3)
            d = r.json()["bitcoin"]
            return {"price":d["usd"],"change_pct":d.get("usd_24h_change",0),"high":0,"low":0}
        except:
            return {"price":0,"change_pct":0,"high":0,"low":0}

def fetch_gold():
    # Try multiple fast sources
    sources = [
        lambda: _gold_metals_live(),
        lambda: _gold_yahoo(),
        lambda: _gold_alphavantage(),
    ]
    for source in sources:
        try:
            result = source()
            if result["price"] > 0:
                return result
        except:
            continue
    return {"price":0,"change_pct":0,"high":0,"low":0}

def _gold_metals_live():
    r = requests.get("https://api.metals.live/v1/spot/gold", timeout=3)
    d = r.json()
    gp = float(d[0]["gold"]) if isinstance(d,list) else float(d["gold"])
    return {"price":gp,"change_pct":0,"high":0,"low":0}

def _gold_yahoo():
    headers = {"User-Agent":"Mozilla/5.0"}
    r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d", headers=headers, timeout=3)
    d = r.json()["chart"]["result"][0]["meta"]
    return {"price":d["regularMarketPrice"],"change_pct":d.get("regularMarketChangePercent",0),"high":d.get("regularMarketDayHigh",0),"low":d.get("regularMarketDayLow",0)}

def _gold_alphavantage():
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey={ALPHA_KEY}"
    r = requests.get(url, timeout=3)
    d = r.json()["Realtime Currency Exchange Rate"]
    return {"price":float(d["5. Exchange Rate"]),"change_pct":0,"high":0,"low":0}

def fetch_eur():
    sources = [
        lambda: _eur_frankfurter(),
        lambda: _eur_alphavantage(),
        lambda: _eur_openrates(),
    ]
    for source in sources:
        try:
            result = source()
            if result["price"] > 0:
                return result
        except:
            continue
    return {"price":0,"change_pct":0,"high":0,"low":0}

def _eur_frankfurter():
    r = requests.get("https://api.frankfurter.app/latest?from=EUR&to=USD", timeout=3)
    d = r.json()
    return {"price":d["rates"]["USD"],"change_pct":0,"high":0,"low":0}

def _eur_alphavantage():
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=USD&apikey={ALPHA_KEY}"
    r = requests.get(url, timeout=3)
    d = r.json()["Realtime Currency Exchange Rate"]
    return {"price":float(d["5. Exchange Rate"]),"change_pct":0,"high":0,"low":0}

def _eur_openrates():
    r = requests.get("https://open.er-api.com/v6/latest/EUR", timeout=3)
    d = r.json()
    return {"price":d["rates"]["USD"],"change_pct":0,"high":0,"low":0}

@st.cache_data(ttl=60)
def get_live_prices():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(fetch_btc)
        f2 = ex.submit(fetch_gold)
        f3 = ex.submit(fetch_eur)
        return {"BTCUSD":f1.result(),"XAUUSD":f2.result(),"EURUSD":f3.result()}

@st.cache_data(ttl=60)
def get_ohlcv(symbol):
    try:
        if symbol == "BTCUSD":
            r = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=1", timeout=8)
            data = r.json()
            return [{"time":str(d[0]),"open":d[1],"high":d[2],"low":d[3],"close":d[4],"volume":0} for d in data]
        elif symbol == "XAUUSD":
            headers = {"User-Agent":"Mozilla/5.0"}
            r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=5d", headers=headers, timeout=8)
            d = r.json()["chart"]["result"][0]
            times = d["timestamp"]; ohlcv = d["indicators"]["quote"][0]
            return [{"time":str(times[i]),"open":ohlcv["open"][i] or 0,"high":ohlcv["high"][i] or 0,"low":ohlcv["low"][i] or 0,"close":ohlcv["close"][i] or 0,"volume":ohlcv["volume"][i] or 0} for i in range(len(times)) if ohlcv["close"][i]]
        elif symbol == "EURUSD":
            headers = {"User-Agent":"Mozilla/5.0"}
            r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=15m&range=5d", headers=headers, timeout=8)
            d = r.json()["chart"]["result"][0]
            times = d["timestamp"]; ohlcv = d["indicators"]["quote"][0]
            return [{"time":str(times[i]),"open":ohlcv["open"][i] or 0,"high":ohlcv["high"][i] or 0,"low":ohlcv["low"][i] or 0,"close":ohlcv["close"][i] or 0,"volume":ohlcv["volume"][i] or 0} for i in range(len(times)) if ohlcv["close"][i]]
    except:
        base = 1.085 if symbol=="EURUSD" else 1950.0 if symbol=="XAUUSD" else 60000.0
        return [{"time":str(i),"open":base,"high":base*1.001,"low":base*0.999,"close":base*(1+random.uniform(-0.001,0.001)),"volume":1000} for i in range(100)]

@st.cache_data(ttl=30)
def load_account():
    try:
        r  = requests.get(f"{BASE_URL}/v2/account",  headers=HEADERS, timeout=8)
        r2 = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS, timeout=8)
        return r.json(), r2.json(), None
    except Exception as e:
        return {}, [], str(e)

# =========================================================================
# INDICATORS
# =========================================================================
def calc_ema(data, length):
    result = [None]*len(data); k = 2/(length+1)
    for i in range(len(data)):
        if data[i] is None: continue
        result[i] = data[i] if (i==0 or result[i-1] is None) else data[i]*k+result[i-1]*(1-k)
    return result

def calc_rsi(close, length=14):
    result = [50]*len(close)
    if len(close) < length+1: return result
    gains=[]; losses=[]
    for i in range(1,len(close)):
        ch=close[i]-close[i-1]; gains.append(max(ch,0)); losses.append(max(-ch,0))
    if len(gains)<length: return result
    ag=sum(gains[:length])/length; al=sum(losses[:length])/length
    for i in range(length,len(close)):
        rs=ag/al if al!=0 else 100; result[i]=100-(100/(1+rs))
        if i-1<len(gains):
            ag=(ag*(length-1)+gains[i-1])/length; al=(al*(length-1)+losses[i-1])/length
    return result

# =========================================================================
# PAGE CONFIG & CSS
# =========================================================================
st.set_page_config(page_title="SHREE AUTO TRADING BOT", page_icon="🤖", layout="wide")
st.markdown("""
<style>
    .stApp{background:linear-gradient(135deg,#0a0a0a,#0d1117,#0a0f1e)}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1117,#161b22);border-right:1px solid #21262d}
    .main-title{text-align:center;font-size:42px;font-weight:900;letter-spacing:4px;background:linear-gradient(90deg,#00d4aa,#00a8ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;padding:20px 0 5px 0;text-transform:uppercase}
    .sub-title{text-align:center;color:#8b949e;font-size:13px;letter-spacing:3px;text-transform:uppercase;margin-bottom:20px}
    .ticker{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 20px;color:#8b949e;font-size:12px;text-align:center;letter-spacing:2px;margin-bottom:15px}
    .admin-badge{background:linear-gradient(135deg,#1a0a3a,#2d1060);border:1px solid #7b2ff7;border-radius:8px;padding:8px 16px;color:#bc8cff;font-size:13px;font-weight:700;letter-spacing:2px;text-align:center;margin-bottom:10px}
    .user-badge{background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #30363d;border-radius:8px;padding:8px 16px;color:#00d4aa;font-size:13px;font-weight:700;letter-spacing:2px;text-align:center;margin-bottom:10px}
    [data-testid="stMetric"]{background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #30363d;border-radius:12px;padding:16px;box-shadow:0 4px 15px rgba(0,0,0,0.3)}
    [data-testid="stMetricLabel"]{color:#8b949e !important;font-size:12px !important;letter-spacing:1px;text-transform:uppercase}
    [data-testid="stMetricValue"]{color:#e6edf3 !important;font-size:24px !important;font-weight:700 !important}
    .price-card{background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #30363d;border-radius:12px;padding:15px;text-align:center;margin:5px 0}
    .signal-buy{background:linear-gradient(135deg,#0d2818,#1a4731);border:1px solid #2ea043;border-left:4px solid #2ea043;border-radius:8px;padding:16px;font-size:18px;font-weight:700;color:#3fb950;margin:10px 0}
    .signal-sell{background:linear-gradient(135deg,#2d0f0f,#4a1c1c);border:1px solid #da3633;border-left:4px solid #da3633;border-radius:8px;padding:16px;font-size:18px;font-weight:700;color:#f85149;margin:10px 0}
    .signal-hold{background:linear-gradient(135deg,#1c1a0f,#332d10);border:1px solid #9e6a03;border-left:4px solid #d29922;border-radius:8px;padding:16px;font-size:18px;font-weight:700;color:#d29922;margin:10px 0}
    .client-card-active{background:linear-gradient(135deg,#0d2818,#1a4731);border:1px solid #2ea043;border-radius:12px;padding:15px;margin:5px 0}
    .client-card-inactive{background:linear-gradient(135deg,#2d0f0f,#4a1c1c);border:1px solid #da3633;border-radius:12px;padding:15px;margin:5px 0}
    .live-badge{background:#ff4444;color:white;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
    .paper-badge{background:#0066cc;color:white;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
</style>
""", unsafe_allow_html=True)

# =========================================================================
# SESSION STATE
# =========================================================================
if "logged_in"      not in st.session_state: st.session_state.logged_in=False
if "role"           not in st.session_state: st.session_state.role=None
if "current_user"   not in st.session_state: st.session_state.current_user=None
if "login_attempts" not in st.session_state: st.session_state.login_attempts=0
if "locked_until"   not in st.session_state: st.session_state.locked_until=None

# =========================================================================
# LOGIN
# =========================================================================
if not st.session_state.logged_in:
    st.markdown('<div class="main-title">SHREE AUTO TRADING BOT</div>',unsafe_allow_html=True)
    st.markdown('<div class="sub-title">🔐 SECURE LOGIN PORTAL · AUTHORIZED ACCESS ONLY 🔐</div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,2,1])
    with c2:
        if st.session_state.locked_until and datetime.now(IST)<st.session_state.locked_until:
            st.error(f"🔒 Locked! Try again in {(st.session_state.locked_until-datetime.now(IST)).seconds} seconds.")
            st.stop()
        st.markdown('<div style="text-align:center;font-size:28px;font-weight:900;color:#00d4aa;letter-spacing:3px;margin-bottom:20px;">🔐 LOGIN</div>',unsafe_allow_html=True)
        username=st.text_input("👤 Username",placeholder="Enter username")
        password=st.text_input("🔒 Password",type="password",placeholder="Enter password")
        if st.button("🚀 LOGIN",use_container_width=True):
            if username==ADMIN["username"] and password==ADMIN["password"]:
                st.session_state.logged_in=True; st.session_state.role="admin"; st.session_state.current_user="Parvish"; st.rerun()
            elif username in st.session_state.clients:
                cl=st.session_state.clients[username]
                if not cl["active"]: st.error("❌ Account deactivated. Contact Admin.")
                elif cl["password"]==password:
                    st.session_state.logged_in=True; st.session_state.role="client"; st.session_state.current_user=username; st.rerun()
                else:
                    st.session_state.login_attempts+=1
                    if st.session_state.login_attempts>=3:
                        st.session_state.locked_until=datetime.now(IST)+timedelta(minutes=5); st.error("🔒 Locked 5 min!")
                    else: st.error(f"❌ Wrong password! {3-st.session_state.login_attempts} left.")
            else: st.error("❌ Username not found!")
        st.markdown('<div style="text-align:center;color:#8b949e;font-size:11px;margin-top:20px;">🔐 SHREE AUTO TRADING BOT · PRIVATE & CONFIDENTIAL</div>',unsafe_allow_html=True)

# =========================================================================
# MAIN APP
# =========================================================================
else:
    now=datetime.now(IST)
    st.markdown('<div class="main-title">SHREE AUTO TRADING BOT</div>',unsafe_allow_html=True)
    st.markdown('<div class="sub-title">⚡ LIVE 24/7 · BITCOIN · GOLD · EUR/USD ⚡</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="ticker">🕐 {now.strftime("%A, %d %B %Y  |  %H:%M:%S IST")}  |  👤 {st.session_state.current_user.upper()}  |  {"👑 ADMIN" if st.session_state.role=="admin" else "👤 CLIENT"}  |  📡 LIVE DATA</div>',unsafe_allow_html=True)

    # Live Prices
    prices=get_live_prices()
    p1,p2,p3=st.columns(3)
    labels={"BTCUSD":"₿ BITCOIN","XAUUSD":"🥇 GOLD","EURUSD":"💱 EUR/USD"}
    for col,(sym,data) in zip([p1,p2,p3],prices.items()):
        color="#2ea043" if data["change_pct"]>=0 else "#f85149"
        arrow="▲" if data["change_pct"]>=0 else "▼"
        price_str=f"${data['price']:,.4f}" if data['price']>0 else "⏳ Loading..."
        col.markdown(f'<div class="price-card"><div style="color:#8b949e;font-size:11px;letter-spacing:2px;">{labels.get(sym,sym)}</div><div style="color:#e6edf3;font-size:22px;font-weight:700;">{price_str}</div><div style="color:{color};font-size:13px;">{arrow} {data["change_pct"]:+.2f}%</div></div>',unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    if st.session_state.role=="admin":
        st.sidebar.markdown('<div class="admin-badge">👑 PARVISH · ADMIN</div>',unsafe_allow_html=True)
    else:
        cn=st.session_state.clients[st.session_state.current_user]["name"]
        st.sidebar.markdown(f'<div class="user-badge">👤 {cn.upper()} · CLIENT</div>',unsafe_allow_html=True)
    st.sidebar.markdown("## ⚙️ CONTROLS")
    symbol=st.sidebar.selectbox("📈 Symbol",["BTCUSD","XAUUSD","EURUSD"])
    timeframe=st.sidebar.selectbox("⏱ Timeframe",["15Min","1Hour","4Hour","1Day"])
    st.sidebar.markdown("---")
    auto_refresh=st.sidebar.checkbox("🔄 Auto-refresh (60s)")
    st.sidebar.markdown("---")
    if st.session_state.role=="admin":
        page=st.sidebar.radio("📱 NAVIGATION",["📊 Dashboard","🧠 Strategies","📈 Backtest","📋 Trade Report","👥 Client Manager"])
    else:
        page=st.sidebar.radio("📱 NAVIGATION",["📊 Dashboard","💼 My Trading","📋 My Trade Report"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 LOGOUT",use_container_width=True):
        st.session_state.logged_in=False; st.session_state.role=None; st.session_state.current_user=None; st.rerun()

    account,positions,acc_err=load_account()
    candles=get_ohlcv(symbol)

    c1,c2,c3,c4,c5=st.columns(5)
    if not acc_err:
        cash=float(account.get("cash",0)); equity=float(account.get("equity",0))
        pnl=float(account.get("unrealized_pl") or 0); buying=float(account.get("buying_power",0))
        c1.metric("💰 CASH",f"${cash:,.2f}"); c2.metric("📊 EQUITY",f"${equity:,.2f}")
        c3.metric("💹 BUYING POWER",f"${buying:,.2f}"); c4.metric("📉 P&L",f"${pnl:,.2f}",delta=f"{pnl:+.2f}")
        c5.metric("🔓 POSITIONS",len(positions))
    st.markdown("---")

    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    if page=="📊 Dashboard":
        left,right=st.columns([2,1])
        with left:
            if candles:
                closes=[c["close"] for c in candles]; opens=[c["open"] for c in candles]
                highs=[c["high"] for c in candles]; lows=[c["low"] for c in candles]
                vols=[c["volume"] for c in candles]; times=list(range(len(candles)))
                ema9=calc_ema(closes,9); ema21=calc_ema(closes,21); rsi_v=calc_rsi(closes,14)
                fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.6,0.2,0.2],vertical_spacing=0.02,
                                  subplot_titles=(f"{symbol} · LIVE PRICE + EMA 9/21","RSI (14)","VOLUME"))
                fig.add_trace(go.Candlestick(x=times,open=opens,high=highs,low=lows,close=closes,name="Price",
                              increasing_line_color="#2ea043",decreasing_line_color="#f85149"),row=1,col=1)
                fig.add_trace(go.Scatter(x=times,y=ema9,name="EMA 9",line=dict(color="#d29922",width=1.5)),row=1,col=1)
                fig.add_trace(go.Scatter(x=times,y=ema21,name="EMA 21",line=dict(color="#58a6ff",width=1.5)),row=1,col=1)
                fig.add_trace(go.Scatter(x=times,y=rsi_v,name="RSI",line=dict(color="#bc8cff",width=1.5)),row=2,col=1)
                fig.add_hline(y=70,line_dash="dot",line_color="#f85149",row=2,col=1)
                fig.add_hline(y=30,line_dash="dot",line_color="#2ea043",row=2,col=1)
                colors=["#2ea043" if c>=o else "#f85149" for c,o in zip(closes,opens)]
                fig.add_trace(go.Bar(x=times,y=vols,name="Volume",marker_color=colors),row=3,col=1)
                fig.update_layout(height=600,paper_bgcolor="#0d1117",plot_bgcolor="#0d1117",
                                  font=dict(color="#8b949e"),xaxis_rangeslider_visible=False,
                                  legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
                                  margin=dict(l=0,r=0,t=30,b=0))
                fig.update_xaxes(gridcolor="#21262d"); fig.update_yaxes(gridcolor="#21262d")
                st.plotly_chart(fig,use_container_width=True)
            else:
                st.warning("Loading chart data...")

        with right:
            st.markdown("### 🎯 STRATEGY 1 — EMA")
            if candles and len(candles)>2:
                closes=[c["close"] for c in candles]
                ema9=calc_ema(closes,9); ema21=calc_ema(closes,21); rsi_v=calc_rsi(closes,14)
                if ema9[-2] and ema21[-2] and ema9[-1] and ema21[-1]:
                    if ema9[-2]<ema21[-2] and ema9[-1]>ema21[-1] and rsi_v[-1]<70:
                        st.markdown(f'<div class="signal-buy">🟢 BUY<br><small>EMA Cross UP · RSI:{rsi_v[-1]:.1f}</small></div>',unsafe_allow_html=True)
                    elif ema9[-2]>ema21[-2] and ema9[-1]<ema21[-1] and rsi_v[-1]>30:
                        st.markdown(f'<div class="signal-sell">🔴 SELL<br><small>EMA Cross DOWN · RSI:{rsi_v[-1]:.1f}</small></div>',unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="signal-hold">🟡 HOLD<br><small>No crossover · RSI:{rsi_v[-1]:.1f}</small></div>',unsafe_allow_html=True)
                last=closes[-1]
                st.metric("💰 Price",f"${last:,.4f}")
                st.metric("📈 EMA 9",f"${ema9[-1]:,.4f}" if ema9[-1] else "N/A")
                st.metric("📉 EMA 21",f"${ema21[-1]:,.4f}" if ema21[-1] else "N/A")
                st.metric("📊 RSI",f"{rsi_v[-1]:.1f}")

            st.markdown("### 📡 MARKET STATUS")
            st.success("🟢 BITCOIN — 24/7 LIVE")
            st.success("🟢 EUR/USD — 24/7 LIVE")
            st.info("🟡 GOLD — Open 7PM-1:30AM IST")

        st.markdown("---")
        st.markdown("### 🔓 OPEN POSITIONS")
        if positions:
            import pandas as pd
            pdf=pd.DataFrame([{"Symbol":p["symbol"],"Qty":p["qty"],"Entry $":p["avg_entry_price"],"Current $":p["current_price"],"P&L $":p["unrealized_pl"]} for p in positions])
            st.dataframe(pdf,use_container_width=True)
        else:
            st.info("No open positions.")

    # ── CLIENT TRADING ─────────────────────────────────────────────────────
    elif page=="💼 My Trading":
        client=st.session_state.clients[st.session_state.current_user]
        st.markdown(f"### 💼 MY TRADING PANEL — {client['name'].upper()}")
        st.markdown("---")
        c1,c2=st.columns(2)
        with c1:
            available=[k for k,v in STRATEGIES.items() if v!="Empty Slot"]
            sel=st.selectbox("🧠 Strategy",available)
            qty=st.number_input("📦 Quantity",min_value=1,max_value=1000,value=client["quantity"])
            mode=st.radio("🔄 Mode",["📄 Paper Trading","🔴 Live Trading"],index=0 if client["mode"]=="Paper" else 1)
            if "Live" in mode: st.error("⚠️ WARNING: Live Trading uses REAL MONEY!")
            if st.button("💾 SAVE",use_container_width=True):
                st.session_state.clients[st.session_state.current_user].update({"strategy":sel,"quantity":qty,"mode":"Live" if "Live" in mode else "Paper"})
                st.success("✅ Saved!")
        with c2:
            tp=sum(t.get("pnl",0) for t in client["trades"]); total=len(client["trades"])
            wins=len([t for t in client["trades"] if t.get("pnl",0)>0])
            st.metric("💰 Balance",f"${client['balance']:,.2f}")
            st.metric("📈 P&L",f"${tp:+,.2f}")
            st.metric("🎯 Win Rate",f"{(wins/total*100):.1f}%" if total>0 else "0%")
            st.metric("📊 Trades",total)

    # ── STRATEGIES ─────────────────────────────────────────────────────────
    elif page=="🧠 Strategies":
        st.markdown("### 🧠 STRATEGY MANAGER — 5 SLOTS")
        st.markdown("---")
        for slot,name in STRATEGIES.items():
            c1,c2=st.columns([3,1])
            with c1:
                if name!="Empty Slot":
                    st.markdown(f'<div class="client-card-active">✅ <b>{slot}</b> — {name}</div>',unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:#161b22;border:2px dashed #30363d;border-radius:12px;padding:15px;margin:5px 0;">📭 <b>{slot}</b> — Empty</div>',unsafe_allow_html=True)
            with c2:
                st.success("🟢 ACTIVE") if name!="Empty Slot" else st.info("⬜ EMPTY")

    # ── BACKTEST ──────────────────────────────────────────────────────────
    elif page=="📈 Backtest":
        st.markdown("### 📈 STRATEGY BACKTESTER")
        st.markdown("---")
        c1,c2=st.columns(2)
        with c1: bt_sym=st.selectbox("📈 Symbol",["BTCUSD","XAUUSD","EURUSD"])
        with c2: init_cap=st.number_input("💰 Initial Capital ($)",value=10000,step=1000)
        if st.button("🚀 RUN BACKTEST",use_container_width=True):
            with st.spinner("Running backtest..."):
                bt_candles=get_ohlcv(bt_sym)
                if bt_candles:
                    closes=[c["close"] for c in bt_candles]
                    ema9=calc_ema(closes,9); ema21=calc_ema(closes,21); rsi_v=calc_rsi(closes,14)
                    capital=init_cap; position=0; entry_price=0; trades=[]; equity=[capital]
                    for i in range(22,len(bt_candles)):
                        cur=closes[i]
                        buy_sig=ema9[i-1] and ema21[i-1] and ema9[i] and ema21[i] and ema9[i-1]<ema21[i-1] and ema9[i]>ema21[i] and rsi_v[i]<70
                        sell_sig=ema9[i-1] and ema21[i-1] and ema9[i] and ema21[i] and ema9[i-1]>ema21[i-1] and ema9[i]<ema21[i] and rsi_v[i]>30
                        if buy_sig and position==0:
                            shares=int((capital*1/100)/cur)
                            if shares>0: position=shares; entry_price=cur
                        elif sell_sig and position>0:
                            pnl=(cur-entry_price)*position; roi=(pnl/(entry_price*position)*100) if entry_price>0 else 0
                            capital+=pnl
                            trades.append({"Entry $":round(entry_price,4),"Exit $":round(cur,4),"P&L $":round(pnl,2),"ROI %":round(roi,2),"Result":"✅ WIN" if pnl>0 else "❌ LOSS"})
                            position=0; entry_price=0
                        equity.append(capital)
                    if trades:
                        import pandas as pd
                        df_t=pd.DataFrame(trades); total_pnl=capital-init_cap
                        wins=len([t for t in trades if t["P&L $"]>0]); win_rate=wins/len(trades)*100
                        r1,r2,r3,r4=st.columns(4)
                        r1.metric("💰 Final",f"${capital:,.2f}",delta=f"${total_pnl:+,.2f}")
                        r2.metric("📈 ROI",f"{total_pnl/init_cap*100:+.2f}%")
                        r3.metric("🎯 Win Rate",f"{win_rate:.1f}%")
                        r4.metric("📊 Trades",len(trades))
                        st.dataframe(df_t,use_container_width=True)
                        if win_rate>=50 and total_pnl>0: st.success(f"✅ PROFITABLE!")
                        else: st.warning(f"⚠️ Needs improvement.")

    # ── TRADE REPORT ──────────────────────────────────────────────────────
    elif page in ["📋 Trade Report","📋 My Trade Report"]:
        import pandas as pd
        st.markdown("### 📋 TRADE REPORT")
        sample=[
            {"Client":"client1","Strategy":"EMA Crossover","Symbol":"BTCUSD","Entry Time":"2026-06-25 19:15","Square Off":"2026-06-25 21:30","Entry $":61420.50,"Exit $":62100.00,"Qty":1,"P&L $":679.50,"ROI %":1.04,"Mode":"Paper","Result":"✅ WIN"},
            {"Client":"client1","Strategy":"4-Confluence","Symbol":"XAUUSD","Entry Time":"2026-06-26 09:00","Square Off":"2026-06-26 11:30","Entry $":1945.00,"Exit $":1962.00,"Qty":1,"P&L $":17.00,"ROI %":0.87,"Mode":"Paper","Result":"✅ WIN"},
            {"Client":"client2","Strategy":"EMA Crossover","Symbol":"EURUSD","Entry Time":"2026-06-26 08:00","Square Off":"2026-06-26 10:00","Entry $":1.0842,"Exit $":1.0780,"Qty":1000,"P&L $":-62.00,"ROI %":-0.57,"Mode":"Paper","Result":"❌ LOSS"},
        ]
        if st.session_state.role=="client":
            sample=[t for t in sample if t["Client"]==st.session_state.current_user]
        tp=sum(t["P&L $"] for t in sample); wins=len([t for t in sample if t["P&L $"]>0])
        s1,s2,s3,s4=st.columns(4)
        s1.metric("📊 Trades",len(sample)); s2.metric("💰 P&L",f"${tp:+,.2f}")
        s3.metric("✅ Wins",wins); s4.metric("❌ Losses",len(sample)-wins)
        df_r=pd.DataFrame(sample)
        if st.session_state.role=="client": df_r=df_r.drop(columns=["Client"])
        st.dataframe(df_r,use_container_width=True)

    # ── CLIENT MANAGER ─────────────────────────────────────────────────────
    elif page=="👥 Client Manager":
        st.markdown("### 👥 CLIENT MANAGER")
        st.markdown("---")
        for cid,client in st.session_state.clients.items():
            c1,c2,c3,c4=st.columns([2,1,1,1])
            with c1:
                if client["active"]: st.markdown(f'<div class="client-card-active">✅ <b>{client["name"]}</b> · @{client["username"]}</div>',unsafe_allow_html=True)
                else: st.markdown(f'<div class="client-card-inactive">❌ <b>{client["name"]}</b> · @{client["username"]} · DEACTIVATED</div>',unsafe_allow_html=True)
            with c2: st.markdown(f"**{'🟢 ACTIVE' if client['active'] else '🔴 INACTIVE'}**")
            with c3:
                if client["active"]:
                    if st.button(f"🔴 Deactivate",key=f"d_{cid}"): st.session_state.clients[cid]["active"]=False; st.rerun()
                else:
                    if st.button(f"🟢 Activate",key=f"a_{cid}"): st.session_state.clients[cid]["active"]=True; st.rerun()
            with c4:
                if st.button(f"🔑 Reset",key=f"r_{cid}"): st.session_state.clients[cid]["password"]=f"{cid.capitalize()}@123"; st.success(f"Reset!")
            st.markdown("---")
        st.markdown("### ✏️ EDIT CLIENT")
        ec=st.selectbox("Select",list(st.session_state.clients.keys()))
        cd=st.session_state.clients[ec]
        e1,e2,e3=st.columns(3)
        with e1: nn=st.text_input("👤 Name",value=cd["name"])
        with e2: np=st.text_input("🔒 Password",value=cd["password"])
        with e3: nb=st.number_input("💰 Balance",value=cd["balance"],step=1000)
        if st.button("💾 UPDATE",use_container_width=True):
            st.session_state.clients[ec].update({"name":nn,"password":np,"balance":nb}); st.success(f"✅ {nn} updated!")

    if auto_refresh:
        time.sleep(60)
        st.rerun()
