# HedgeHog

Perpetual Crypto Futures LBANK Hedge Platform

## Overview

Hedge Hog is a multi-platform, Matrix-themed LBANK trading console that instantly executes
hedged long/short positions with configurable take-profit and stop-loss targets. It streams
all HTTP/WebSocket activity to a live log feed so you can debug production trades in real
time.

The repository currently includes:

- **Flask web app** located in `webapp/` – run locally to drive trades from the browser.
- **SwiftUI iOS blueprint** in `ios/` – provides the same UI/logic using native components.
- **Tkinter desktop terminal** in `desktop/` – offers a desktop experience with identical
  behaviour.

Each client shares the same core LBANK integration rules: execute simultaneous long/short
market orders with LBANK-side TP/SL and expose a bright Matrix aesthetic.

## ⚠️ Production Safety

The platform is wired for **live trading only**. It expects valid LBANK API credentials and
never uses a sandbox. Always review position sizes and risk settings before pressing
`EXECUTE TRADE`.

Export credentials before starting any client:

```bash
export LBANK_API_KEY="your-api-key"
export LBANK_SECRET_KEY="your-secret"
```

## Web Application

```bash
cd webapp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000> to access the terminal. The UI auto-refreshes the symbol list,
streams logs via Server-Sent Events, and provides a neon Matrix skin with digital rain.

## Desktop Application (Tkinter)

The desktop client reuses the Python trading engine and provides native windows controls.
See `desktop/README.md` for build instructions.

## iOS Application

The SwiftUI client uses Keychain for secure credential storage and replicates the web
console. See `ios/README.md` for Xcode setup guidance.

## License

Released under the MIT License.
