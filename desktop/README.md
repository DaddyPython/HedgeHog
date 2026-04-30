# Hedge Hog Desktop Terminal

Matrix-styled Tkinter interface for the Hedge Hog dual-order LBANK trading engine.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../webapp/requirements.txt
export LBANK_API_KEY="your-api-key"
export LBANK_SECRET_KEY="your-secret"
python main.py
```

The UI mirrors the web console: choose a symbol, adjust take-profit/stop-loss sliders, and
trigger simultaneous long/short orders. Logs stream live into the terminal window for
immediate diagnostics.
