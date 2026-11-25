import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Quant Options & Gold Radar", page_icon="📊", layout="centered")
st.title("📊 لوحة التحليل الكمي الذكية")
st.caption("عزل آلي للمؤشر + تحليل الزمن والسيولة + هندسة الأوبشن")

ASSETS_LIST = ["NVDA", "TSLA", "AMD", "AAPL", "MSFT", "META", "AMZN", "GLD", "SLV", "SPY", "QQQ", "SOXX", "IWM", "UUP", "BTC-USD", "ETH-USD"]
BENCHMARKS_POOL = ["SPY", "QQQ", "SOXX", "IWM", "UUP", "BTC-USD"]
Z_CHOICES = ["AUTO (تلقائي ذكي)"] + BENCHMARKS_POOL

col1, col2, col3 = st.columns(3)
with col1:
    asset_x = st.selectbox("الأصل الأول (X)", ASSETS_LIST, index=0)
with col2:
    asset_y = st.selectbox("الأصل الثاني (Y - للتحوط)", ASSETS_LIST, index=7)
with col3:
    market_z_choice = st.selectbox("المؤشر المرجعي (Z)", Z_CHOICES, index=0)

custom_x = st.text_input("أو اكتب رمز سهم مخصص هنا (اختياري):", value="")
if custom_x.strip():
    asset_x = custom_x.strip().upper()

if st.button("🚀 تحديث التحليل والرادار الآن", use_container_width=True, type="primary"):
    st.rerun()

with st.spinner("⏳ جاري سحب البيانات وحساب المصفوفات..."):
    radar_base = ["SPY", "QQQ", "GLD", "SLV", "TSLA", "NVDA", "AAPL", "BTC-USD"]
    all_tickers = list(dict.fromkeys([asset_x, asset_y] + BENCHMARKS_POOL + radar_base))
    if market_z_choice != "AUTO (تلقائي ذكي)" and market_z_choice not in all_tickers:
        all_tickers.append(market_z_choice)

    raw_data = yf.download(all_tickers, period="45d", interval="1d", progress=False)
    close_df = raw_data['Close'].dropna(how='all').tail(30)
    vol_df = raw_data['Volume'].dropna(how='all').tail(30)

    def calc_volume_flow(ticker):
        c = close_df[ticker].ffill()
        v = vol_df[ticker].ffill()
        log_ret = np.log(c / c.shift(1))
        vol_ratio = (v / v.mean()).fillna(1.0).replace(0, 1.0)
        return (log_ret * vol_ratio).dropna()

    flow_x = calc_volume_flow(asset_x)
    flow_y = calc_volume_flow(asset_y)

    if market_z_choice == "AUTO (تلقائي ذكي)":
        best_z = "SPY"
        best_corr_abs = -1.0
        for b in BENCHMARKS_POOL:
            if b != asset_x and b != asset_y and b in close_df.columns:
                flow_b = calc_volume_flow(b)
                temp_df = pd.DataFrame({'X': flow_x, 'B': flow_b}).dropna()
                if len(temp_df) > 10:
                    c_val = abs(float(temp_df['X'].corr(temp_df['B'])))
                    if c_val > best_corr_abs:
                        best_corr_abs = c_val
                        best_z = b
        market_z = best_z
        z_label_note = f"{market_z} (آلي | ارتباط: {best_corr_abs:.2f})"
    else:
        market_z = market_z_choice
        z_label_note = f"{market_z} (يدوي)"

    flow_z = calc_volume_flow(market_z)
    aligned = pd.DataFrame({'X': flow_x, 'Y': flow_y, 'Z': flow_z}).dropna()

    r_xy = float(aligned['X'].corr(aligned['Y']))
    r_xz = float(aligned['X'].corr(aligned['Z']))
    r_yz = float(aligned['Y'].corr(aligned['Z']))
    partial_corr = float((r_xy - (r_xz * r_yz)) / np.sqrt((1 - r_xz**2) * (1 - r_yz**2)))

    prices_x = close_df[asset_x].dropna().tail(30)
    curr_price = float(prices_x.iloc[-1])
    time_series = pd.Series(np.arange(1, len(prices_x) + 1), index=prices_x.index)
    
    std_slope_x = float(prices_x.corr(time_series))
    r_squared_x = float(std_slope_x ** 2)
    
    slope, intercept = np.polyfit(time_series.values, prices_x.values, 1)
    trend_line = slope * time_series.values + intercept
    std_err = float(np.std(prices_x.values - trend_line))
    ann_vol = float(aligned['X'].std() * np.sqrt(252))

    step = 5.0 if curr_price > 200 else (2.5 if curr_price > 50 else 1.0)
    round_strike = lambda val: round(val / step) * step

    if r_squared_x > 0.75 and ann_vol < 0.45:
        rec_dte = "14 - 21 يوم (زخم سريع)"
    elif ann_vol >= 0.45:
        rec_dte = "30 - 45 يوم (حماية من Theta)"
    else:
        rec_dte = "21 - 30 يوم (فترة أمان)"

    if std_slope_x > 0.60 and r_squared_x > 0.60:
        opt_type = "✅ شراء عقد CALL (اتجاه مؤسسي صاعد)"
        safe_strike = f"${round_strike(curr_price - std_err*0.5):.1f} (ITM آمن)"
        target_strike = f"${round_strike(curr_price + std_err*1.2):.1f} (OTM هدف)"
        stop_loss = f"كسر ${curr_price - std_err*1.5:.2f}"
    elif std_slope_x < -0.60 and r_squared_x > 0.60:
        opt_type = "🔻 شراء عقد PUT (اتجاه مؤسسي هابط)"
        safe_strike = f"${round_strike(curr_price + std_err*0.5):.1f} (ITM آمن)"
        target_strike = f"${round_strike(curr_price - std_err*1.2):.1f} (OTM هدف)"
        stop_loss = f"اختراق ${curr_price + std_err*1.5:.2f}"
    else:
        opt_type = "⚠️ تجنب الأوبشن حالياً (تذبذب / ضعف R²)"
        safe_strike = f"اختراق ${round_strike(float(trend_line[-1]) + std_err):.1f} للـ CALL"
        target_strike = f"كسر ${round_strike(float(trend_line[-1]) - std_err):.1f} للـ PUT"
        stop_loss = "انتظار التأكيد"

    hedge_status = f"🛡️ ممتاز للتحوط العكسي ({partial_corr:.2f})" if partial_corr < -0.40 else f"⚖️ ارتباط محايد/طردي ({partial_corr:.2f})"

    st.subheader("🎯 بطاقة هندسة عقود الأوبشن")
    m1, m2, m3 = st.columns(3)
    m1.metric(f"سعر {asset_x}", f"${curr_price:.2f}")
    m2.metric("كفاءة الزمن (R²)", f"{r_squared_x:.1%}", f"ميل: {std_slope_x:+.2f}")
    m3.metric("الارتباط الحدي", f"{partial_corr:.2f}", market_z)

    st.info(f"**القرار الآلي:** {opt_type}")

    options_df = pd.DataFrame({
        "البند": ["المؤشر المعزول (Z)", "السترايك المحافظ (Safe)", "السترايك المستهدف (Target)", "مدة الانتهاء (DTE)", "وقف الخسارة الكمي", f"التحوط بـ ({asset_y})"],
        "القيمة": [z_label_note, safe_strike, target_strike, rec_dte, stop_loss, hedge_status]
    })
    st.table(options_df)

    st.subheader("📈 قناة الزمن والانحراف المعياري")
    dates_str = prices_x.index.strftime('%b %d')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates_str, y=trend_line + 1.5*std_err, mode='lines', line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=dates_str, y=trend_line - 1.5*std_err, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(33, 150, 243, 0.15)', name='Whale Zone (±1.5 Std)'))
    fig.add_trace(go.Scatter(x=dates_str, y=trend_line, mode='lines', line=dict(color='#d32f2f', dash='dash', width=2), name='Time Trend'))
    fig.add_trace(go.Scatter(x=dates_str, y=prices_x.values, mode='lines+markers', line=dict(color='#1a237e', width=3), name=f'{asset_x} Price'))
    fig.update_layout(
        title=dict(text=f"{asset_x} Time Channel (R² = {r_squared_x:.1%})", x=0.5, xanchor='center'),
        xaxis=dict(type='category', tickangle=-45, nticks=8),
        template="plotly_white", height=380, margin=dict(l=10, r=10, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📡 رادار الفرص الشامل لكل الأسواق")
    radar_rows = []
    for sym in radar_base:
        c_s = close_df[sym].dropna().tail(20)
        v_s = vol_df[sym].dropna().tail(20)
        cp = float(c_s.iloc[-1])
        z_sc = float((cp - c_s.mean()) / c_s.std())
        rel_v = float((v_s.iloc[-1] / v_s.mean()) * 100) if v_s.mean() > 0 else 100.0
        if z_sc > 2.0 and rel_v > 130:
            sig = "🔥 تشبع شرائي (PUT)"
        elif z_sc < -2.0 and rel_v > 130:
            sig = "💎 تشبع بيعي (CALL)"
        elif 0.8 < z_sc < 1.8 and rel_v > 120:
            sig = "🚀 اختراق صحي (CALL)"
        else:
            sig = "⚖️ متوازن"
        radar_rows.append({"Asset": sym, "Price": f"${cp:.2f}", "Z-Score": round(z_sc, 2), "Vol%": f"{rel_v:.0f}%", "Signal": sig})
    st.dataframe(pd.DataFrame(radar_rows), use_container_width=True, hide_index=True)
