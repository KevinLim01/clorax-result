# Alpaca Paper Portfolio Dashboard

A simple read-only Streamlit dashboard for your Alpaca paper trading account.

It shows:

- portfolio value
- daily change
- cash
- buying power
- open positions
- current price
- market value
- unrealized P/L
- long and short exposure
- P/L bar chart
- CSV export

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Local environment variables

Create a `.env` file if you use a local environment loader, or export these in your terminal:

```bash
export ALPACA_API_KEY="your_key_here"
export ALPACA_SECRET_KEY="your_secret_here"
export ALPACA_PAPER="true"
```

Then run:

```bash
streamlit run app.py
```

## Streamlit Cloud secrets

On Streamlit Cloud, go to:

```text
App settings → Secrets
```

Paste:

```toml
ALPACA_API_KEY = "your_key_here"
ALPACA_SECRET_KEY = "your_secret_here"
ALPACA_PAPER = "true"
```

## Safety

Never place Alpaca keys directly inside `app.py`.

This app does not submit trades. It only reads account and position data.
