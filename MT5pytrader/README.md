# MT5pytrader
##### A trading assistant for seamless trade execution on the MT5 platform

![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)

MT5pytrader is a lightweight Python helper that wraps common MetaTrader 5 (MT5) trading
operations—connecting to an account, placing market/limit orders, closing positions,
modifying stops/take-profits, and reporting running P/L.

## Features

- Connect to an MT5 account.
- Open/close market orders (buy/sell).
- Open/close pending limit orders.
- Partial close support for open positions.
- Modify stop-loss and take-profit values.
- Summaries of open positions and cumulative running profit.

## Installation

```sh
pip install MT5pytrader
```

## Requirements

- MetaTrader 5 terminal installed and running with Algo Trading enabled.
- Python packages:
  - MetaTrader5
  - pandas

```sh
pip install --upgrade MetaTrader5 pandas
```

## Usage

```sh
>>> from MT5pytrader import Trader

# instantiate
>>> trader = Trader()

# Connect to a specified account
>>> trader.connect(account, password, server)

# Open a buy position
>>> trader.open_buy(symbol="GBPUSD", lot=1.0, stop_loss=200)

# Open a sell position
>>> trader.open_sell(symbol="CADJPY", lot=0.5, take_profit=150)
```

## Development

MT5pytrader is in active development.

Want to contribute? Great! Please contact me via email with your ideas.

## License

MIT

**Free Software, Enjoy and Feedback!**
