import os
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text


st.set_page_config(
    page_title="ConsumerAlpha | Retail Nowcasting",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

      html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
      }

      /* Base */
      .stApp { background: #07111f; }
      .block-container { padding-top: 4rem; padding-bottom: 2rem; max-width: 1480px; }

      /* Sidebar */
      [data-testid="stSidebar"] {
        background: #07111f;
        border-right: 1px solid #132033;
      }
      [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.6rem;
      }

      /* Sidebar wordmark */
      .ca-wordmark {
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
        font-size: 1.05rem;
        letter-spacing: 0.04em;
        color: #22d3ee;
        padding: 0 1rem 0.1rem 1rem;
      }
      .ca-tagline {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        color: #4a7fa5;
        letter-spacing: 0.1em;
        padding: 0 1rem 1.4rem 1rem;
      }

      /* Nav buttons in sidebar */
      .ca-nav-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        color: #64748b;
        letter-spacing: 0.12em;
        padding: 0 1rem;
        margin-bottom: 0.4rem;
        margin-top: 0.6rem;
      }

      div[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        border-left: 2px solid transparent;
        border-radius: 0;
        color: #4a7fa5;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.84rem;
        font-weight: 400;
        padding: 0.5rem 1rem;
        margin: 0;
        transition: all 0.15s ease;
      }
      div[data-testid="stSidebar"] .stButton > button:hover {
        background: #0d1f33;
        color: #e2e8f0;
        border-left-color: #22d3ee;
      }
      div[data-testid="stSidebar"] .stButton > button:focus {
        outline: none;
        box-shadow: none;
        background: #0d1f33;
        color: #22d3ee;
        border-left-color: #22d3ee;
      }

      /* Active nav item */
      .nav-active button {
        background: #0d1f33 !important;
        color: #22d3ee !important;
        border-left-color: #22d3ee !important;
        font-weight: 500 !important;
      }

      /* Divider */
      .ca-divider {
        height: 1px;
        background: #132033;
        margin: 1rem 0;
      }

      /* Refresh area */
      div[data-testid="stSidebar"] .stButton.refresh > button {
        background: #0d1f33;
        border: 1px solid #1e3a52;
        border-radius: 4px;
        color: #4a7fa5;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        padding: 0.45rem 1rem;
        margin: 0 1rem;
        width: calc(100% - 2rem);
      }
      div[data-testid="stSidebar"] .stButton.refresh > button:hover {
        background: #132a40;
        color: #22d3ee;
        border-color: #22d3ee;
      }

      /* Main content page header */
      .ca-page-eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #94a3b8;
        letter-spacing: 0.14em;
        margin-bottom: 0.3rem;
      }
      .ca-page-title {
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
        font-size: 2rem;
        color: #e2e8f0;
        letter-spacing: -0.03em;
        margin: 0 0 0.3rem 0;
        line-height: 1.1;
      }
      .ca-page-sub {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.92rem;
        color: #64748b;
        margin-bottom: 0.2rem;
      }

      /* Metric cards */
      .ca-metric {
        background: #0d1823;
        border: 1px solid #132033;
        border-top: 2px solid #22d3ee;
        border-radius: 4px;
        padding: 1rem 1.1rem 0.9rem;
      }
      .ca-metric-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        color: #64748b;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
      }
      .ca-metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.75rem;
        font-weight: 500;
        color: #e2e8f0;
        letter-spacing: -0.02em;
        line-height: 1;
      }
      .ca-metric-note {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 0.4rem;
      }

      /* Section headings */
      .ca-section {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #94a3b8;
        letter-spacing: 0.12em;
        margin: 1.8rem 0 0.7rem 0;
        padding: 0.35rem 0 0.35rem 0.75rem;
        border-left: 2px solid #22d3ee;
        border-bottom: none;
      }

      /* Dataframe overrides */
      .stDataFrame { border: 1px solid #132033; border-radius: 4px; }

      /* Plot container */
      div[data-testid="stPlotlyChart"] {
        background: #0d1823;
        border: 1px solid #132033;
        border-radius: 4px;
      }

      /* Streamlit metrics */
      div[data-testid="stMetric"] {
        background: #0d1823;
        border: 1px solid #132033;
        border-top: 2px solid #22d3ee;
        border-radius: 4px;
        padding: 1rem;
      }
      div[data-testid="stMetricLabel"] > div {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: #64748b;
        letter-spacing: 0.08em;
      }
      div[data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace;
        color: #e2e8f0;
      }

      /* Streamlit caption */
      .stCaption, [data-testid="stCaptionContainer"] p {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #64748b;
      }

      /* Selectbox */
      div[data-testid="stSelectbox"] label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #64748b;
        letter-spacing: 0.08em;
      }
      div[data-testid="stSelectbox"] > div > div {
        background: #0d1823;
        border-color: #1e3a52;
        color: #94a3b8;
      }

      /* Warning / info */
      div[data-testid="stAlert"] {
        background: #0d1f2e;
        border-color: #1e3a52;
        color: #4a7fa5;
      }

      #MainMenu, footer { visibility: hidden; }

      header[data-testid="stHeader"] {
        background: #07111f;
        border-bottom: 1px solid #132033;
      }
      /* Style the collapse/expand sidebar button */
      button[kind="header"] {
        color: #4a7fa5 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Constants ----------
TABLES = {
    "predictions": ("public_mart", "fct_model_predictions"),
    "signals": ("public_mart", "fct_retail_signals_monthly"),
    "backtest": ("public_mart", "rpt_backtest_summary"),
    "granger": ("public_mart", "rpt_granger_diagnostics"),
    "coefficients": ("public_mart", "rpt_feature_coefficients"),
}

CATEGORY_NAMES = {
    "RSAFS": "Total Retail & Food Services",
    "RSGMS": "General Merchandise",
    "RSFHFS": "Furniture & Home Furnishings",
    "RSEAS": "Electronics & Appliances",
    "RSDBS": "Building Materials & Garden",
}

SIGNAL_LABELS = {
    "job_openings_yoy": "Retail Job Openings (YoY)",
    "lagged_umich_sentiment": "Consumer Sentiment (Lagged)",
    "reddit_budget_yoy": "Reddit: Budget Talk (YoY)",
    "reddit_deals_yoy": "Reddit: Deal Seeking (YoY)",
    "reddit_neg_share_m": "Reddit: Negative Sentiment Share",
    "reddit_posts_yoy": "Reddit: Retail Post Volume (YoY)",
    "reddit_sentiment_m": "Reddit: Sentiment Score",
    "reddit_shopping_yoy": "Reddit: Shopping Mentions (YoY)",
    "trend_deals_yoy": "Search: Deals Trend (YoY)",
    "trend_electronics_yoy": "Search: Electronics Trend (YoY)",
    "trend_financial_pressure_yoy": "Search: Financial Pressure (YoY)",
    "trend_furniture_yoy": "Search: Furniture Trend (YoY)",
    "trend_home_improvement_yoy": "Search: Home Improvement Trend (YoY)",
    "xly_yoy": "Consumer Discretionary ETF (YoY)",
    "xrt_vol_m": "Retail ETF: Monthly Volume",
    "xrt_yoy": "Retail ETF (YoY)",
    "target_yoy_lag_1m": "Retail Sales, 1-Month Lag (YoY)",
    "delinquency_rate": "Credit Card Delinquency Rate",
    "delinquency_rate_yoy": "Credit Card Delinquency (YoY)",
}

PLOT_BG = "#0d1823"
PAPER_BG = "#0d1823"
GRID = "#132033"
CYAN = "#22d3ee"
STEEL = "#4a7fa5"
WHITE = "#e2e8f0"
GREEN = "#34d399"
RED = "#f87171"
AMBER = "#f59e0b"


def get_database_url():
    try:
        value = st.secrets.get("DATABASE_URL", "")
        if value:
            return value
    except Exception:
        pass
    return os.getenv("DATABASE_URL", "")


@st.cache_resource
def get_engine(database_url):
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing.")
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=300)


@st.cache_data(ttl=300, show_spinner=False)
def read_table(schema, table, database_url):
    engine = get_engine(database_url)
    query = text(f'SELECT * FROM "{schema}"."{table}"')
    with engine.connect() as connection:
        return pd.read_sql_query(query, connection)


def load_data(database_url):
    loaded = {}
    errors = {}
    for key, (schema, table) in TABLES.items():
        try:
            loaded[key] = read_table(schema, table, database_url)
        except Exception as exc:
            loaded[key] = pd.DataFrame()
            errors[key] = str(exc)
    return loaded, errors


def find_col(df, candidates):
    if df is None or df.empty:
        return None
    lookup = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def add_category_name(df):
    if df.empty:
        return df
    code_col = find_col(df, ["category_code"])
    if code_col:
        df = df.copy()
        df["category_label"] = df[code_col].map(CATEGORY_NAMES).fillna(df[code_col].astype(str))
    return df


def label_signal(name):
    return SIGNAL_LABELS.get(str(name).lower(), str(name).replace("_", " ").title())


def prepare_predictions(predictions, signals):
    if predictions.empty:
        return predictions
    df = predictions.copy()
    date_col = find_col(df, ["month_date", "month", "forecast_month"])
    category_col = find_col(df, ["category_code"])
    actual_col = find_col(df, ["actual_yoy_pct", "retail_sales_yoy_pct", "actual_pct"])
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if actual_col is None and not signals.empty:
        signal_date = find_col(signals, ["month_date"])
        signal_category = find_col(signals, ["category_code"])
        signal_actual = find_col(signals, ["retail_sales_yoy_pct", "actual_yoy_pct"])
        if date_col and category_col and signal_date and signal_category and signal_actual:
            actuals = signals[[signal_date, signal_category, signal_actual]].copy()
            actuals[signal_date] = pd.to_datetime(actuals[signal_date], errors="coerce")
            actuals = actuals.rename(
                columns={
                    signal_date: date_col,
                    signal_category: category_col,
                    signal_actual: "actual_yoy_pct",
                }
            )
            df = df.merge(actuals, on=[date_col, category_col], how="left")
    return df


def fmt_pct(value):
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "—"


def chart_title(text):
    style = (
        "font-family:'IBM Plex Sans',sans-serif;"
        "font-size:0.9rem;"
        "font-weight:500;"
        "color:#cbd5e1;"
        "margin:0 0 0.4rem 2px;"
    )
    st.markdown(f'<div style="{style}">{text}</div>', unsafe_allow_html=True)


def style_figure(fig, height=390):
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        height=height,
        margin=dict(l=20, r=20, t=48, b=24),
        title="",
        font=dict(family="IBM Plex Sans", color="#94a3b8", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=12, color="#94a3b8"),
            itemsizing="constant",
            tracegroupgap=0,
        ),
        hoverlabel=dict(
            bgcolor="#0d1f33",
            bordercolor=GRID,
            font_color=WHITE,
            font_family="IBM Plex Sans",
        ),
    )
    fig.update_xaxes(
        gridcolor=GRID,
        zerolinecolor=GRID,
        linecolor=GRID,
        tickfont=dict(family="IBM Plex Mono", size=10, color="#4a7fa5"),
        title_font=dict(family="IBM Plex Sans", size=11, color="#4a7fa5"),
    )
    fig.update_yaxes(
        gridcolor=GRID,
        zerolinecolor=GRID,
        linecolor=GRID,
        tickfont=dict(family="IBM Plex Mono", size=10, color="#4a7fa5"),
        title_font=dict(family="IBM Plex Sans", size=11, color="#4a7fa5"),
    )
    return fig


def page_header(eyebrow, title, subtitle):
    st.markdown(f'<div class="ca-page-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ca-page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ca-page-sub">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1.2rem"></div>', unsafe_allow_html=True)


def metric_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="ca-metric">
          <div class="ca-metric-label">{label}</div>
          <div class="ca-metric-value">{value}</div>
          <div class="ca-metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(text):
    st.markdown(f'<div class="ca-section">{text}</div>', unsafe_allow_html=True)


def get_live_rows(df):
    if df.empty:
        return df
    live_col = find_col(df, ["is_live_forecast", "is_live"])
    date_col = find_col(df, ["month_date", "month", "forecast_month"])
    if live_col:
        mask = df[live_col].astype(str).str.lower().isin(["true", "1", "t", "yes"])
        live = df.loc[mask].copy()
        if not live.empty:
            return live
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        if dates.notna().any():
            return df.loc[dates == dates.max()].copy()
    return df.tail(5).copy()


# ---------- Pages ----------

def render_overview(predictions, backtest, granger):
    page_header(
        "EXECUTIVE NOWCAST",
        "Retail sales, before the release.",
        "Alternative-data signals and model nowcasts for US monthly retail sales.",
    )
    if predictions.empty:
        st.warning("No prediction records found. Check the database connection.")
        return

    df = predictions.copy()
    pred_col = find_col(df, ["predicted_yoy_pct", "prediction", "predicted_pct"])
    base_col = find_col(df, ["baseline_ar1_pct", "ar1_prediction", "baseline_pct"])
    code_col = find_col(df, ["category_code"])
    date_col = find_col(df, ["month_date", "month", "forecast_month"])
    if not pred_col or not code_col:
        st.error("Predictions table is missing expected columns.")
        st.dataframe(df.head(20), width="stretch")
        return

    live = get_live_rows(df)
    live = add_category_name(live)
    latest_date = pd.to_datetime(live[date_col], errors="coerce").max() if date_col else None
    latest_label = latest_date.strftime("%B %Y") if pd.notna(latest_date) else "Latest"

    total_row = live.loc[live[code_col].astype(str) == "RSAFS"]
    total_prediction = total_row[pred_col].iloc[0] if not total_row.empty else None
    total_baseline = total_row[base_col].iloc[0] if base_col and not total_row.empty else None

    bt_mae = find_col(backtest, ["mae_ridge"])
    bt_base_mae = find_col(backtest, ["mae_ar1"])
    bt_dir = find_col(backtest, ["directional_accuracy_pct"])
    total_bt = (
        backtest.loc[backtest["category_code"].astype(str) == "RSAFS"]
        if not backtest.empty and "category_code" in backtest.columns
        else pd.DataFrame()
    )
    mae_value = "—"
    mae_note = ""
    if not total_bt.empty and bt_mae and bt_base_mae:
        mae_value = f"{float(total_bt[bt_mae].iloc[0]):.2f} pp"
        mae_note = f"AR(1) baseline: {float(total_bt[bt_base_mae].iloc[0]):.2f} pp"

    significant_count = "—"
    p_col = find_col(granger, ["p_value", "pvalue", "granger_p_value"])
    if p_col:
        pvals = pd.to_numeric(granger[p_col], errors="coerce")
        significant_count = str(int((pvals < 0.05).sum()))

    st.caption(
        f"Forecast period: {latest_label}  ·  Refreshed {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}"
    )
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("TOTAL RETAIL NOWCAST", fmt_pct(total_prediction), latest_label)
    with c2:
        metric_card("AR(1) BASELINE", fmt_pct(total_baseline), "Prior-month growth benchmark")
    with c3:
        metric_card("RIDGE BACKTEST MAE", mae_value, mae_note)
    with c4:
        metric_card("GRANGER SIGNALS", significant_count, "p < 0.05, unadjusted")

    section("CATEGORY NOWCASTS")
    display_cols = [code_col, pred_col]
    if base_col:
        display_cols.append(base_col)
    if date_col:
        display_cols.append(date_col)
    table = live[display_cols].copy()
    rename_map = {code_col: "Category", pred_col: "Ridge nowcast (%)"}
    if base_col:
        rename_map[base_col] = "AR(1) baseline (%)"
    if date_col:
        rename_map[date_col] = "Forecast month"
    table = table.rename(columns=rename_map)
    if "Category" in table.columns:
        table["Category"] = table["Category"].map(CATEGORY_NAMES).fillna(table["Category"])
    st.dataframe(table, width="stretch", hide_index=True)

    section("HISTORICAL PERFORMANCE")
    actual_col = find_col(df, ["actual_yoy_pct", "retail_sales_yoy_pct", "actual_pct"])
    if actual_col and date_col:
        historical = df.copy()
        historical[date_col] = pd.to_datetime(historical[date_col], errors="coerce")
        historical[actual_col] = pd.to_numeric(historical[actual_col], errors="coerce")
        historical[pred_col] = pd.to_numeric(historical[pred_col], errors="coerce")
        selected = st.selectbox(
            "Category",
            options=sorted(historical[code_col].dropna().astype(str).unique()),
            format_func=lambda x: CATEGORY_NAMES.get(x, x),
            key="overview_category",
        )
        hist = historical.loc[historical[code_col].astype(str) == selected].sort_values(date_col)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=hist[date_col], y=hist[actual_col],
                name="Actual", mode="lines+markers",
                line=dict(color=WHITE, width=2),
                marker=dict(size=4),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=hist[date_col], y=hist[pred_col],
                name="Ridge", mode="lines",
                line=dict(color=CYAN, width=1.8, dash="dash"),
            )
        )
        if base_col:
            hist[base_col] = pd.to_numeric(hist[base_col], errors="coerce")
            fig.add_trace(
                go.Scatter(
                    x=hist[date_col], y=hist[base_col],
                    name="AR(1)", mode="lines",
                    line=dict(color=AMBER, width=1.8, dash="dot"),
                )
            )
        fig.add_hline(y=0, line_color="#1e3a52", line_dash="solid", line_width=1)
        fig.update_layout(yaxis_title="YoY growth (%)")
        chart_title(CATEGORY_NAMES.get(selected, selected))
        st.plotly_chart(style_figure(fig, 440), width="stretch")
    else:
        st.info("Historical actuals not available in predictions table.")


def render_signal_attribution(granger, coefficients):
    page_header(
        "SIGNAL ATTRIBUTION",
        "What moves ahead of retail?",
        "Leading indicators, Granger-causality test results, and fitted Ridge coefficients.",
    )

    if not granger.empty:
        p_col = find_col(granger, ["p_value", "pvalue", "granger_p_value"])
        feature_col = find_col(granger, ["feature", "feature_name", "signal_name", "feature_col"])
        category_col = find_col(granger, ["category_code"])

        if p_col and feature_col:
            g = granger.copy()
            g[p_col] = pd.to_numeric(g[p_col], errors="coerce")
            g["signal_label"] = g[feature_col].apply(label_signal)

            if category_col:
                categories = ["All"] + sorted(g[category_col].dropna().astype(str).unique().tolist())
                chosen = st.selectbox("Category", categories, key="granger_category")
                if chosen != "All":
                    g = g.loc[g[category_col].astype(str) == chosen]

            pivot = g.pivot_table(
                index="signal_label",
                columns=category_col if category_col else None,
                values=p_col,
                aggfunc="min",
            )
            if isinstance(pivot, pd.Series):
                pivot = pivot.to_frame()

            pivot.columns = [CATEGORY_NAMES.get(str(c), str(c)) for c in pivot.columns]

            fig = px.imshow(
                pivot,
                aspect="auto",
                color_continuous_scale=[[0, "#22d3ee"], [0.05, "#f59e0b"], [0.3, "#1e3a52"], [1, "#07111f"]],
                zmin=0,
                zmax=1,
                labels=dict(color="p-value"),
            )
            fig.update_layout(
                xaxis=dict(tickangle=-30, tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=10)),
                coloraxis_colorbar=dict(
                    title="p-value",
                    title_font=dict(size=10, color="#4a7fa5"),
                    tickfont=dict(size=9, color="#4a7fa5", family="IBM Plex Mono"),
                    thickness=12,
                    len=0.8,
                ),
            )
            chart_title("Granger p-values  ·  lower = stronger leading relationship")
            st.plotly_chart(style_figure(fig, max(360, 36 * len(pivot) + 150)), width="stretch")
            st.caption("Granger p-values are unadjusted for multiple comparisons and lag selection. Predictability does not establish causation.")
        else:
            st.info("Feature or p-value column names differ from expected schema.")
            st.dataframe(granger, width="stretch", hide_index=True)
    else:
        st.warning("No Granger diagnostic rows found.")

    section("RIDGE COEFFICIENT PROFILE")
    if not coefficients.empty:
        coef_col = find_col(coefficients, ["standardized_coef", "standardized_coefficient", "coefficient", "coef"])
        feat_col = find_col(coefficients, ["feature", "feature_name", "signal_name", "feature_col"])
        cat_col = find_col(coefficients, ["category_code"])
        if coef_col and feat_col:
            c = coefficients.copy()
            c[coef_col] = pd.to_numeric(c[coef_col], errors="coerce")
            c["signal_label"] = c[feat_col].apply(label_signal)
            if cat_col:
                choices = ["All"] + sorted(c[cat_col].dropna().astype(str).unique().tolist())
                chosen_cat = st.selectbox(
                    "Category",
                    [CATEGORY_NAMES.get(x, x) if x != "All" else "All" for x in choices],
                    key="coef_category",
                )
                # Map back to code
                inv_map = {v: k for k, v in CATEGORY_NAMES.items()}
                chosen_code = inv_map.get(chosen_cat, chosen_cat)
                if chosen_cat != "All":
                    c = c.loc[c[cat_col].astype(str) == chosen_code]
            c = c.dropna(subset=[coef_col]).sort_values(coef_col)
            c["direction"] = c[coef_col].apply(lambda x: "Positive" if x >= 0 else "Negative")
            fig = px.bar(
                c,
                x=coef_col,
                y="signal_label",
                orientation="h",
                color="direction",
                color_discrete_map={"Positive": CYAN, "Negative": RED},
            )
            fig.add_vline(x=0, line_color="#1e3a52", line_width=1.5)
            fig.update_layout(xaxis_title="Standardised coefficient", yaxis_title="")
            chart_title("Standardised Ridge coefficients")
            st.plotly_chart(style_figure(fig, max(380, 30 * len(c) + 140)), width="stretch")
            st.caption("Coefficients describe the fitted Ridge model and are not causal estimates.")
        else:
            st.dataframe(coefficients, width="stretch", hide_index=True)
    else:
        st.info("No feature coefficient rows found.")


def render_backtest(backtest, predictions):
    page_header(
        "BACKTEST DIAGNOSTICS",
        "Performance, without the spin.",
        "Walk-forward evaluation against a simple autoregressive baseline.",
    )
    if backtest.empty:
        st.warning("No backtest summary rows found.")
        return

    b = backtest.copy()
    mae_col = find_col(b, ["mae_ridge"])
    ar_col = find_col(b, ["mae_ar1"])
    direction_col = find_col(b, ["directional_accuracy_pct"])
    category_col = find_col(b, ["category_code"])
    name_col = find_col(b, ["category_name"])

    if mae_col and ar_col:
        b[mae_col] = pd.to_numeric(b[mae_col], errors="coerce")
        b[ar_col] = pd.to_numeric(b[ar_col], errors="coerce")
        fig = go.Figure()
        labels = (
            b[name_col]
            if name_col
            else b[category_col].map(CATEGORY_NAMES).fillna(b[category_col])
            if category_col
            else b.index.astype(str)
        )
        fig.add_trace(
            go.Bar(name="Ridge MAE", x=labels, y=b[mae_col], marker_color=CYAN, marker_line_width=0)
        )
        fig.add_trace(
            go.Bar(name="AR(1) baseline MAE", x=labels, y=b[ar_col], marker_color=AMBER, marker_line_width=0)
        )
        fig.update_layout(barmode="group", yaxis_title="MAE (pp)")
        chart_title("Mean absolute error by category (percentage points)")
        st.plotly_chart(style_figure(fig, 400), width="stretch")

    c1, c2, c3 = st.columns(3)
    with c1:
        if mae_col:
            c1.metric("Mean Ridge MAE", f"{b[mae_col].mean():.3f} pp")
    with c2:
        if ar_col:
            c2.metric("Mean AR(1) MAE", f"{b[ar_col].mean():.3f} pp")
    with c3:
        if direction_col:
            c3.metric(
                "Mean directional accuracy",
                f"{pd.to_numeric(b[direction_col], errors='coerce').mean():.1f}%",
            )

    section("CATEGORY-LEVEL RESULTS")

    display_b = b.copy()
    if category_col and name_col is None:
        display_b["Category"] = display_b[category_col].map(CATEGORY_NAMES).fillna(display_b[category_col])
    st.dataframe(display_b, width="stretch", hide_index=True)

    if not predictions.empty:
        actual_col = find_col(predictions, ["actual_yoy_pct", "retail_sales_yoy_pct", "actual_pct"])
        pred_col = find_col(predictions, ["predicted_yoy_pct", "prediction", "predicted_pct"])
        code_col = find_col(predictions, ["category_code"])
        if actual_col and pred_col:
            p = predictions.copy()
            p[actual_col] = pd.to_numeric(p[actual_col], errors="coerce")
            p[pred_col] = pd.to_numeric(p[pred_col], errors="coerce")
            p = p.dropna(subset=[actual_col, pred_col])
            if code_col:
                p["Category"] = p[code_col].map(CATEGORY_NAMES).fillna(p[code_col])
            if not p.empty:
                section("ACTUAL VS PREDICTED")
                color_col = "Category" if "Category" in p.columns else find_col(p, ["category_code"])
                fig = px.scatter(
                    p,
                    x=actual_col,
                    y=pred_col,
                    color=color_col,
                    color_discrete_sequence=[CYAN, AMBER, GREEN, RED, STEEL],
                    hover_data=[c for c in ["month_date", "category_code"] if c in p.columns],
                )
                low = min(p[actual_col].min(), p[pred_col].min()) - 0.5
                high = max(p[actual_col].max(), p[pred_col].max()) + 0.5
                fig.add_shape(
                    type="line", x0=low, y0=low, x1=high, y1=high,
                    line=dict(color="#1e3a52", dash="dash", width=1.5),
                )
                fig.update_layout(
                    xaxis_title="Actual YoY growth (%)",
                    yaxis_title="Predicted YoY growth (%)",
                )
                chart_title("Actual vs Ridge-predicted YoY growth (%)")
                st.plotly_chart(style_figure(fig, 420), width="stretch")

    st.warning(
        "Ridge currently has a higher MAE than the AR(1) baseline across all five categories. "
        "The simple autoregressive baseline is performing better in this backtest window."
    )


# ---------- Main ----------

def main():
    database_url = get_database_url()

    # Sidebar
    with st.sidebar:
        st.markdown('<div class="ca-wordmark">CONSUMERALPHA</div>', unsafe_allow_html=True)
        st.markdown('<div class="ca-tagline">ALTERNATIVE DATA / RETAIL NOWCASTING</div>', unsafe_allow_html=True)
        st.markdown('<div class="ca-divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="ca-nav-label">PAGES</div>', unsafe_allow_html=True)

        if "page" not in st.session_state:
            st.session_state.page = "Executive Nowcast"

        pages = ["Executive Nowcast", "Signal Attribution", "Backtest Diagnostics"]

        active_page = st.session_state.page

        nav_css_parts = []
        for p in pages:
            safe = p.replace(" ", "").replace("&", "")
            if p == active_page:
                nav_css_parts.append(
                    f'div[data-testid="stSidebar"] div[data-testid="stButton"]:has(button[kind="secondary"][data-testid$="nav_{safe}"]) button,'
                    f'div[data-testid="stSidebar"] div[data-testid="stButton"]:has(button[key="nav_{safe}"]) button'
                    f'{{ background:#0d1f33!important;color:#22d3ee!important;border-left:2px solid #22d3ee!important;font-weight:500!important; }}'
                )

        positions = {p: i + 1 for i, p in enumerate(pages)}
        active_nth = positions.get(active_page, 1)
        nav_css = (
            f'div[data-testid="stSidebar"] .stButton:nth-of-type({active_nth}) > button '
            f'{{ background:#0d1f33!important;color:#22d3ee!important;'
            f'border-left:2px solid #22d3ee!important;font-weight:500!important; }}'
        )
        st.markdown(f"<style>{nav_css}</style>", unsafe_allow_html=True)

        for p in pages:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p
                st.rerun()

        st.markdown('<div class="ca-divider"></div>', unsafe_allow_html=True)

        if st.button("↻  Refresh", key="refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)
        st.caption("Auto-refresh: 5 min")
        st.caption("Source: Neon PostgreSQL")

    if not database_url:
        st.error(
            "DATABASE_URL is not configured. Add it to `.streamlit/secrets.toml` or your environment variables."
        )
        st.stop()

    @st.fragment(run_every="5m")
    def dashboard_content():
        with st.spinner("Loading..."):
            data, errors = load_data(database_url)

        if errors:
            with st.expander("Connection notices", expanded=False):
                for key, message in errors.items():
                    st.warning(f"{key}: {message}")

        predictions = prepare_predictions(data["predictions"], data["signals"])
        page = st.session_state.get("page", "Executive Nowcast")

        if page == "Executive Nowcast":
            render_overview(predictions, data["backtest"], data["granger"])
        elif page == "Signal Attribution":
            render_signal_attribution(data["granger"], data["coefficients"])
        elif page == "Backtest Diagnostics":
            render_backtest(data["backtest"], predictions)

        st.markdown('<div class="ca-divider"></div>', unsafe_allow_html=True)
        st.caption(
            f"ConsumerAlpha  ·  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ·  Nowcasts are estimates, not official Census releases."
        )

    dashboard_content()


if __name__ == "__main__":
    main()