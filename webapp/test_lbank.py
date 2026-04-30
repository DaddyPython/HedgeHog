import os
import ccxt

exchange = ccxt.lbank({
    'apiKey': os.getenv("LBANK_API_KEY"),
    'secret': os.getenv("LBANK_API_SECRET"),
})

print("Testing connection...")
print(exchange.fetch_balance())
