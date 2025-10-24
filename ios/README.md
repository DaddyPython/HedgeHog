# Hedge Hog iOS Terminal

SwiftUI client for the Hedge Hog LBANK trading console with Matrix-inspired visuals.

## Features

- Dynamic symbol picker that mirrors the Flask API
- Sliders for take-profit / stop-loss configuration
- Real-time activity log with neon styling
- Keychain-ready credential storage (see `SecretsManager.swift`)

## Setup

1. Open the `ios/` directory in Xcode (create a new SwiftUI project and replace the default
   files with the provided sources).
2. Add the custom font "ShareTechMono-Regular" to the project (available via Google Fonts).
3. Configure transport security to allow calls to `http://localhost:5000` during development.
4. Populate your LBANK API keys in the secure storage helper.
5. Run the Flask backend from `webapp/` before launching the iOS app.

The app issues real LBANK orders. Confirm balances and API permissions before pressing the
**EXECUTE TRADE** button.
