import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Global Quant Matrix", page_icon="🌐", layout="wide")
st.title("🌐 المصفوفة الكمية الشاملة لجميع الأسواق العالمية")
st.caption("بحث حر لأي رمز مالي + ربط آلي بالمؤشر المرجعي (تاسي / الدولار / ناسداك / بيتكوين) + معايرة التذبذب")

QUICK_X = ["NVDA", "TSLA", "AAPL", "GLD", "GC=F", "2222.SR", "1120.SR", "^TASI.SR", "EURUSD=X", "GBPUSD=X", "USDJPY=X", "BTC-USD", "ETH-USD"]
QUICK_Y = ["GLD", "UUP", "SPY", "^TASI.SR", "EURUSD=X", "USDJPY=X", "BTC-USD", "SLV", "TLT"]
BENCHMARKS_POOL = ["SPY", "QQQ", "SOXX", "IWM", "UUP", "DX-Y.NYB", "^TASI.SR", "BTC-USD"]
QUICK_Z = ["AUTO (تلقائي ذكي حسب السوق)"] + BENCHMARKS_POOL

c1, c2, c3 = st.columns(3)
with c1:
    sel_x = st.selectbox("اختر الأصل الأول (X):", QUICK_X, index=0)
    custom_x = st.text_input("أو اكتب أي رمز عالمي لـ (X):", placeholder="مثال: 4001.SR أو XAUUSD=X أو AMZN")
    asset_x = custom_x.strip().upper() if custom_x.strip() else sel_x

with c2:
    sel_y = st.selectbox("اختر أصل التحوط / المقارنة (Y):", QUICK_Y, index=0)
    custom_y = st.text_input("أو اكتب أي رمز عالمي لـ (Y):", placeholder="مثال: DXY أو 1180.SR أو GBPJPY=X")
    asset_y = custom_y.strip().upper() if custom_y.strip() else sel_y

with c3:
    sel_z = st.selectbox("المؤشر المرجعي المعزول (Z):", QUICK_Z, index=0)
    custom_z = st.text_input("أو اكتب مؤشراً مرجعياً مخصصاً لـ (Z):", placeholder="مثال: ^GSPC أو ^IXIC أو ^TASI.SR")
    market_z_choice = custom_z.strip().upper() if custom_z.strip() else sel_z

if st.button("🚀 تشغيل التحليل الكمي الشامل", use_container_width=True, type="primary"):
    st.rerun()

with st.spinner(f"⏳ جاري تحليل ({asset_x}) ومقارنته مع ({asset_y}) وعزل ضوضاء السوق..."):
    try:
        radar_base = ["SPY", "QQQ", "GLD", "2222.SR", "1120.SR", "^TASI.SR", "EURUSD=X", "USDJPY=X", "BTC-USD"]
        all_tickers = list(dict.fromkeys([asset_x, asset_y] + BENCHMARKS_POOL + radar_base))
        if market_z_choice != "AUTO (تلقائي ذكي حسب السوق)" and market_z_choice not in all_tickers:
            all_tickers.append(market_z_choice)

        raw_data = yf.download(all_tickers, period="50d", interval="1d", progress=False)
        close_df = raw_data['Close'].dropna(how='all').tail(30)
        vol_df = raw_data['Volume'].dropna(how='all').tail(30)

        if asset_x not in close_df.columns or close_df[asset_x].dropna().empty:
            st.error(f"❌ لم يتم العثور على بيانات للرمز ({asset_x}). تأكد من كتابة الرمز بصيغة Yahoo Finance الصحيحة.")
            st.stop()

        def calc_volume_flow(ticker):
            c = close_df[ticker].ffill()
            v = vol_df[ticker].ffill()
            log_ret = np.log(c / c.shift(1))
            if v.isna().all() or v.mean() == 0:
                return log_ret.dropna()
            vol_ratio = (v / v.mean()).fillna(1.0).replace(0, 1.0)
            return (log_ret * vol_ratio).dropna()

        flow_x = calc_volume_flow(asset_x)
        flow_y = calc_volume_flow(asset_y)

        if market_z_choice == "AUTO (تلقائي ذكي حسب السوق)":
            if asset_x.endswith(".SR") and asset_x != "^TASI.SR" and "^TASI.SR" in close_df.columns:
                market_z = "^TASI.SR"
                market_tag = "السوق السعودي (تاسي)"
            elif asset_x.endswith("=X"):
                market_z = "DX-Y.NYB" if "DX-Y.NYB" in close_df.columns and not close_df["DX-Y.NYB"].dropna().empty else "UUP"
                market_tag = "سوق الفوركس (مؤشر الدولار)"
            elif asset_x.endswith("-USD") and asset_x != "BTC-USD" and "BTC-USD" in close_df.columns:
                market_z = "BTC-USD"
                market_tag = "سوق الكريبتو (البيتكوين)"
            else:
                best_z = "SPY"
                best_corr_abs = -1.0
                for b in ["SPY", "QQQ", "SOXX", "IWM", "UUP"]:
                    if b != asset_x and b != asset_y and b in close_df.columns:
                        temp_df = pd.DataFrame({'X': flow_x, 'B': calc_volume_flow(b)}).dropna()
                        if len(temp_df) > 10:
                            c_val = abs(float(temp_df['X'].corr(temp_df['B'])))
                            if c_val > best_corr_abs:
                                best_corr_abs = c_val
                                best_z = b
                market_z = best_z
                market_tag = "الأسواق العالمية"

            temp_z = pd.DataFrame({'X': flow_x, 'Z': calc_volume_flow(market_z)}).dropna()
            z_corr = abs(float(temp_z['X'].corr(temp_z['Z']))) if len(temp_z) > 5 else 0.0
            z_label_note = f"{market_z} ({market_tag} | ارتباط: {z_corr:.2f})"
        else:
            market_z = market_z_choice
            z_label_note = f"{market_z} (اختيار يدوي)"
        flow_z = calc_volume_flow(market_z)
        aligned = pd.DataFrame({'X': flow_x, 'Y': flow_y, 'Z': flow_z}).dropna()

        r_xy = float(aligned['X'].corr(aligned['Y']))
        r_xz = float(aligned['X'].corr(aligned['Z']))
        r_yz = float(aligned['Y'].corr(aligned['Z']))
        denom = np.sqrt((1 - r_xz**2) * (1 - r_yz**2))
        partial_corr = float((r_xy - (r_xz * r_yz)) / denom) if denom > 0 else 0.0

        prices_x = close_df[asset_x].dropna().tail(30)
        curr_price = float(prices_x.iloc[-1])
        time_series = pd.Series(np.arange(1, len(prices_x) + 1), index=prices_x.index)
        
        std_slope_x = float(prices_x.corr(time_series))
        r_squared_x = float(std_slope_x ** 2)
        
        slope, intercept = np.polyfit(time_series.values, prices_x.values, 1)
        trend_line = slope * time_series.values + intercept
        std_err = float(np.std(prices_x.values - trend_line))
        
        daily_returns = np.log(prices_x / prices_x.shift(1)).dropna()
        daily_vol_pct = float(daily_returns.std() * 100)
        ann_vol = float(daily_returns.std() * np.sqrt(252))

        is_forex = asset_x.endswith("=X") and "JPY" not in asset_x
        is_saudi = asset_x.endswith(".SR")
        
        def fmt_p(val):
            if is_forex:
                return f"{val:.4f}"
            elif is_saudi:
                return f"{val:.2f} SAR"
            else:
                return f"${val:.2f}"

        if is_forex:
            step = 0.0025
        elif "JPY" in asset_x:
            step = 0.25
        elif curr_price > 200:
            step = 5.0
        elif curr_price > 50:
            step = 2.5
        elif curr_price > 10:
            step = 0.5
        else:
            step = 0.05
        round_level = lambda val: round(val / step) * step

        if daily_vol_pct < 0.6:
            vol_regime = f"هادئ ({daily_vol_pct:.2f}% يومياً) - مناسب لرافعة/أهداف قريبة"
        elif daily_vol_pct < 1.8:
            vol_regime = f"متوازن ({daily_vol_pct:.2f}% يومياً) - حركة مؤسسية صحية"
        else:
            vol_regime = f"مرتفع ({daily_vol_pct:.2f}% يومياً) - وسّع وقف الخسارة"

        if std_slope_x > 0.60 and r_squared_x > 0.60:
            opt_type = "✅ اتجاه صاعد منتظم: شراء (CALL / Long)"
            safe_target = f"{fmt_p(round_level(curr_price - std_err*0.5))} (دخول / سترايك آمن)"
            main_target = f"{fmt_p(round_level(curr_price + std_err*1.2))} (الهدف الرئيسي)"
            stop_loss = f"كسر {fmt_p(curr_price - std_err*1.5)}"
        elif std_slope_x < -0.60 and r_squared_x > 0.60:
            opt_type = "🔻 اتجاه هابط منتظم: بيع / خروج (PUT / Short)"
            safe_target = f"{fmt_p(round_level(curr_price + std_err*0.5))} (دخول / سترايك آمن)"
            main_target = f"{fmt_p(round_level(curr_price - std_err*1.2))} (الهدف الرئيسي)"
            stop_loss = f"اختراق {fmt_p(curr_price + std_err*1.5)}"
        else:
            opt_type = "⚠️ تذبذب عرضي / ضعف R²: تجنب الدخول الآن"
            safe_target = f"اختراق {fmt_p(round_level(float(trend_line[-1]) + std_err))} للشراء"
            main_target = f"كسر {fmt_p(round_level(float(trend_line[-1]) - std_err))} للبيع"
            stop_loss = "انتظار التأكيد الزمني"

        hedge_status = f"🛡️ ممتاز للتحوط العكسي ({partial_corr:.2f})" if partial_corr < -0.40 else f"⚖️ ارتباط محايد/طردي ({partial_corr:.2f})"

        st.subheader(f"🎯 بطاقة التحليل الكمي الشاملة: ({asset_x})")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("السعر الحالي", fmt_p(curr_price))
        m2.metric("كفاءة الزمن (R²)", f"{r_squared_x:.1%}", f"ميل: {std_slope_x:+.2f}")
        m3.metric("الارتباط الحدي", f"{partial_corr:.2f}", market_z)
        m4.metric("التذبذب اليومي", f"{daily_vol_pct:.2f}%", f"سنوي: {ann_vol:.0%}")

        st.info(f"**القرار الآلي:** {opt_type}")

        options_df = pd.DataFrame({
            "المعيار الكمي": [
                "المؤشر المرجعي المعزول (Z)",
                "نظام التذبذب (Volatility Regime)",
                "نقطة الدخول / السترايك المحافظ",
                "الهدف السعري / السترايك المستهدف",
                "وقف الخسارة الكمي (Stop Loss)",
                f"حالة التحوط مع ({asset_y})"
            ],
            "النتيجة والمعايرة": [
                z_label_note,
                vol_regime,
                safe_target,
                main_target,
                stop_loss,
                hedge_status
            ]
        })
        st.table(options_df)

        st.subheader("📈 قناة الزمن والانحراف المعياري (Whale Zone)")
        dates_str = prices_x.index.strftime('%b %d')
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates_str, y=trend_line + 1.5*std_err, mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=dates_str, y=trend_line - 1.5*std_err, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(33, 150, 243, 0.15)', name='Whale Zone (±1.5 Std)'))
        fig.add_trace(go.Scatter(x=dates_str, y=trend_line, mode='lines', line=dict(color='#d32f2f', dash='dash', width=2), name='Time Trend'))
        fig.add_trace(go.Scatter(x=dates_str, y=prices_x.values, mode='lines+markers', line=dict(color='#1a237e', width=3), name=f'{asset_x} Price'))
        fig.update_layout(
            title=dict(text=f"{asset_x} Time Channel (R² = {r_squared_x:.1%})", x=0.5, xanchor='center'),
            xaxis=dict(type='category', tickangle=-45, nticks=10),
            template="plotly_white", height=420, margin=dict(l=10, r=10, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📡 رادار الفرص العالمي (أمريكي + سعودي + فوركس + كريبتو)")
        radar_rows = []
        for sym in radar_base:
            try:
                c_s = close_df[sym].dropna().tail(20)
                v_s = vol_df[sym].dropna().tail(20)
                cp = float(c_s.iloc[-1])
                z_sc = float((cp - c_s.mean()) / c_s.std())
                d_vol = float(np.log(c_s / c_s.shift(1)).std() * 100)
                has_vol = not (v_s.isna().all() or v_s.mean() == 0)
                rel_v = float((v_s.iloc[-1] / v_s.mean()) * 100) if has_vol else 100.0
                
                if z_sc > 2.0 and (rel_v > 120 or not has_vol):
                    sig = "🔥 تشبع شرائي (بيع / PUT)"
                elif z_sc < -2.0 and (rel_v > 120 or not has_vol):
                    sig = "💎 تشبع بيعي (شراء / CALL)"
                elif 0.8 < z_sc < 1.8 and (rel_v > 115 or not has_vol):
                    sig = "🚀 اختراق صحي (شراء)"
                else:
                    sig = "⚖️ متوازن"
                    
                p_str = f"{cp:.4f}" if (sym.endswith("=X") and "JPY" not in sym) else (f"{cp:.2f} SAR" if sym.endswith(".SR") else f"${cp:.2f}")
                vol_str = f"{rel_v:.0f}%" if has_vol else "N/A (Forex)"
                radar_rows.append({
                    "Asset": sym,
                    "Price": p_str,
                    "Z-Score": round(z_sc, 2),
                    "Daily Vol%": f"{d_vol:.2f}%",
                    "Rel Vol%": vol_str,
                    "Signal": sig
                })
            except Exception:
                pass
        st.dataframe(pd.DataFrame(radar_rows), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة البيانات: {e}")
