from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}
PALETTE = ["#8b5cf6", "#22d3ee", "#f59e0b", "#34d399", "#fb7185", "#60a5fa"]


st.set_page_config(
    page_title="Store Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#f6f7fb; --muted:#8e97aa; --panel:#151922; --panel-2:#1b202b; --line:#292f3d; --violet:#8b5cf6; --cyan:#22d3ee; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 78% 0%, #24203d 0, #0d1017 35%, #0d1017 100%); color:var(--ink); }
    [data-testid="stSidebar"] { background:#11141b; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] * { color:#dce1ec; }
    h1,h2,h3,h4 { font-family:'Space Grotesk', sans-serif; letter-spacing:-.03em; }
    h1 { font-size:2.25rem; margin-bottom:.15rem; }
    h2 { margin-top:0; }
    .eyebrow { color:#a78bfa; text-transform:uppercase; letter-spacing:.18em; font-size:.72rem; font-weight:700; }
    .subcopy { color:var(--muted); font-size:.95rem; margin-bottom:1.25rem; }
    .metric-card { background:linear-gradient(135deg, rgba(29,34,46,.98), rgba(19,22,30,.98)); border:1px solid var(--line); border-radius:16px; padding:18px 20px; min-height:122px; }
    .metric-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.1em; font-weight:700; }
    .metric-value { color:var(--ink); font-family:'Space Grotesk',sans-serif; font-size:1.7rem; font-weight:700; margin-top:12px; }
    .metric-delta { color:#34d399; font-size:.78rem; margin-top:6px; }
    .section-title { font-family:'Space Grotesk'; font-weight:700; font-size:1.15rem; margin:1.5rem 0 .7rem; }
    .insight { background:linear-gradient(135deg, rgba(139,92,246,.17), rgba(34,211,238,.08)); border:1px solid rgba(139,92,246,.28); border-radius:16px; padding:16px 18px; height:100%; }
    .insight b { color:#e9d5ff; }
    .stPlotlyChart { border:1px solid var(--line); border-radius:16px; overflow:hidden; background:rgba(21,25,34,.7); }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; }
    .small-note { color:var(--muted); font-size:.8rem; }
    button[kind="secondary"] { border-color:#343b4c; }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    value = float(value or 0)
    if abs(value) >= 1_000_000_000:
        return f"PKR {value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"PKR {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"PKR {value / 1_000:.1f}K"
    return f"PKR {value:,.0f}"


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    return clean_data(frame)


@st.cache_data(show_spinner=False)
def load_uploaded(file_bytes: bytes) -> pd.DataFrame:
    from io import BytesIO

    return clean_data(pd.read_csv(BytesIO(file_bytes), low_memory=False))


def clean_data(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    frame = frame.drop(columns=[c for c in frame.columns if c.lower().startswith("unnamed:")], errors="ignore")
    frame = frame.dropna(how="all")

    numeric_columns = ["item_id", "price", "qty_ordered", "grand_total", "discount_amount", "Year", "Month", "Customer ID"]
    for column in numeric_columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ["status", "category_name_1", "payment_method", "BI Status", "sku", "increment_id", "FY"]:
        if column in frame:
            frame[column] = frame[column].astype("string").str.strip().replace({"": pd.NA, "\\N": pd.NA})
    if "created_at" in frame:
        frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce")
    elif "Working Date" in frame:
        frame["created_at"] = pd.to_datetime(frame["Working Date"], errors="coerce")
    else:
        frame["created_at"] = pd.NaT

    frame["category"] = frame.get("category_name_1", pd.Series("Unknown", index=frame.index)).fillna("Unknown")
    frame["status_clean"] = frame.get("status", pd.Series("Unknown", index=frame.index)).fillna("Unknown").str.replace("_", " ").str.title()
    frame["payment"] = frame.get("payment_method", pd.Series("Unknown", index=frame.index)).fillna("Unknown").str.upper()
    if "grand_total" not in frame:
        frame["grand_total"] = frame.get("price", 0) * frame.get("qty_ordered", 0)
    frame["revenue"] = pd.to_numeric(frame["grand_total"], errors="coerce").fillna(0)
    frame["units"] = pd.to_numeric(frame.get("qty_ordered", 0), errors="coerce").fillna(0)
    frame["month_num"] = frame["created_at"].dt.month
    frame["month_name"] = frame["month_num"].map(MONTH_NAMES)
    frame["year_month"] = frame["created_at"].dt.to_period("M").astype("string")
    frame["customer"] = frame.get("Customer ID", pd.Series(pd.NA, index=frame.index))
    frame["order_id"] = frame.get("increment_id", pd.Series(pd.NA, index=frame.index)).fillna(frame.get("item_id", pd.Series(pd.NA, index=frame.index)).astype("string"))
    return frame.reset_index(drop=True)


def chart_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=48, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dce1ec", family="DM Sans"),
        title_font=dict(family="Space Grotesk", size=16),
        legend=dict(orientation="h", y=1.12, x=0),
        xaxis=dict(gridcolor="#292f3d", zerolinecolor="#292f3d"),
        yaxis=dict(gridcolor="#292f3d", zerolinecolor="#292f3d"),
    )
    return fig


def metric(label: str, value: str, note: str = "") -> None:
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-delta">{note}</div></div>', unsafe_allow_html=True)


def render_empty_state() -> None:
    st.markdown("## Upload the ecommerce CSV to activate the dashboard")
    st.info("The notebook references `Pakistan Largest Ecommerce Dataset.csv`, but that CSV is not included in this workspace. Use the uploader in the sidebar, or place the CSV beside this app and rerun it.")
    st.markdown("### Notebook benchmark snapshot")
    cols = st.columns(4)
    for col, label, value in zip(cols, ["Rows in notebook", "Populated records", "Notebook revenue", "Peak month"], ["1.05M", "584.5K", "PKR 8.94B", "November"]):
        with col:
            metric(label, value, "from saved notebook outputs")
    st.markdown("""
    <div class="insight"><b>Why the CSV is required:</b> the notebook only stores outputs, not the original row-level file. The dashboard is built to recompute every view from the uploaded data, including date, category, status, payment, customer, and order-level filters.</div>
    """, unsafe_allow_html=True)


def main() -> None:
    st.sidebar.markdown('<div class="eyebrow">Pakistan ecommerce</div><h2 style="margin:4px 0 18px">Store Intelligence</h2>', unsafe_allow_html=True)
    st.sidebar.caption("Interactive decision dashboard built from the E-commerce Store Insights notebook.")
    uploaded = st.sidebar.file_uploader("Upload dataset CSV", type=["csv"])

    local_csv = first_existing([
        APP_DIR / "Pakistan Largest Ecommerce Dataset.csv",
        APP_DIR.parent / "Pakistan Largest Ecommerce Dataset.csv",
        APP_DIR / "data" / "Pakistan Largest Ecommerce Dataset.csv",
    ])
    if uploaded is not None:
        df = load_uploaded(uploaded.getvalue())
        source_label = "uploaded CSV"
    elif local_csv:
        df = load_csv(str(local_csv))
        source_label = local_csv.name
    else:
        render_empty_state()
        return

    st.sidebar.divider()
    st.sidebar.markdown("**Filters**")
    valid_dates = df["created_at"].dropna()
    if not valid_dates.empty:
        date_min, date_max = valid_dates.min().date(), valid_dates.max().date()
        date_range = st.sidebar.date_input("Order date", (date_min, date_max), min_value=date_min, max_value=date_max)
    else:
        date_range = None
    categories = sorted(df["category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect("Category", categories, placeholder="All categories")
    statuses = sorted(df["status_clean"].dropna().unique().tolist())
    selected_statuses = st.sidebar.multiselect("Order status", statuses, placeholder="All statuses")
    payments = sorted(df["payment"].dropna().unique().tolist())
    selected_payments = st.sidebar.multiselect("Payment method", payments, placeholder="All methods")
    top_n = st.sidebar.slider("Top categories shown", 5, 16, 8)

    filtered = df.copy()
    if date_range and len(date_range) == 2:
        filtered = filtered[filtered["created_at"].dt.date.between(date_range[0], date_range[1])]
    if selected_categories:
        filtered = filtered[filtered["category"].isin(selected_categories)]
    if selected_statuses:
        filtered = filtered[filtered["status_clean"].isin(selected_statuses)]
    if selected_payments:
        filtered = filtered[filtered["payment"].isin(selected_payments)]

    orders = filtered.groupby("order_id", dropna=True)["revenue"].max() if not filtered.empty else pd.Series(dtype=float)
    total_revenue = filtered["revenue"].sum()
    total_orders = orders.size
    aov = orders.mean() if total_orders else 0
    cancelled = filtered["status_clean"].str.contains("Canceled", case=False, na=False).mean() * 100 if len(filtered) else 0
    customer_count = filtered["customer"].nunique(dropna=True)

    st.markdown('<div class="eyebrow">Executive overview</div>', unsafe_allow_html=True)
    st.title("Your store, in focus.")
    st.markdown(f'<div class="subcopy">A clean view of sales performance, demand, and fulfillment signals · {len(filtered):,} line items · source: {source_label}</div>', unsafe_allow_html=True)

    kpis = st.columns(5)
    with kpis[0]: metric("Gross revenue", money(total_revenue), "selected scope")
    with kpis[1]: metric("Orders", f"{total_orders:,}", "unique order IDs")
    with kpis[2]: metric("Average order value", money(aov), "order-level average")
    with kpis[3]: metric("Cancellation rate", f"{cancelled:.1f}%", "of filtered line items")
    with kpis[4]: metric("Customers", f"{customer_count:,}", "unique customer IDs")

    if filtered.empty:
        st.warning("No rows match the current filter combination. Widen the filters in the sidebar.")
        return

    monthly = filtered.dropna(subset=["year_month"]).groupby("year_month", as_index=False).agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"))
    if not monthly.empty:
        fig = px.area(monthly, x="year_month", y="revenue", markers=True, title="Revenue momentum", color_discrete_sequence=["#8b5cf6"])
        fig.update_traces(line=dict(width=3), fillcolor="rgba(139,92,246,.18)", hovertemplate="%{x}<br>PKR %{y:,.0f}<extra></extra>")
        st.plotly_chart(chart_layout(fig, 370), use_container_width=True)

    left, right = st.columns([1.4, 1])
    with left:
        category = filtered.groupby("category", as_index=False).agg(revenue=("revenue", "sum"), units=("units", "sum"), orders=("order_id", "nunique")).sort_values("revenue", ascending=False).head(top_n)
        fig = px.bar(category.sort_values("revenue"), x="revenue", y="category", orientation="h", color="revenue", color_continuous_scale=["#312e81", "#8b5cf6", "#22d3ee"], title="Top categories by revenue", hover_data=["orders", "units"])
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(chart_layout(fig, 390), use_container_width=True)
    with right:
        status = filtered["status_clean"].value_counts().reset_index(name="orders").rename(columns={"index": "status"})
        fig = px.pie(status, names="status_clean", values="orders", hole=.62, title="Order status mix", color_discrete_sequence=PALETTE)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(chart_layout(fig, 390), use_container_width=True)

    top_category = category.iloc[0]["category"] if not category.empty else "—"
    peak_month = monthly.loc[monthly["revenue"].idxmax(), "year_month"] if not monthly.empty else "—"
    peak_status = status.iloc[0]["status_clean"] if not status.empty else "—"
    insight_cols = st.columns(3)
    insight_items = [
        ("Category signal", f"{top_category} leads the selected scope by revenue. Prioritize stock depth, bundles, and cross-sells here."),
        ("Timing signal", f"{peak_month} is the strongest revenue period in the selection. Build inventory and campaigns ahead of this window."),
        ("Fulfillment signal", f"{peak_status} is the largest status bucket. Review cancellation, refund, and pending flows before optimizing acquisition."),
    ]
    for col, (title, body) in zip(insight_cols, insight_items):
        with col:
            st.markdown(f'<div class="insight"><div class="eyebrow">{title}</div><p>{body}</p></div>', unsafe_allow_html=True)

    tab_category, tab_orders, tab_explorer = st.tabs(["Category & demand", "Orders & fulfillment", "Data explorer"])
    with tab_category:
        c1, c2 = st.columns(2)
        with c1:
            payment = filtered["payment"].value_counts().head(8).reset_index(name="orders").rename(columns={"index": "payment"})
            fig = px.bar(payment.sort_values("orders"), x="orders", y="payment", orientation="h", title="Payment method adoption", color="orders", color_continuous_scale=["#164e63", "#22d3ee"])
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(chart_layout(fig, 360), use_container_width=True)
        with c2:
            month = filtered.dropna(subset=["month_name"]).groupby(["month_num", "month_name"], as_index=False).agg(revenue=("revenue", "sum"), units=("units", "sum")).sort_values("month_num")
            fig = px.bar(month, x="month_name", y="revenue", title="Seasonality by calendar month", color="revenue", color_continuous_scale=["#312e81", "#8b5cf6", "#f59e0b"])
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(chart_layout(fig, 360), use_container_width=True)
        sample = filtered.sample(min(5000, len(filtered)), random_state=42).copy()
        # Refunds and adjustments can make revenue negative. Plotly marker sizes
        # must be non-negative, so use the absolute value as visual magnitude
        # while keeping the original revenue available in the hover data.
        sample["bubble_size"] = (
            pd.to_numeric(sample["revenue"], errors="coerce")
            .replace([float("inf"), float("-inf")], 0)
            .fillna(0)
            .abs()
        )
        if not sample.empty and sample["bubble_size"].max() == 0:
            sample["bubble_size"] = 1.0
        fig = px.scatter(sample, x="price", y="units", color="category", size="bubble_size", size_max=28, hover_data=["status_clean", "payment", "revenue"], opacity=.55, title="Price vs. quantity ordered")
        st.plotly_chart(chart_layout(fig, 420), use_container_width=True)

    with tab_orders:
        c1, c2 = st.columns(2)
        with c1:
            status_revenue = filtered.groupby("status_clean", as_index=False).agg(revenue=("revenue", "sum"), avg_order_value=("revenue", "mean"), orders=("order_id", "nunique")).sort_values("revenue", ascending=False)
            fig = px.bar(status_revenue, x="status_clean", y="revenue", title="Revenue by order status", color="revenue", color_continuous_scale=["#312e81", "#8b5cf6", "#22d3ee"], hover_data=["orders", "avg_order_value"])
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(chart_layout(fig, 360), use_container_width=True)
        with c2:
            daily = filtered.dropna(subset=["created_at"]).groupby(filtered.dropna(subset=["created_at"])["created_at"].dt.day_name()).size().reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).reset_index(name="line_items")
            fig = px.bar(daily, x="created_at", y="line_items", title="Demand by day of week", color="line_items", color_continuous_scale=["#164e63", "#22d3ee"])
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(chart_layout(fig, 360), use_container_width=True)
        st.dataframe(status_revenue.style.format({"revenue": "PKR {:,.0f}", "avg_order_value": "PKR {:,.0f}", "orders": "{:,.0f}"}), use_container_width=True, hide_index=True)

    with tab_explorer:
        st.download_button("Download filtered CSV", filtered.drop(columns=["year_month"], errors="ignore").to_csv(index=False).encode("utf-8"), "filtered_ecommerce_orders.csv", "text/csv")
        visible_columns = [c for c in ["created_at", "order_id", "category", "status_clean", "payment", "price", "units", "revenue", "customer"] if c in filtered.columns]
        st.dataframe(filtered[visible_columns].sort_values("revenue", ascending=False).head(1000), use_container_width=True, hide_index=True)
        with st.expander("Data quality notes"):
            missing = df.isna().mean().sort_values(ascending=False).head(10).mul(100).round(1).reset_index()
            missing.columns = ["field", "missing_pct"]
            st.caption("The app drops completely blank rows and removes empty Unnamed columns. Missing categorical values remain visible as Unknown so filters do not silently hide them.")
            st.dataframe(missing, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
