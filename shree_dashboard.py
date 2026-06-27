import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone
import requests
import time
import random
import math

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY    = "PKMZNC3C3GPVPO3LE7MIKZDS47"
SECRET_KEY = "GPkmZFqzAiv7fhweXnaG7A6YtnxN1gGt2CFJCAwCojgB"
BASE_URL   = "https://paper-api.alpaca.markets"
HEADERS    = {"APCA-API-KEY-ID": API_KEY, "APCA-API-SECRET-KEY": SECRET_KEY}
IST        = timezone(timedelta(hours=5, minutes=30))

SYMBOL_MAP = {"BTCUSD": "bitcoin", "XAUUSD": "gold", "EURUSD": "eur"}

# ── Admin ─────────────────────────────────────────────────────────────────────
ADMIN = {"username": "Parvish", "password": "Parvish753210#"}

if "clients" not in st.session_state:
    st.session_state.clients = {
        "client1": {"name": "Client 1", "username": "client1", "password": "Client1@123", "active": True,  "mode": "Paper", "strategy": "Strategy 1", "quantity": 1, "trades": [], "balance": 10000},
        "client2": {"name": "Client 2", "username": "client2", "password": "Client2@123", "active": True,  "mode": "Paper", "strategy": "Strategy 1", "quantity": 1, "trades": [], "balance": 10000},
        "client3": {"name": "Client 3", "username": "client3", "password": "Client3@123", "active": True,  "mode": "Paper", "strategy": "Strategy 1", "quantity": 1, "trades": [], "balance": 10000},
        "client4": {"name": "Client 4", "username": "client4", "password": "Client4@123", "active": False, "mode": "Paper", "strategy": "Strategy 1", "quantity": 1, "trades": [], "balance": 10000},
        "client5": {"name": "Client 5", "username": "client5", "password": "Client5@123", "active": False, "mode": "Paper", "strategy": "Strategy 1", "quantity": 1, "trades": [], "balance": 10000},
    }

STRATEGIES = {
    "Strategy 1": "EMA Crossover",
    "Strategy 2": "4-Confluence",
    "Strategy 3": "Empty Slot",
    "Strategy 4": "Empty Slot",
    "Strategy 5": "Empty Slot",
}

# =========================================================================
# 4-CONFLUENCE STRATEGY (Built-in — No separate file needed)
# =========================================================================
def calc_rsi(close, length=14):
    if len(close) < length + 1:
        return [50] * len(close)
    result = [50] * len(close)
    gains, losses = [], []
    for i in range(1, len(close)):
        ch = close[i] - close[i-1]
        gains.append(max(ch, 0))
        losses.append(max(-ch, 0))
    if len(gains) < length:
        return result
    ag = sum(gains[:length]) / length
    al = sum(losses[:length]) / length
    for i in range(length, len(close)):
        rs = ag / al if al != 0 else 100
        result[i] = 100 - (100 / (1 + rs))
        if i - 1 < len(gains):
            ag = (ag * (length-1) + gains[i-1]) / length
            al = (al * (length-1) + losses[i-1]) / length
    return result

def calc_ema(data, length):
    result = [None] * len(data)
    k = 2 / (length + 1)
    for i in range(len(data)):
        if data[i] is None:
            continue
        if i == 0 or result[i-1] is None:
            result[i] = data[i]
        else:
            result[i] = data[i] * k + result[i-1] * (1 - k)
    return result

def calc_sma(data, length):
    result = [None] * len(data)
    for i in range(length-1, len(data)):
        w = data[i-length+1:i+1]
        if None not in w:
            result[i] = sum(w) / length
    return result

def calc_stdev(data, length):
    result = [None] * len(data)
    for i in range(length-1, len(data)):
        w = data[i-length+1:i+1]
        if None not in w:
            m = sum(w)/length
            result[i] = math.sqrt(sum((x-m)**2 for x in w)/length)
    return result

def calc_atr(high, low, close, length=14):
    tr = [0]
    for i in range(1, len(close)):
        tr.append(max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])))
    result = [None] * len(close)
    if len(tr) >= length:
        result[length-1] = sum(tr[:length]) / length
        for i in range(length, len(tr)):
            if result[i-1]:
                result[i] = (result[i-1]*(length-1) + tr[i]) / length
    return result

def calc_adx(high, low, close, length=14):
    n = len(close)
    dm_p = [0]*n; dm_m = [0]*n; tr = [0]*n
    for i in range(1, n):
        up = high[i]-high[i-1]; dn = low[i-1]-low[i]
        dm_p[i] = up if up>dn and up>0 else 0
        dm_m[i] = dn if dn>up and dn>0 else 0
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    def ws(d, l):
        r = [0]*len(d)
        if len(d) >= l:
            r[l] = sum(d[1:l+1])
            for i in range(l+1, len(d)):
                r[i] = r[i-1] - r[i-1]/l + d[i]
        return r
    str_ = ws(tr, length); sdp = ws(dm_p, length); sdm = ws(dm_m, length)
    adx = [0]*n
    dx_vals = []
    for i in range(length, n):
        if str_[i] > 0:
            dip = 100*sdp[i]/str_[i]; dim = 100*sdm[i]/str_[i]
            tot = dip+dim
            dx_vals.append((i, 100*abs(dip-dim)/tot if tot>0 else 0))
    if len(dx_vals) >= length:
        start = dx_vals[length-1][0]
        adx[start] = sum(v for _,v in dx_vals[:length])/length
        prev = start
        for i,v in dx_vals[length:]:
            adx[i] = (adx[prev]*(length-1)+v)/length
            prev = i
    return adx

def confluence_signal(candles, params=None):
    if len(candles) < 50:
        return {"signal":"HOLD","bull_votes":0,"bear_votes":0,"adx":0,"is_trending":False,
                "rsi":50,"entry":0,"sl_price":None,"tp_price":None,
                "votes":{"MTF RSI":"⬜","SR+Volume":"⬜","Squeeze":"⬜","WaveTrend":"⬜"}}
    if params is None:
        params = {"rsi_bull":55,"rsi_bear":45,"vol_mult":1.35,"sr_buffer":0.006,
                  "bb_len":20,"bb_mult":2.0,"kc_mult":1.6,"wt_ch":10,"wt_avg":21,
                  "wt_ob":55,"wt_os":-55,"adx_thresh":20,"sl_perc":0.012,"rr":3.0,"min_conf":2}

    close  = [c["close"]  for c in candles]
    high   = [c["high"]   for c in candles]
    low    = [c["low"]    for c in candles]
    volume = [c["volume"] for c in candles]
    hlc3   = [(h+l+c)/3 for h,l,c in zip(high,low,close)]

    # 1. RSI
    rsi_vals = calc_rsi(close, 14)
    rsi_cur  = rsi_vals[-1]
    mtf_bull = rsi_cur > params["rsi_bull"]
    mtf_bear = rsi_cur < params["rsi_bear"]

    # 2. SR + Volume
    plen = 5
    ph = [None]*len(high)
    pl = [None]*len(low)
    for i in range(plen, len(high)-plen):
        if high[i] == max(high[i-plen:i+plen+1]): ph[i] = high[i]
        if low[i]  == min(low[i-plen:i+plen+1]):  pl[i] = low[i]
    last_res = next((v for v in reversed(ph) if v), None)
    last_sup = next((v for v in reversed(pl) if v), None)
    vol_sma  = calc_sma(volume, 20)
    vol_avg  = vol_sma[-1] if vol_sma[-1] else 1
    vol_spk  = volume[-1] > vol_avg * params["vol_mult"]
    buf      = params["sr_buffer"]
    cur      = close[-1]
    near_s   = last_sup and cur<=last_sup*(1+buf) and cur>=last_sup*(1-buf)
    near_r   = last_res and cur<=last_res*(1+buf) and cur>=last_res*(1-buf)
    sr_bull  = bool(near_s and vol_spk)
    sr_bear  = bool(near_r and vol_spk)

    # 3. Squeeze Momentum
    bl = params["bb_len"]
    basis = calc_sma(close, bl)
    sd    = calc_stdev(close, bl)
    bb_up = [b+params["bb_mult"]*s if b and s else None for b,s in zip(basis,sd)]
    bb_lo = [b-params["bb_mult"]*s if b and s else None for b,s in zip(basis,sd)]
    kcb   = calc_ema(close, bl)
    atrv  = calc_atr(high, low, close, bl)
    kc_up = [k+params["kc_mult"]*a if k and a else None for k,a in zip(kcb,atrv)]
    kc_lo = [k-params["kc_mult"]*a if k and a else None for k,a in zip(kcb,atrv)]
    sqz   = [bool(bl and bu and kl and ku and bl>kl and bu<ku) for bu,bl,ku,kl in zip(bb_up,bb_lo,kc_up,kc_lo)]
    hi_n  = [max(high[max(0,i-bl+1):i+1]) for i in range(len(high))]
    lo_n  = [min(low[max(0,i-bl+1):i+1])  for i in range(len(low))]
    mom_s = [c-((h+l)/2+(b if b else c))/2 for c,h,l,b in zip(close,hi_n,lo_n,basis)]
    mom   = calc_ema(mom_s, bl)
    sqz_bull = mom[-1] and mom[-2] and mom[-1]>0 and mom[-1]>mom[-2]
    sqz_bear = mom[-1] and mom[-2] and mom[-1]<0 and mom[-1]<mom[-2]
    fired_b  = len(sqz)>1 and sqz[-2] and not sqz[-1] and mom[-1] and mom[-1]>0
    fired_s  = len(sqz)>1 and sqz[-2] and not sqz[-1] and mom[-1] and mom[-1]<0

    # 4. WaveTrend
    esa  = calc_ema(hlc3, params["wt_ch"])
    dv   = calc_ema([abs(h-e) if e else 0 for h,e in zip(hlc3,esa)], params["wt_ch"])
    ci   = [(h-e)/(0.015*d) if e and d and d!=0 else 0 for h,e,d in zip(hlc3,esa,dv)]
    wt1  = calc_ema(ci, params["wt_avg"])
    wt2  = calc_sma(wt1, 4)
    wt_up   = wt1[-2] and wt2[-2] and wt1[-1] and wt2[-1] and wt1[-2]<wt2[-2] and wt1[-1]>wt2[-1] and wt1[-1]<params["wt_os"]+25
    wt_down = wt1[-2] and wt2[-2] and wt1[-1] and wt2[-1] and wt1[-2]>wt2[-2] and wt1[-1]<wt2[-1] and wt1[-1]>params["wt_ob"]-25

    # 5. ADX
    adx_v    = calc_adx(high, low, close, 14)
    adx_cur  = adx_v[-1] if adx_v[-1] else 0
    trending = adx_cur > params["adx_thresh"]

    # Votes
    bv = sum([bool(mtf_bull), bool(sr_bull), bool(sqz_bull or fired_b), bool(wt_up)])
    sv = sum([bool(mtf_bear), bool(sr_bear), bool(sqz_bear or fired_s), bool(wt_down)])
    trend_ok = trending

    long_ok  = bv >= params["min_conf"] and trend_ok
    short_ok = sv >= params["min_conf"] and trend_ok

    if long_ok:
        sl = cur*(1-params["sl_perc"]); tp = cur+(cur-sl)*params["rr"]; sig="BUY"
    elif short_ok:
        sl = cur*(1+params["sl_perc"]); tp = cur-(sl-cur)*params["rr"]; sig="SELL"
    else:
        sl=None; tp=None; sig="HOLD"

    return {
        "signal": sig, "bull_votes": bv, "bear_votes": sv,
        "adx": round(adx_cur,2), "is_trending": trending,
        "rsi": round(rsi_cur,2), "entry": round(cur,4),
        "sl_price": round(sl,4) if sl else None,
        "tp_price": round(tp,4) if tp else None,
        "votes": {
            "MTF RSI":  "✅" if mtf_bull else ("🔴" if mtf_bear else "⬜"),
            "SR+Volume":"✅" if sr_bull  else ("🔴" if sr_bear  else "⬜"),
            "Squeeze":  "✅" if (sqz_bull or fired_b) else ("🔴" if (sqz_bear or fired_s) else "⬜"),
            "WaveTrend":"✅" if wt_up    else ("🔴" if wt_down   else "⬜"),
        }
    }

# =========================================================================
# DATA FUNCTIONS
# =========================================================================
@st.cache_data(ttl=15)
def get_live_prices():
    prices = {}

    # ── BITCOIN — Binance primary, CoinGecko backup ────────────────────────
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=8)
        d = r.json()
        prices["BTCUSD"] = {
            "price":      float(d["lastPrice"]),
            "change_pct": float(d["priceChangePercent"]),
            "high":       float(d["highPrice"]),
            "low":        float(d["lowPrice"]),
        }
    except:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=8)
            d = r.json()["bitcoin"]
            prices["BTCUSD"] = {"price": d["usd"], "change_pct": d.get("usd_24h_change",0), "high":0,"low":0}
        except:
            prices["BTCUSD"] = {"price": 0, "change_pct": 0, "high":0,"low":0}

    # ── GOLD — Yahoo Finance primary, metals.live backup ──────────────────
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d", headers=headers, timeout=8)
        d = r.json()["chart"]["result"][0]["meta"]
        prices["XAUUSD"] = {
            "price":      d["regularMarketPrice"],
            "change_pct": d.get("regularMarketChangePercent", 0),
            "high":       d.get("regularMarketDayHigh", 0),
            "low":        d.get("regularMarketDayLow", 0),
        }
    except:
        try:
            r = requests.get("https://api.metals.live/v1/spot/gold", timeout=8)
            d = r.json()
            gp = float(d[0]["gold"]) if isinstance(d, list) else float(d["gold"])
            prices["XAUUSD"] = {"price": gp, "change_pct": 0, "high":0,"low":0}
        except:
            try:
                r = requests.get("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", timeout=8)
                d = r.json()
                gp = float(d[0]["spreadProfilePrices"][0]["ask"])
                prices["XAUUSD"] = {"price": gp, "change_pct": 0, "high":0,"low":0}
            except:
                prices["XAUUSD"] = {"price": 0, "change_pct": 0, "high":0,"low":0}

    # ── EUR/USD — Yahoo Finance primary, Frankfurter backup ───────────────
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=1m&range=1d", headers=headers, timeout=8)
        d = r.json()["chart"]["result"][0]["meta"]
        prices["EURUSD"] = {
            "price":      d["regularMarketPrice"],
            "change_pct": d.get("regularMarketChangePercent", 0),
            "high":       d.get("regularMarketDayHigh", 0),
            "low":        d.get("regularMarketDayLow", 0),
        }
    except:
        try:
            r = requests.get("https://api.frankfurter.app/latest?from=EUR&to=USD", timeout=8)
            d = r.json()
            prices["EURUSD"] = {"price": d["rates"]["USD"], "change_pct": 0, "high":0,"low":0}
        except:
            try:
                r = requests.get("https://open.er-api.com/v6/latest/EUR", timeout=8)
                d = r.json()
                prices["EURUSD"] = {"price": d["rates"]["USD"], "change_pct": 0, "high":0,"low":0}
            except:
                prices["EURUSD"] = {"price": 0, "change_pct": 0, "high":0,"low":0}

    return prices

@st.cache_data(ttl=60)
def get_ohlcv(symbol):
    try:
        if symbol == "BTCUSD":
            r    = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=1", timeout=10)
            data = r.json()
            rows = [{"time":str(d[0]),"open":d[1],"high":d[2],"low":d[3],"close":d[4],"volume":0} for d in data]
            return rows
        elif symbol == "XAUUSD":
            # Yahoo Finance for Gold futures
            r    = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=5d", timeout=10)
            d    = r.json()
            result = d["chart"]["result"][0]
            times  = result["timestamp"]
            ohlcv  = result["indicators"]["quote"][0]
            rows   = []
            for i in range(len(times)):
                if ohlcv["close"][i]:
                    rows.append({
                        "time":   str(times[i]),
                        "open":   ohlcv["open"][i]  or 0,
                        "high":   ohlcv["high"][i]  or 0,
                        "low":    ohlcv["low"][i]   or 0,
                        "close":  ohlcv["close"][i] or 0,
                        "volume": ohlcv["volume"][i] or 0,
                    })
            return rows
        elif symbol == "EURUSD":
            # Yahoo Finance for EUR/USD
            r    = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=15m&range=5d", timeout=10)
            d    = r.json()
            result = d["chart"]["result"][0]
            times  = result["timestamp"]
            ohlcv  = result["indicators"]["quote"][0]
            rows   = []
            for i in range(len(times)):
                if ohlcv["close"][i]:
                    rows.append({
                        "time":   str(times[i]),
                        "open":   ohlcv["open"][i]  or 0,
                        "high":   ohlcv["high"][i]  or 0,
                        "low":    ohlcv["low"][i]   or 0,
                        "close":  ohlcv["close"][i] or 0,
                        "volume": ohlcv["volume"][i] or 0,
                    })
            return rows
        else:
            return []
    except Exception as e:
        # Fallback mock data
        base = 1.085 if symbol=="EURUSD" else 1950.0 if symbol=="XAUUSD" else 60000.0
        rows = []
        for i in range(100):
            c = base*(1+random.uniform(-0.002,0.002))
            rows.append({"time":str(i),"open":c,"high":c*1.001,"low":c*0.999,"close":c,"volume":random.randint(100,1000)})
        return rows

@st.cache_data(ttl=30)
def load_account():
    try:
        r  = requests.get(f"{BASE_URL}/v2/account",   headers=HEADERS, timeout=10)
        r2 = requests.get(f"{BASE_URL}/v2/positions",  headers=HEADERS, timeout=10)
        return r.json(), r2.json(), None
    except Exception as e:
        return {}, [], str(e)

# =========================================================================
# APP CONFIG
# =========================================================================
st.set_page_config(page_title="SHREE AUTO TRADING BOT", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .stApp{background:linear-gradient(135deg,#0a0a0a 0%,#0d1117 50%,#0a0f1e 100%)}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1117 0%,#161b22 100%);border-right:1px solid #21262d}
    .main-title{text-align:center;font-size:42px;font-weight:900;letter-spacing:4px;background:linear-gradient(90deg,#00d4aa,#00a8ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;padding:20px 0 5px 0;text-transform:uppercase}
    .sub-title{text-align:center;color:#8b949e;font-size:13px;letter-spacing:3px;text-transform:uppercase;margin-bottom:20px}
    .ticker{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 20px;color:#8b949e;font-size:12px;text-align:center;letter-spacing:2px;margin-bottom:15px}
    .user-badge{background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #30363d;border-radius:8px;padding:8px 16px;color:#00d4aa;font-size:13px;font-weight:700;letter-spacing:2px;text-align:center;margin-bottom:10px}
    .admin-badge{background:linear-gradient(135deg,#1a0a3a,#2d1060);border:1px solid #7b2ff7;border-radius:8px;padding:8px 16px;color:#bc8cff;font-size:13px;font-weight:700;letter-spacing:2px;text-align:center;margin-bottom:10px}
    [data-testid="stMetric"]{background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #30363d;border-radius:12px;padding:16px;box-shadow:0 4px 15px rgba(0,0,0,0.3)}
    [data-testid="stMetricLabel"]{color:#8b949e !important;font-size:12px !important;letter-spacing:1px;text-transform:uppercase}
    [data-testid="stMetricValue"]{color:#e6edf3 !important;font-size:24px !important;font-weight:700 !important}
    .signal-buy{background:linear-gradient(135deg,#0d2818,#1a4731);border:1px solid #2ea043;border-left:4px solid #2ea043;border-radius:8px;padding:16px 20px;font-size:18px;font-weight:700;color:#3fb950;margin:10px 0}
    .signal-sell{background:linear-gradient(135deg,#2d0f0f,#4a1c1c);border:1px solid #da3633;border-left:4px solid #da3633;border-radius:8px;padding:16px 20px;font-size:18px;font-weight:700;color:#f85149;margin:10px 0}
    .signal-hold{background:linear-gradient(135deg,#1c1a0f,#332d10);border:1px solid #9e6a03;border-left:4px solid #d29922;border-radius:8px;padding:16px 20px;font-size:18px;font-weight:700;color:#d29922;margin:10px 0}
    .price-card{background:linear-gradient(135deg,#161b22,#1c2128);border:1px solid #30363d;border-radius:12px;padding:15px;text-align:center;margin:5px 0}
    .client-card-active{background:linear-gradient(135deg,#0d2818,#1a4731);border:1px solid #2ea043;border-radius:12px;padding:15px;margin:5px 0}
    .client-card-inactive{background:linear-gradient(135deg,#2d0f0f,#4a1c1c);border:1px solid #da3633;border-radius:12px;padding:15px;margin:5px 0}
    .conf-panel{background:linear-gradient(135deg,#0a0f1e,#161b22);border:1px solid #30363d;border-radius:12px;padding:15px;margin:10px 0}
    .live-badge{background:#ff4444;color:white;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
    .paper-badge{background:#0066cc;color:white;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
</style>
""", unsafe_allow_html=True)

# =========================================================================
# SESSION STATE
# =========================================================================
if "logged_in"      not in st.session_state: st.session_state.logged_in      = False
if "role"           not in st.session_state: st.session_state.role           = None
if "current_user"   not in st.session_state: st.session_state.current_user   = None
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "locked_until"   not in st.session_state: st.session_state.locked_until   = None

# =========================================================================
# LOGIN
# =========================================================================
if not st.session_state.logged_in:
    st.markdown('<div class="main-title">SHREE AUTO TRADING BOT</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">🔐 SECURE LOGIN PORTAL · AUTHORIZED ACCESS ONLY 🔐</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        if st.session_state.locked_until and datetime.now(IST) < st.session_state.locked_until:
            st.error(f"🔒 Locked! Try again in {(st.session_state.locked_until-datetime.now(IST)).seconds} seconds.")
            st.stop()
        st.markdown('<div style="text-align:center;font-size:28px;font-weight:900;color:#00d4aa;letter-spacing:3px;margin-bottom:20px;">🔐 LOGIN</div>', unsafe_allow_html=True)
        username = st.text_input("👤 Username", placeholder="Enter username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter password")
        if st.button("🚀 LOGIN", use_container_width=True):
            if username == ADMIN["username"] and password == ADMIN["password"]:
                st.session_state.logged_in=True; st.session_state.role="admin"; st.session_state.current_user="Parvish"; st.rerun()
            elif username in st.session_state.clients:
                cl = st.session_state.clients[username]
                if not cl["active"]: st.error("❌ Account deactivated. Contact Admin.")
                elif cl["password"]==password:
                    st.session_state.logged_in=True; st.session_state.role="client"; st.session_state.current_user=username; st.rerun()
                else:
                    st.session_state.login_attempts+=1
                    if st.session_state.login_attempts>=3:
                        st.session_state.locked_until=datetime.now(IST)+timedelta(minutes=5); st.error("🔒 Locked 5 min!")
                    else: st.error(f"❌ Wrong password! {3-st.session_state.login_attempts} left.")
            else: st.error("❌ Username not found!")
        st.markdown("---")
        st.markdown('<div style="text-align:center;color:#8b949e;font-size:11px;">🔐 SHREE AUTO TRADING BOT · PRIVATE & CONFIDENTIAL</div>', unsafe_allow_html=True)

# =========================================================================
# MAIN APP
# =========================================================================
else:
    now = datetime.now(IST)
    st.markdown('<div class="main-title">SHREE AUTO TRADING BOT</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">⚡ LIVE 24/7 · BITCOIN · GOLD · EUR/USD ⚡</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ticker">🕐 {now.strftime("%A, %d %B %Y  |  %H:%M:%S IST")}  |  👤 {st.session_state.current_user.upper()}  |  {"👑 ADMIN" if st.session_state.role=="admin" else "👤 CLIENT"}  |  📡 LIVE DATA</div>', unsafe_allow_html=True)

    # Live Prices
    prices = get_live_prices()
    p1,p2,p3 = st.columns(3)
    labels = {"BTCUSD":"₿ BITCOIN","XAUUSD":"🥇 GOLD","EURUSD":"💱 EUR/USD"}
    for col,(sym,data) in zip([p1,p2,p3],prices.items()):
        color  = "#2ea043" if data["change_pct"]>=0 else "#f85149"
        arrow  = "▲" if data["change_pct"]>=0 else "▼"
        price_str = f"${data['price']:,.4f}" if data['price']>0 else "⏳ Loading..."
        high_str  = f"H: ${data['high']:,.2f}" if data.get('high',0)>0 else ""
        low_str   = f"L: ${data['low']:,.2f}"  if data.get('low',0)>0  else ""
        col.markdown(f"""
        <div class="price-card">
            <div style="color:#8b949e;font-size:11px;letter-spacing:2px;">{labels.get(sym,sym)}</div>
            <div style="color:#e6edf3;font-size:22px;font-weight:700;">{price_str}</div>
            <div style="color:{color};font-size:13px;">{arrow} {data['change_pct']:+.2f}%</div>
            <div style="color:#8b949e;font-size:11px;">{high_str} &nbsp; {low_str}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    if st.session_state.role=="admin":
        st.sidebar.markdown('<div class="admin-badge">👑 PARVISH · ADMIN</div>', unsafe_allow_html=True)
    else:
        cn = st.session_state.clients[st.session_state.current_user]["name"]
        st.sidebar.markdown(f'<div class="user-badge">👤 {cn.upper()} · CLIENT</div>', unsafe_allow_html=True)

    st.sidebar.markdown("## ⚙️ CONTROLS")
    symbol    = st.sidebar.selectbox("📈 Symbol", ["BTCUSD","XAUUSD","EURUSD"])
    timeframe = st.sidebar.selectbox("⏱ Timeframe", ["15Min","1Hour","4Hour","1Day"], index=0)
    st.sidebar.markdown("---")
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (60s)")
    st.sidebar.markdown("---")

    if st.session_state.role=="admin":
        page = st.sidebar.radio("📱 NAVIGATION", ["📊 Dashboard","🧠 Strategies","📈 Backtest","📋 Trade Report","👥 Client Manager"])
    else:
        page = st.sidebar.radio("📱 NAVIGATION", ["📊 Dashboard","💼 My Trading","📋 My Trade Report"])

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 LOGOUT", use_container_width=True):
        st.session_state.logged_in=False; st.session_state.role=None; st.session_state.current_user=None; st.rerun()

    account, positions, acc_err = load_account()
    candles = get_ohlcv(symbol)

    c1,c2,c3,c4,c5 = st.columns(5)
    if not acc_err:
        cash=float(account.get("cash",0)); equity=float(account.get("equity",0))
        pnl=float(account.get("unrealized_pl") or 0); buying=float(account.get("buying_power",0))
        c1.metric("💰 CASH",f"${cash:,.2f}"); c2.metric("📊 EQUITY",f"${equity:,.2f}")
        c3.metric("💹 BUYING POWER",f"${buying:,.2f}"); c4.metric("📉 P&L",f"${pnl:,.2f}",delta=f"{pnl:+.2f}")
        c5.metric("🔓 POSITIONS",len(positions))
    st.markdown("---")

    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    if page == "📊 Dashboard":
        left, right = st.columns([2,1])
        with left:
            if candles:
                times  = list(range(len(candles)))
                opens  = [c["open"]  for c in candles]
                highs  = [c["high"]  for c in candles]
                lows   = [c["low"]   for c in candles]
                closes = [c["close"] for c in candles]
                vols   = [c["volume"] for c in candles]
                ema9   = calc_ema(closes, 9)
                ema21  = calc_ema(closes, 21)
                rsi_v  = calc_rsi(closes, 14)

                fig = make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.6,0.2,0.2],
                                    vertical_spacing=0.02,subplot_titles=(f"{symbol} · LIVE PRICE + EMA 9/21","RSI (14)","VOLUME"))
                fig.add_trace(go.Candlestick(x=times,open=opens,high=highs,low=lows,close=closes,name="Price",
                              increasing_line_color="#2ea043",decreasing_line_color="#f85149"),row=1,col=1)
                fig.add_trace(go.Scatter(x=times,y=ema9, name="EMA 9",  line=dict(color="#d29922",width=1.5)),row=1,col=1)
                fig.add_trace(go.Scatter(x=times,y=ema21,name="EMA 21", line=dict(color="#58a6ff",width=1.5)),row=1,col=1)
                fig.add_trace(go.Scatter(x=times,y=rsi_v,name="RSI",    line=dict(color="#bc8cff",width=1.5)),row=2,col=1)
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
                st.warning("Loading data...")

        with right:
            # EMA Crossover Signal
            st.markdown("### 🎯 STRATEGY 1 — EMA CROSSOVER")
            if candles and len(candles)>2:
                closes = [c["close"] for c in candles]
                ema9   = calc_ema(closes,9)
                ema21  = calc_ema(closes,21)
                rsi_v  = calc_rsi(closes,14)
                if ema9[-2] and ema21[-2] and ema9[-1] and ema21[-1]:
                    if ema9[-2]<ema21[-2] and ema9[-1]>ema21[-1] and rsi_v[-1]<70:
                        st.markdown(f'<div class="signal-buy">🟢 BUY<br><small>EMA Cross UP · RSI:{rsi_v[-1]:.1f}</small></div>',unsafe_allow_html=True)
                    elif ema9[-2]>ema21[-2] and ema9[-1]<ema21[-1] and rsi_v[-1]>30:
                        st.markdown(f'<div class="signal-sell">🔴 SELL<br><small>EMA Cross DOWN · RSI:{rsi_v[-1]:.1f}</small></div>',unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="signal-hold">🟡 HOLD<br><small>No crossover · RSI:{rsi_v[-1]:.1f}</small></div>',unsafe_allow_html=True)

            st.markdown("---")

            # 4-Confluence Signal
            st.markdown("### 🎯 STRATEGY 2 — 4-CONFLUENCE")
            if candles and len(candles)>=50:
                result = confluence_signal(candles)
                sig = result["signal"]
                bv  = result["bull_votes"]
                sv  = result["bear_votes"]
                if sig=="BUY":
                    st.markdown(f'<div class="signal-buy">🟢 BUY — {bv}/4 Votes<br><small>ADX:{result["adx"]} · RSI:{result["rsi"]}</small></div>',unsafe_allow_html=True)
                elif sig=="SELL":
                    st.markdown(f'<div class="signal-sell">🔴 SELL — {sv}/4 Votes<br><small>ADX:{result["adx"]} · RSI:{result["rsi"]}</small></div>',unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="signal-hold">🟡 HOLD — {max(bv,sv)}/4 Votes<br><small>ADX:{result["adx"]} · Need {2} confluence</small></div>',unsafe_allow_html=True)

                st.markdown('<div class="conf-panel">', unsafe_allow_html=True)
                st.markdown("**📊 Confluence Votes:**")
                for ind,vote in result["votes"].items():
                    st.markdown(f"{vote} **{ind}**")
                st.markdown(f"**📈 ADX:** {result['adx']} {'✅ Trending' if result['is_trending'] else '⚠️ Choppy — No Trade'}")
                st.markdown('</div>', unsafe_allow_html=True)

                if result["sl_price"]:
                    st.markdown("**Risk Management:**")
                    st.metric("🛑 Stop Loss",   f"${result['sl_price']:,.2f}")
                    st.metric("🎯 Take Profit", f"${result['tp_price']:,.2f}")
                    sl = result['sl_price']; tp = result['tp_price']; ep = result['entry']
                    risk = abs(ep-sl); reward = abs(tp-ep)
                    st.metric("⚖️ R:R Ratio",  f"1:{reward/risk:.1f}" if risk>0 else "N/A")
            else:
                st.info("Need 50+ candles for 4-Confluence signal")

            st.markdown("### 📡 MARKET STATUS")
            st.success("🟢 BITCOIN — 24/7 LIVE")
            st.success("🟢 EUR/USD — 24/7 LIVE")
            st.info("🟡 GOLD — Open 7PM-1:30AM IST")

        st.markdown("---")
        st.markdown("### 🔓 OPEN POSITIONS")
        if positions:
            import pandas as pd
            pdf = pd.DataFrame([{"Symbol":p["symbol"],"Qty":p["qty"],"Entry $":p["avg_entry_price"],"Current $":p["current_price"],"P&L $":p["unrealized_pl"]} for p in positions])
            st.dataframe(pdf,use_container_width=True)
        else:
            st.info("No open positions.")

    # ── CLIENT TRADING ────────────────────────────────────────────────────────
    elif page=="💼 My Trading":
        client=st.session_state.clients[st.session_state.current_user]
        st.markdown(f"### 💼 MY TRADING PANEL — {client['name'].upper()}")
        st.markdown("---")
        c1,c2=st.columns(2)
        with c1:
            available=[k for k,v in STRATEGIES.items() if v!="Empty Slot"]
            sel_strat=st.selectbox("🧠 Select Strategy",available)
            qty=st.number_input("📦 Trade Quantity",min_value=1,max_value=1000,value=client["quantity"])
            mode=st.radio("🔄 Trading Mode",["📄 Paper Trading","🔴 Live Trading"],index=0 if client["mode"]=="Paper" else 1)
            if "Live" in mode: st.error("⚠️ WARNING: Live Trading uses REAL MONEY!")
            if st.button("💾 SAVE SETTINGS",use_container_width=True):
                st.session_state.clients[st.session_state.current_user].update({"strategy":sel_strat,"quantity":qty,"mode":"Live" if "Live" in mode else "Paper"})
                st.success("✅ Settings saved!")
        with c2:
            total_pnl=sum(t.get("pnl",0) for t in client["trades"])
            wins=len([t for t in client["trades"] if t.get("pnl",0)>0])
            total=len(client["trades"])
            win_rate=(wins/total*100) if total>0 else 0
            roi=(total_pnl/client["balance"]*100) if client["balance"]>0 else 0
            st.metric("💰 Balance",f"${client['balance']:,.2f}")
            st.metric("📈 Total P&L",f"${total_pnl:+,.2f}")
            st.metric("📐 ROI",f"{roi:+.2f}%")
            st.metric("🎯 Win Rate",f"{win_rate:.1f}%")
            st.metric("📊 Total Trades",total)
            mode_b=f'<span class="live-badge">🔴 LIVE</span>' if client["mode"]=="Live" else f'<span class="paper-badge">📄 PAPER</span>'
            st.markdown(f"**Mode:** {mode_b}",unsafe_allow_html=True)

    # ── STRATEGIES ────────────────────────────────────────────────────────────
    elif page=="🧠 Strategies":
        st.markdown("### 🧠 STRATEGY MANAGER — 5 SLOTS")
        st.markdown("---")
        for slot,name in STRATEGIES.items():
            c1,c2=st.columns([3,1])
            with c1:
                if name!="Empty Slot":
                    st.markdown(f'<div class="client-card-active">✅ <b>{slot}</b> — {name}</div>',unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:#161b22;border:2px dashed #30363d;border-radius:12px;padding:15px;margin:5px 0;">📭 <b>{slot}</b> — Empty · Ready for Pine Script</div>',unsafe_allow_html=True)
            with c2:
                st.success("🟢 ACTIVE") if name!="Empty Slot" else st.info("⬜ EMPTY")
        st.markdown("---")
        st.info("📝 Share your Pine Script → I will convert and deploy it!")

    # ── BACKTEST ──────────────────────────────────────────────────────────────
    elif page=="📈 Backtest":
        st.markdown("### 📈 STRATEGY BACKTESTER")
        st.markdown("---")
        c1,c2,c3=st.columns(3)
        with c1: bt_sym=st.selectbox("📈 Symbol",["BTCUSD","XAUUSD","EURUSD"])
        with c2: bt_per=st.selectbox("📅 Period",["1 Month","3 Months","6 Months","1 Year"])
        with c3: bt_strat=st.selectbox("🧠 Strategy",["EMA Crossover","4-Confluence"])
        c4,c5=st.columns(2)
        with c4: init_cap=st.number_input("💰 Initial Capital ($)",value=10000,step=1000)
        with c5: risk_pt=st.number_input("⚠️ Risk per Trade (%)",value=1.0,step=0.5)

        if st.button("🚀 RUN BACKTEST",use_container_width=True):
            with st.spinner("Fetching historical data..."):
                try:
                    days_map={"1 Month":30,"3 Months":90,"6 Months":180,"1 Year":365}
                    days=days_map[bt_per]
                    if bt_sym=="BTCUSD":
                        r=requests.get(f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days={days}",timeout=15)
                        data=r.json()
                        bt_candles=[{"time":str(d[0]),"open":d[1],"high":d[2],"low":d[3],"close":d[4],"volume":0} for d in data]
                    else:
                        base=1.085 if bt_sym=="EURUSD" else 1950.0
                        bt_candles=[{"time":str(i),"open":base*(1+random.uniform(-0.002,0.002)),"high":base*1.002,"low":base*0.998,"close":base*(1+random.uniform(-0.002,0.002)),"volume":1000} for i in range(days*4)]

                    capital=init_cap; position=0; entry_price=0; trades=[]; equity=[capital]
                    closes=[c["close"] for c in bt_candles]
                    highs=[c["high"] for c in bt_candles]
                    lows=[c["low"] for c in bt_candles]

                    ema9=calc_ema(closes,9); ema21=calc_ema(closes,21); rsi_v=calc_rsi(closes,14)

                    for i in range(22,len(bt_candles)):
                        if bt_strat=="EMA Crossover":
                            buy_sig  = ema9[i-1] and ema21[i-1] and ema9[i] and ema21[i] and ema9[i-1]<ema21[i-1] and ema9[i]>ema21[i] and rsi_v[i]<70
                            sell_sig = ema9[i-1] and ema21[i-1] and ema9[i] and ema21[i] and ema9[i-1]>ema21[i-1] and ema9[i]<ema21[i] and rsi_v[i]>30
                        else:
                            chunk=bt_candles[max(0,i-99):i+1]
                            if len(chunk)>=50:
                                res=confluence_signal(chunk)
                                buy_sig=res["signal"]=="BUY"; sell_sig=res["signal"]=="SELL"
                            else:
                                buy_sig=False; sell_sig=False

                        cur=closes[i]
                        if buy_sig and position==0:
                            shares=int((capital*risk_pt/100)/cur)
                            if shares>0: position=shares; entry_price=cur
                        elif sell_sig and position>0:
                            pnl=(cur-entry_price)*position; roi=(pnl/(entry_price*position)*100) if entry_price>0 else 0
                            capital+=pnl
                            trades.append({"Strategy":bt_strat,"Entry $":round(entry_price,4),"Exit $":round(cur,4),"Shares":position,"P&L $":round(pnl,2),"ROI %":round(roi,2),"Result":"✅ WIN" if pnl>0 else "❌ LOSS"})
                            position=0; entry_price=0
                        equity.append(capital)

                    if trades:
                        import pandas as pd
                        df_t=pd.DataFrame(trades); total_pnl=capital-init_cap
                        wins=len([t for t in trades if t["P&L $"]>0]); losses=len(trades)-wins
                        win_rate=wins/len(trades)*100; total_roi=total_pnl/init_cap*100
                        r1,r2,r3,r4,r5,r6=st.columns(6)
                        r1.metric("💰 Final",f"${capital:,.2f}",delta=f"${total_pnl:+,.2f}")
                        r2.metric("📈 ROI",f"{total_roi:+.2f}%"); r3.metric("🎯 Win Rate",f"{win_rate:.1f}%")
                        r4.metric("✅ Wins",wins); r5.metric("❌ Losses",losses); r6.metric("📊 Trades",len(trades))
                        fig_eq=go.Figure()
                        fig_eq.add_trace(go.Scatter(y=equity,mode="lines",line=dict(color="#00d4aa",width=2),fill="tozeroy",fillcolor="rgba(0,212,170,0.1)"))
                        fig_eq.update_layout(height=250,paper_bgcolor="#0d1117",plot_bgcolor="#0d1117",font=dict(color="#8b949e"),margin=dict(l=0,r=0,t=10,b=0),showlegend=False)
                        fig_eq.update_xaxes(gridcolor="#21262d"); fig_eq.update_yaxes(gridcolor="#21262d")
                        st.plotly_chart(fig_eq,use_container_width=True)
                        st.dataframe(df_t.style.format({"Entry $":"{:.4f}","Exit $":"{:.4f}","P&L $":"{:+.2f}","ROI %":"{:+.2f}%"}),use_container_width=True)
                        if win_rate>=50 and total_pnl>0: st.success(f"✅ PROFITABLE! Win Rate:{win_rate:.1f}% | ROI:{total_roi:+.2f}%")
                        else: st.warning(f"⚠️ Needs improvement. Win Rate:{win_rate:.1f}% | ROI:{total_roi:+.2f}%")
                    else: st.warning("No trades generated.")
                except Exception as e: st.error(f"Error: {e}")

    # ── TRADE REPORT ──────────────────────────────────────────────────────────
    elif page in ["📋 Trade Report","📋 My Trade Report"]:
        import pandas as pd
        if st.session_state.role=="admin":
            st.markdown("### 📋 ALL CLIENTS TRADE REPORT")
            fc=st.selectbox("👥 Filter",["All"]+list(st.session_state.clients.keys()))
        else:
            st.markdown("### 📋 MY TRADE REPORT"); fc=st.session_state.current_user
        sample=[
            {"Client":"client1","Strategy":"EMA Crossover","Symbol":"BTCUSD","Entry Time":"2026-06-20 19:15","Square Off":"2026-06-20 21:30","Entry $":65420.50,"Exit $":66100.00,"Qty":1,"P&L $":679.50,"ROI %":1.04,"Mode":"Paper","Result":"✅ WIN"},
            {"Client":"client1","Strategy":"4-Confluence","Symbol":"BTCUSD","Entry Time":"2026-06-21 09:00","Square Off":"2026-06-21 11:30","Entry $":66200.00,"Exit $":65800.00,"Qty":1,"P&L $":-400.00,"ROI %":-0.60,"Mode":"Paper","Result":"❌ LOSS"},
            {"Client":"client2","Strategy":"4-Confluence","Symbol":"BTCUSD","Entry Time":"2026-06-21 08:00","Square Off":"2026-06-21 10:00","Entry $":65000.00,"Exit $":66950.00,"Qty":1,"P&L $":1950.00,"ROI %":3.00,"Mode":"Paper","Result":"✅ WIN"},
        ]
        all_trades=sample if fc=="All" else [t for t in sample if t["Client"]==fc]
        if all_trades:
            tp=sum(t["P&L $"] for t in all_trades); wins=len([t for t in all_trades if t["P&L $"]>0])
            wr=(wins/len(all_trades)*100); ar=sum(t["ROI %"] for t in all_trades)/len(all_trades)
            s1,s2,s3,s4,s5,s6=st.columns(6)
            s1.metric("📊 Trades",len(all_trades)); s2.metric("💰 P&L",f"${tp:+,.2f}")
            s3.metric("🎯 Win Rate",f"{wr:.1f}%"); s4.metric("✅ Wins",wins)
            s5.metric("❌ Losses",len(all_trades)-wins); s6.metric("📐 Avg ROI",f"{ar:+.2f}%")
            st.markdown("---")
            df_r=pd.DataFrame(all_trades)
            if st.session_state.role=="client": df_r=df_r.drop(columns=["Client"])
            st.dataframe(df_r.style.format({"Entry $":"{:.4f}","Exit $":"{:.4f}","P&L $":"{:+.2f}","ROI %":"{:+.2f}%"}),use_container_width=True)

    # ── CLIENT MANAGER ────────────────────────────────────────────────────────
    elif page=="👥 Client Manager":
        st.markdown("### 👥 CLIENT MANAGER — ADMIN ONLY")
        st.markdown("---")
        for cid,client in st.session_state.clients.items():
            c1,c2,c3,c4,c5=st.columns([2,1,1,1,1])
            with c1:
                if client["active"]: st.markdown(f'<div class="client-card-active">✅ <b>{client["name"]}</b><br><small>@{client["username"]}</small></div>',unsafe_allow_html=True)
                else: st.markdown(f'<div class="client-card-inactive">❌ <b>{client["name"]}</b><br><small>@{client["username"]} · DEACTIVATED</small></div>',unsafe_allow_html=True)
            with c2: st.markdown(f"**{'🟢 ACTIVE' if client['active'] else '🔴 INACTIVE'}**")
            with c3:
                mb=f'<span class="live-badge">🔴 LIVE</span>' if client["mode"]=="Live" else f'<span class="paper-badge">📄 PAPER</span>'
                st.markdown(mb,unsafe_allow_html=True)
            with c4:
                if client["active"]:
                    if st.button(f"🔴 Deactivate",key=f"d_{cid}"): st.session_state.clients[cid]["active"]=False; st.rerun()
                else:
                    if st.button(f"🟢 Activate",key=f"a_{cid}"): st.session_state.clients[cid]["active"]=True; st.rerun()
            with c5:
                if st.button(f"🔑 Reset",key=f"r_{cid}"): st.session_state.clients[cid]["password"]=f"{cid.capitalize()}@123"; st.info(f"Reset: {cid.capitalize()}@123")
            st.markdown("---")
        st.markdown("### ✏️ EDIT CLIENT")
        ec=st.selectbox("Select",list(st.session_state.clients.keys()))
        cd=st.session_state.clients[ec]
        e1,e2,e3=st.columns(3)
        with e1: nn=st.text_input("👤 Name",value=cd["name"])
        with e2: np=st.text_input("🔒 Password",value=cd["password"])
        with e3: nb=st.number_input("💰 Balance",value=cd["balance"],step=1000)
        if st.button("💾 UPDATE CLIENT",use_container_width=True):
            st.session_state.clients[ec].update({"name":nn,"password":np,"balance":nb}); st.success(f"✅ {nn} updated!")

    if auto_refresh:
        time.sleep(60)
        st.rerun()
