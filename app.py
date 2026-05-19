from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
from alpaca.trading.client import TradingClient


st.set_page_config(
    page_title="Alpaca Paper Portfolio",
    page_icon="📈",
    layout="wide",
)


def get_secret(name: str, default: str | None = None) -> str | None:
    """
    Reads Streamlit secrets first, then environment variables.
    Works locally and on Streamlit Cloud.
    """
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    value = os.getenv(name)
    if value:
        return str(value)

    return default


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def pct(value: Any) -> str:
    try:
        return f"{float(value):,.2f}%"
    except Exception:
        return "0.00%"


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


@st.cache_resource(ttl=30)
def get_client() -> TradingClient:
    api_key = get_secret("ALPACA_API_KEY")
    secret_key = get_secret("ALPACA_SECRET_KEY")
    paper_raw = get_secret("ALPACA_PAPER", "true")

    if not api_key or not secret_key:
        raise RuntimeError(
            "Missing Alpaca keys. Add ALPACA_API_KEY and ALPACA_SECRET_KEY "
            "as Streamlit secrets or environment variables."
        )

    paper = str(paper_raw).strip().lower() in {"1", "true", "yes", "y", "on"}
    return TradingClient(api_key, secret_key, paper=paper)


@st.cache_data(ttl=20)
def load_account_data() -> dict[str, Any]:
    client = get_client()
    account = client.get_account()
    positions = client.get_all_positions()

    account_data = {
        "portfolio_value": safe_float(account.portfolio_value),
        "cash": safe_float(account.cash),
        "buying_power": safe_float(account.buying_power),
        "equity": safe_float(account.equity),
        "last_equity": safe_float(account.last_equity),
        "status": str(account.status),
        "trading_blocked": bool(account.trading_blocked),
        "transfers_blocked": bool(account.transfers_blocked),
        "account_blocked": bool(account.account_blocked),
    }

    rows = []
    for p in positions:
        qty = safe_float(p.qty)
        current_price = safe_float(p.current_price)
        market_value = safe_float(p.market_value)
        avg_entry = safe_float(p.avg_entry_price)
        unrealized_pl = safe_float(p.unrealized_pl)
        unrealized_plpc = safe_float(p.unrealized_plpc) * 100
        side = "Long" if qty > 0 else "Short"

        rows.append(
            {
                "Ticker": p.symbol,
                "Side": side,
                "Qty": qty,
                "Current Price": current_price,
                "Avg Entry": avg_entry,
                "Market Value": market_value,
                "Unrealized P/L $": unrealized_pl,
                "Unrealized P/L %": unrealized_plpc,
            }
        )

    positions_df = pd.DataFrame(rows)
    return {"account": account_data, "positions": positions_df}


def render_header() -> None:
    left, right = st.columns([0.78, 0.22])
    with left:
        st.title("Alpaca Paper Portfolio")
        st.caption("Read-only dashboard for paper holdings, current values, and unrealized P/L.")
    with right:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


def render_metrics(account: dict[str, Any]) -> None:
    portfolio_value = account["portfolio_value"]
    last_equity = account["last_equity"]
    daily_change = portfolio_value - last_equity
    daily_change_pct = (daily_change / last_equity * 100) if last_equity else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Value", money(portfolio_value), f"{daily_change_pct:.2f}% today")
    c2.metric("Daily Change", money(daily_change))
    c3.metric("Cash", money(account["cash"]))
    c4.metric("Buying Power", money(account["buying_power"]))

    st.progress(
        min(max((daily_change_pct + 5) / 10, 0), 1),
        text=f"Daily movement bar: {daily_change_pct:.2f}%",
    )


def render_positions(df: pd.DataFrame) -> None:
    st.subheader("Open Positions")

    if df.empty:
        st.info("No open positions.")
        return

    total_long = df.loc[df["Side"] == "Long", "Market Value"].sum()
    total_short = abs(df.loc[df["Side"] == "Short", "Market Value"].sum())
    total_pl = df["Unrealized P/L $"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Long Exposure", money(total_long))
    c2.metric("Short Exposure", money(total_short))
    c3.metric("Open Position P/L", money(total_pl))

    display_df = df.copy()
    display_df = display_df.sort_values("Market Value", key=lambda s: s.abs(), ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Price": st.column_config.NumberColumn("Current Price", format="$%.2f"),
            "Avg Entry": st.column_config.NumberColumn("Avg Entry", format="$%.2f"),
            "Market Value": st.column_config.NumberColumn("Market Value", format="$%.2f"),
            "Unrealized P/L $": st.column_config.NumberColumn("Unrealized P/L $", format="$%.2f"),
            "Unrealized P/L %": st.column_config.NumberColumn("Unrealized P/L %", format="%.2f%%"),
        },
    )

    chart_df = display_df[["Ticker", "Unrealized P/L $"]].copy()
    st.subheader("P/L by Position")
    st.bar_chart(chart_df.set_index("Ticker"))

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download positions CSV",
        csv,
        file_name="alpaca_positions.csv",
        mime="text/csv",
    )


def render_status(account: dict[str, Any]) -> None:
    st.subheader("Account Status")

    status_rows = {
        "Account status": account["status"],
        "Trading blocked": account["trading_blocked"],
        "Transfers blocked": account["transfers_blocked"],
        "Account blocked": account["account_blocked"],
        "Last updated UTC": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }

    st.table(pd.DataFrame(status_rows.items(), columns=["Field", "Value"]))


def main() -> None:
    render_header()

    st.warning(
        "Do not expose your Alpaca API keys. Keep this app read-only and store keys only in Streamlit secrets or environment variables.",
        icon="⚠️",
    )

    try:
        data = load_account_data()
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    account = data["account"]
    positions_df = data["positions"]

    render_metrics(account)
    render_positions(positions_df)
    render_status(account)


if __name__ == "__main__":
    main()
