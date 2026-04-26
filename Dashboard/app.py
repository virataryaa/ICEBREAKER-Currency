"""
Coffee & Cocoa Currency Dashboard
==================================
Run locally:
    streamlit run app.py
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Currency Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 70% 60% at 20% 80%, rgba(26,74,90,.50) 0%, transparent 65%),
        radial-gradient(ellipse 60% 50% at 80% 20%, rgba(42,85,104,.45) 0%, transparent 60%),
        radial-gradient(ellipse 80% 70% at 50% 30%, rgba(79,176,200,.10) 0%, transparent 55%),
        #0D1620;
    background-attachment: fixed;
}
[data-testid="stHeader"] {
    background: rgba(13,22,32,.85) !important;
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid rgba(188,212,222,.14);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"], .main    { background-color: #fafafa !important; }
  [data-testid="stHeader"]         { background: transparent !important; }
  .block-container { padding-top: 3.5rem !important; padding-bottom: 1.5rem; max-width: 1400px; }
  html, body, [class*="css"]       { font-family: -apple-system, "Helvetica Neue", sans-serif; }
  hr  { border: none !important; border-top: 1px solid #e8e8ed !important; margin: 0.5rem 0 !important; }
  .stCaption                       { color: #6e6e73 !important; font-size: 0.7rem !important; }
  [data-testid="stRadio"] label    { font-size: 0.74rem !important; }
</style>
""", unsafe_allow_html=True)

_DATA = Path(__file__).parent.parent / "Database"
COFFEE_FILE = _DATA / "currency_data.parquet"
COCOA_FILE  = _DATA / "cocoa_currency_data.parquet"

commodity = st.radio(
    "Commodity",
    ["Coffee", "Cocoa"],
    index=0,
    horizontal=True,
    label_visibility="collapsed",
)

if commodity == "Coffee":
    DATA_FILE       = COFFEE_FILE
    COUNTRIES_GRP1  = ["Brazil", "Colombia", "Honduras", "Ethiopia", "Peru"]
    COUNTRIES_GRP2  = ["Vietnam", "Brazil", "Indonesia", "Uganda", "India"]
    GRP1_LABEL      = "Arabica"
    GRP2_LABEL      = "Robusta"
    IDX1_COL        = "Arabica_Idx"
    IDX2_COL        = "Robusta_Idx"
    PRICE1_COL      = "KC_Price"
    PRICE2_COL      = "RC_Price"
    PRICE1_LABEL    = "KC Arabica (c/lb)"
    PRICE2_LABEL    = "RC Robusta ($/t)"
    WEIGHTS_GRP1    = {"Brazil": 54.0, "Colombia": 20.7, "Honduras": 7.4, "Ethiopia": 11.9, "Peru": 5.9}
    WEIGHTS_GRP2    = {"Vietnam": 47.0, "Brazil": 11.0, "Indonesia": 17.0, "Uganda": 16.0, "India": 9.0}
    COLORS_GRP1     = {"Brazil":"#4a7fb5","Colombia":"#e8c96a","Honduras":"#82c982","Ethiopia":"#e89090","Peru":"#c9a0dc"}
    COLORS_GRP2     = {"Vietnam":"#e07b39","Brazil":"#4a7fb5","Indonesia":"#7ec8c0","Uganda":"#a0aad4","India":"#f4a460"}
    COL_IDX1        = "#0a2463"
    COL_IDX2        = "#8b1a00"
    SPREAD_COL      = "Spread_Ara_Rob"
    SPREAD_LABEL    = "Arabica Index - Robusta Index"
else:
    DATA_FILE       = COCOA_FILE
    COUNTRIES_GRP1  = ["IvoryCoast_Cameroon", "Ghana", "Nigeria", "Indonesia", "Brazil", "Peru"]
    COUNTRIES_GRP2  = []
    GRP1_LABEL      = "Cocoa Origins"
    GRP2_LABEL      = ""
    IDX1_COL        = "Cocoa_Idx"
    IDX2_COL        = None
    PRICE1_COL      = "CC_Price"
    PRICE2_COL      = "LCC_Price"
    PRICE1_LABEL    = "CC NY Cocoa ($/t)"
    PRICE2_LABEL    = "LCC London Cocoa ($/t)"
    WEIGHTS_GRP1    = {"IvoryCoast_Cameroon": 53.3, "Ghana": 15.7, "Nigeria": 7.2, "Indonesia": 4.0, "Brazil": 4.7, "Peru": 3.5}
    WEIGHTS_GRP2    = {}
    COLORS_GRP1     = {"IvoryCoast_Cameroon":"#4a7fb5","Ghana":"#e8c96a","Nigeria":"#82c982","Indonesia":"#7ec8c0","Brazil":"#e07b39","Peru":"#c9a0dc"}
    COLORS_GRP2     = {}
    COL_IDX1        = "#0a2463"
    COL_IDX2        = None
    SPREAD_COL      = None
    SPREAD_LABEL    = ""

DISPLAY_NAME = {
    "IvoryCoast_Cameroon": "Ivory Coast / Cameroon",
    "Brazil": "Brazil", "Colombia": "Colombia", "Honduras": "Honduras",
    "Ethiopia": "Ethiopia", "Peru": "Peru", "Vietnam": "Vietnam",
    "Indonesia": "Indonesia", "Uganda": "Uganda", "India": "India",
    "Ghana": "Ghana", "Nigeria": "Nigeria",
}

_D = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="-apple-system, Helvetica Neue, sans-serif", color="#1d1d1f", size=10),
)


def lbl(text):
    return (
        f"<div style='background:#0a2463;padding:5px 13px;border-radius:5px;"
        f"margin:0 0 5px 0;text-align:center'>"
        f"<span style='font-size:0.78rem;font-weight:500;letter-spacing:0.07em;"
        f"text-transform:uppercase;color:#dde4f0'>{text}</span></div>"
    )


def rebase(series):
    first = series.dropna().iloc[0] if not series.dropna().empty else 1
    return series / first * 100


def _maybe_drop_bad_last_row(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 2:
        return df

    if "Arabica_Idx" in df.columns:
        watch_cols = [
            "Brazil", "Colombia", "Honduras", "Ethiopia", "Peru",
            "Vietnam", "Indonesia", "Uganda", "India",
            "Arabica_Idx", "Robusta_Idx", "Spread_Ara_Rob",
            "KC_Price", "RC_Price"
        ]
    else:
        watch_cols = [
            "IvoryCoast_Cameroon", "Ghana", "Nigeria", "Indonesia", "Brazil", "Peru",
            "Cocoa_Idx", "CC_Price", "LCC_Price"
        ]

    watch_cols = [c for c in watch_cols if c in df.columns]

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    for col in watch_cols:
        last_val = pd.to_numeric(pd.Series([last_row[col]]), errors="coerce").iloc[0]
        prev_val = pd.to_numeric(pd.Series([prev_row[col]]), errors="coerce").iloc[0]

        if pd.isna(last_val) or pd.isna(prev_val):
            continue
        if prev_val <= 0:
            continue

        if last_val < 0.8 * prev_val:
            return df.iloc[:-1].copy()

    return df


@st.cache_data(ttl=600)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = (
        df.sort_values("Date")
        .drop_duplicates(subset=["Date"], keep="last")
        .reset_index(drop=True)
    )
    df = _maybe_drop_bad_last_row(df)
    return df


try:
    df = load_data(str(DATA_FILE))
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f"### {commodity} Currency Dashboard &nbsp;"
    "<span style='font-size:0.85rem;font-weight:400;color:#6e6e73'>ICE Connect · Daily FX · USD per local</span>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

default_start = max(pd.Timestamp("2020-01-01").date(), min_date)

date_range = st.slider(
    "Date range",
    min_value=min_date,
    max_value=max_date,
    value=(default_start, max_date),
    format="YYYY-MM-DD",
)
start_date, end_date = date_range

with st.expander("Country filter", expanded=False):
    if commodity == "Coffee":
        c_a, c_b = st.columns(2)
        with c_a:
            st.markdown("**Arabica**")
            sel_grp1 = [c for c in COUNTRIES_GRP1
                        if st.checkbox(f"{DISPLAY_NAME.get(c,c)} ({WEIGHTS_GRP1.get(c,0):.1f}%)", value=True, key=f"g1_{c}")]
        with c_b:
            st.markdown("**Robusta**")
            sel_grp2 = [c for c in COUNTRIES_GRP2
                        if st.checkbox(f"{DISPLAY_NAME.get(c,c)} ({WEIGHTS_GRP2.get(c,0):.1f}%)", value=True, key=f"g2_{c}")]
    else:
        st.markdown("**Cocoa Origins**")
        cols_f = st.columns(3)
        sel_grp1 = []
        for i, c in enumerate(COUNTRIES_GRP1):
            with cols_f[i % 3]:
                if st.checkbox(f"{DISPLAY_NAME.get(c,c)} ({WEIGHTS_GRP1.get(c,0):.1f}%)", value=True, key=f"g1_{c}"):
                    sel_grp1.append(c)
        sel_grp2 = []

if not sel_grp1:
    sel_grp1 = COUNTRIES_GRP1
if commodity == "Coffee" and not sel_grp2:
    sel_grp2 = COUNTRIES_GRP2

dff = df[(df["Date"] >= pd.Timestamp(start_date)) & (df["Date"] <= pd.Timestamp(end_date))].copy()
st.markdown("<hr>", unsafe_allow_html=True)

if dff.empty:
    st.warning("No data for selected range.")
    st.stop()

if commodity == "Coffee":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(lbl("Arabica Currencies - Indexed to Start (= 100)"), unsafe_allow_html=True)
        fig_ai = go.Figure()
        for c in sel_grp1:
            if c not in dff.columns:
                continue
            fig_ai.add_trace(go.Scatter(
                x=dff["Date"], y=rebase(dff[c]),
                name=f"{DISPLAY_NAME.get(c,c)} ({WEIGHTS_GRP1.get(c,0):.0f}%)",
                mode="lines", line=dict(color=COLORS_GRP1.get(c, "#aaa"), width=1.5)
            ))
        fig_ai.add_trace(go.Scatter(
            x=dff["Date"], y=rebase(dff[IDX1_COL]),
            name="Arabica Index", mode="lines", line=dict(color=COL_IDX1, width=2.5, dash="dash")
        ))
        fig_ai.add_hline(y=100, line_color="#cccccc", line_dash="dot", line_width=1)
        fig_ai.update_layout(
            height=320,
            legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)),
            margin=dict(t=10, b=10, l=4, r=4),
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9), title="Indexed (start=100)"),
            **_D
        )
        st.plotly_chart(fig_ai, use_container_width=True)

    with col2:
        st.markdown(lbl("Robusta Currencies - Indexed to Start (= 100)"), unsafe_allow_html=True)
        fig_ri = go.Figure()
        for c in sel_grp2:
            if c not in dff.columns:
                continue
            fig_ri.add_trace(go.Scatter(
                x=dff["Date"], y=rebase(dff[c]),
                name=f"{DISPLAY_NAME.get(c,c)} ({WEIGHTS_GRP2.get(c,0):.0f}%)",
                mode="lines", line=dict(color=COLORS_GRP2.get(c, "#aaa"), width=1.5)
            ))
        fig_ri.add_trace(go.Scatter(
            x=dff["Date"], y=rebase(dff[IDX2_COL]),
            name="Robusta Index", mode="lines", line=dict(color=COL_IDX2, width=2.5, dash="dash")
        ))
        fig_ri.add_hline(y=100, line_color="#cccccc", line_dash="dot", line_width=1)
        fig_ri.update_layout(
            height=320,
            legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)),
            margin=dict(t=10, b=10, l=4, r=4),
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9), title="Indexed (start=100)"),
            **_D
        )
        st.plotly_chart(fig_ri, use_container_width=True)
else:
    st.markdown(lbl("Cocoa Origin Currencies - Indexed to Start (= 100)"), unsafe_allow_html=True)
    fig_ci = go.Figure()
    for c in sel_grp1:
        if c not in dff.columns:
            continue
        fig_ci.add_trace(go.Scatter(
            x=dff["Date"], y=rebase(dff[c]),
            name=f"{DISPLAY_NAME.get(c,c)} ({WEIGHTS_GRP1.get(c,0):.0f}%)",
            mode="lines", line=dict(color=COLORS_GRP1.get(c, "#aaa"), width=1.5)
        ))
    fig_ci.add_trace(go.Scatter(
        x=dff["Date"], y=rebase(dff[IDX1_COL]),
        name="Cocoa Index", mode="lines", line=dict(color=COL_IDX1, width=2.5, dash="dash")
    ))
    fig_ci.add_hline(y=100, line_color="#cccccc", line_dash="dot", line_width=1)
    fig_ci.update_layout(
        height=340,
        legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)),
        margin=dict(t=10, b=10, l=4, r=4),
        xaxis=dict(showgrid=False, tickfont=dict(size=9)),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9), title="Indexed (start=100)"),
        **_D
    )
    st.plotly_chart(fig_ci, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

if commodity == "Coffee":
    col3, col4 = st.columns(2)
    panels = [
        (col3, IDX1_COL, "Arabica", PRICE1_COL, PRICE1_LABEL, COL_IDX1),
        (col4, IDX2_COL, "Robusta", PRICE2_COL, PRICE2_LABEL, COL_IDX2)
    ]
else:
    col3, col4 = st.columns(2)
    panels = [
        (col3, IDX1_COL, "Cocoa (NY)", PRICE1_COL, PRICE1_LABEL, COL_IDX1),
        (col4, IDX1_COL, "Cocoa (London)", PRICE2_COL, PRICE2_LABEL, "#8b1a00")
    ]

for col, idx_col, idx_name, price_col, price_label, idx_color in panels:
    with col:
        st.markdown(lbl(f"{idx_name} Currency Index vs {price_label}"), unsafe_allow_html=True)
        fig_p = make_subplots(specs=[[{"secondary_y": True}]])
        if idx_col and idx_col in dff.columns:
            fig_p.add_trace(go.Scatter(
                x=dff["Date"], y=dff[idx_col], name=f"{idx_name} Idx",
                line=dict(color=idx_color, width=2), mode="lines"
            ), secondary_y=False)
        if price_col in dff.columns:
            valid_p = dff[price_col].dropna()
            if not valid_p.empty:
                fig_p.add_trace(go.Scatter(
                    x=dff["Date"], y=dff[price_col], name=price_label,
                    line=dict(color="#888888", width=1.4, dash="dot"), mode="lines"
                ), secondary_y=True)
        fig_p.update_layout(
            height=280,
            legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)),
            margin=dict(t=10, b=10, l=4, r=4),
            **_D
        )
        fig_p.update_yaxes(
            title_text=f"{idx_name} Index", secondary_y=False,
            showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9)
        )
        fig_p.update_yaxes(
            title_text=price_label, secondary_y=True, showgrid=False, tickfont=dict(size=9)
        )
        fig_p.update_xaxes(showgrid=False, tickfont=dict(size=9))
        st.plotly_chart(fig_p, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

if commodity == "Coffee":
    col5, col6 = st.columns(2)
    with col5:
        st.markdown(lbl("Arabica Index vs Robusta Index"), unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=dff["Date"], y=dff[IDX1_COL], name="Arabica",
            line=dict(color=COL_IDX1, width=2), mode="lines"
        ))
        fig3.add_trace(go.Scatter(
            x=dff["Date"], y=dff[IDX2_COL], name="Robusta",
            line=dict(color=COL_IDX2, width=2), mode="lines"
        ))
        fig3.update_layout(
            height=260,
            legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)),
            margin=dict(t=10, b=10, l=4, r=4),
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9)),
            **_D
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col6:
        st.markdown(lbl("Spread: Arabica Index - Robusta Index"), unsafe_allow_html=True)
        fig4 = go.Figure(go.Scatter(
            x=dff["Date"], y=dff[SPREAD_COL], mode="lines",
            line=dict(color="#9b59b6", width=1.8),
            fill="tozeroy", fillcolor="rgba(155,89,182,0.07)"
        ))
        fig4.add_hline(y=0, line_color="#cccccc", line_width=1)
        fig4.update_layout(
            height=260,
            margin=dict(t=10, b=10, l=4, r=4),
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9)),
            **_D
        )
        st.plotly_chart(fig4, use_container_width=True)
else:
    st.markdown(lbl("NY Cocoa (CCc2) vs London Cocoa (LCCc2) - Settlement Prices"), unsafe_allow_html=True)
    fig_spread = make_subplots(specs=[[{"secondary_y": True}]])
    if "CC_Price" in dff.columns:
        fig_spread.add_trace(go.Scatter(
            x=dff["Date"], y=dff["CC_Price"], name="NY CC ($/t)",
            line=dict(color=COL_IDX1, width=2), mode="lines"
        ), secondary_y=False)
    if "LCC_Price" in dff.columns:
        fig_spread.add_trace(go.Scatter(
            x=dff["Date"], y=dff["LCC_Price"], name="London LCC ($/t)",
            line=dict(color="#8b1a00", width=2), mode="lines"
        ), secondary_y=True)
    fig_spread.update_layout(
        height=260,
        legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)),
        margin=dict(t=10, b=10, l=4, r=4),
        **_D
    )
    fig_spread.update_yaxes(
        title_text="NY CC ($/t)", secondary_y=False, showgrid=True,
        gridcolor="#f0f0f0", tickfont=dict(size=9)
    )
    fig_spread.update_yaxes(
        title_text="London LCC ($/t)", secondary_y=True, showgrid=False, tickfont=dict(size=9)
    )
    fig_spread.update_xaxes(showgrid=False, tickfont=dict(size=9))
    st.plotly_chart(fig_spread, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

def _render_fx_chart(data, country, weights, colors, line_color):
    if country not in data.columns:
        st.caption(f"{DISPLAY_NAME.get(country, country)} - no data")
        return
    s = data[country].dropna()
    if s.empty:
        st.caption(f"{DISPLAY_NAME.get(country, country)} - no data")
        return

    rebased = rebase(data[country])
    fig = go.Figure(go.Scatter(
        x=data["Date"], y=rebased,
        mode="lines",
        line=dict(color=colors.get(country, line_color), width=1.8),
        name=DISPLAY_NAME.get(country, country),
    ))
    fig.add_hline(y=100, line_color="#cccccc", line_dash="dot", line_width=1)
    fig.update_layout(
        height=200,
        title=dict(
            text=f"{DISPLAY_NAME.get(country, country)}<br>"
                 f"<sup style='font-size:9px'>{weights.get(country,0):.1f}% weight</sup>",
            font=dict(size=10), x=0.5, xanchor="center",
        ),
        margin=dict(t=36, b=10, l=4, r=4),
        showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=8)),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=8), title=""),
        **_D,
    )
    st.plotly_chart(fig, use_container_width=True)


all_sel = sel_grp1 + [c for c in sel_grp2 if c not in sel_grp1]
if all_sel:
    if commodity == "Coffee":
        st.markdown(lbl("Arabica Producer Currencies - Individual FX Rates"), unsafe_allow_html=True)
        cols_fx = st.columns(len(sel_grp1))
        for i, c in enumerate(sel_grp1):
            with cols_fx[i]:
                _render_fx_chart(dff, c, WEIGHTS_GRP1, COLORS_GRP1, "#0a2463")

        st.markdown(lbl("Robusta Producer Currencies - Individual FX Rates"), unsafe_allow_html=True)
        cols_fx2 = st.columns(len(sel_grp2))
        for i, c in enumerate(sel_grp2):
            with cols_fx2[i]:
                _render_fx_chart(dff, c, WEIGHTS_GRP2, COLORS_GRP2, "#7a3010")
    else:
        st.markdown(lbl("Cocoa Origin Currencies - Individual FX Rates"), unsafe_allow_html=True)
        cols_fx = st.columns(min(len(sel_grp1), 6))
        for i, c in enumerate(sel_grp1):
            with cols_fx[i % len(cols_fx)]:
                _render_fx_chart(dff, c, WEIGHTS_GRP1, COLORS_GRP1, "#0a2463")

st.markdown("<hr>", unsafe_allow_html=True)

col7, col8 = st.columns(2)

if commodity == "Coffee":
    scatter_pairs = [
        (IDX1_COL, PRICE1_COL, "Arabica Index", PRICE1_LABEL, COL_IDX1),
        (IDX2_COL, PRICE2_COL, "Robusta Index", PRICE2_LABEL, COL_IDX2)
    ]
else:
    scatter_pairs = [
        (IDX1_COL, PRICE1_COL, "Cocoa Index", PRICE1_LABEL, COL_IDX1),
        (IDX1_COL, PRICE2_COL, "Cocoa Index", PRICE2_LABEL, "#8b1a00")
    ]

for col, (idx_col, price_col, idx_name, price_name, color) in zip([col7, col8], scatter_pairs):
    with col:
        if not idx_col or idx_col not in dff.columns or price_col not in dff.columns:
            continue
        valid = dff.dropna(subset=[idx_col, price_col])
        if valid.empty:
            st.info(f"No data for {idx_name} vs {price_name}")
            continue
        r = valid[idx_col].corr(valid[price_col])
        st.markdown(lbl(f"{idx_name} vs {price_name} - r = {r:.3f}"), unsafe_allow_html=True)
        fig_sc = go.Figure(go.Scatter(
            x=valid[idx_col], y=valid[price_col], mode="markers",
            marker=dict(color=color, size=4, opacity=0.4),
            text=valid["Date"].dt.strftime("%Y-%m-%d")
        ))
        z = np.polyfit(valid[idx_col], valid[price_col], 1)
        x_l = np.linspace(valid[idx_col].min(), valid[idx_col].max(), 100)
        fig_sc.add_trace(go.Scatter(
            x=x_l, y=np.polyval(z, x_l), mode="lines",
            line=dict(color="#cccccc", width=1.5, dash="dash"), showlegend=False
        ))
        fig_sc.update_layout(
            height=260,
            margin=dict(t=10, b=10, l=4, r=4),
            xaxis=dict(title=idx_name, showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9)),
            yaxis=dict(title=price_name, showgrid=True, gridcolor="#f0f0f0", tickfont=dict(size=9)),
            showlegend=False,
            **_D
        )
        st.plotly_chart(fig_sc, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

st.markdown(lbl("Latest Values and % Changes"), unsafe_allow_html=True)

anchor_col = sel_grp1[0] if sel_grp1 else None
if anchor_col and anchor_col in dff.columns:
    anchor = dff.dropna(subset=[anchor_col])
    if not anchor.empty:
        last_row = anchor.iloc[-1]
        prev_row = anchor.iloc[-2] if len(anchor) >= 2 else last_row
        y1_cut   = dff[dff["Date"] <= (last_row["Date"] - pd.Timedelta(weeks=52))].dropna(subset=[anchor_col])
        y1_row   = y1_cut.iloc[-1] if not y1_cut.empty else last_row

        rows = []
        all_countries = sel_grp1 + [c for c in sel_grp2 if c not in sel_grp1]
        grp_map = {c: GRP1_LABEL for c in COUNTRIES_GRP1}
        grp_map.update({c: GRP2_LABEL for c in COUNTRIES_GRP2})

        for c in all_countries:
            if c not in dff.columns:
                continue
            d1 = (last_row[c] - prev_row[c]) / prev_row[c] * 100 if prev_row[c] else 0
            y1 = (last_row[c] - y1_row[c]) / y1_row[c] * 100 if y1_row[c] else 0
            rows.append({
                "Country": DISPLAY_NAME.get(c, c),
                "Group": grp_map.get(c, GRP1_LABEL),
                "Weight %": f"{WEIGHTS_GRP1.get(c, WEIGHTS_GRP2.get(c, 0)):.1f}%",
                "Latest FX": f"{last_row[c]:.4f}",
                "1D %": f"{d1:+.2f}%",
                "1Y %": f"{y1:+.1f}%"
            })

        idx_pairs = [(IDX1_COL, f"{GRP1_LABEL} Index")]
        if IDX2_COL:
            idx_pairs.append((IDX2_COL, f"{GRP2_LABEL} Index"))

        for col_name, label in idx_pairs:
            if col_name not in dff.columns:
                continue
            d1 = (last_row[col_name] - prev_row[col_name]) / prev_row[col_name] * 100 if prev_row[col_name] else 0
            y1 = (last_row[col_name] - y1_row[col_name]) / y1_row[col_name] * 100 if y1_row[col_name] else 0
            rows.append({
                "Country": label,
                "Group": "Index",
                "Weight %": "--",
                "Latest FX": f"{last_row[col_name]:.2f}",
                "1D %": f"{d1:+.2f}%",
                "1Y %": f"{y1:+.1f}%"
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            height=min(35 * (len(rows) + 2), 600)
        )

st.markdown("<hr>", unsafe_allow_html=True)
st.caption(
    f"Currency Dashboard · ETG Softs · Source: ICE Connect · "
    f"Last updated: {df['Date'].max().strftime('%Y-%m-%d')}"
)