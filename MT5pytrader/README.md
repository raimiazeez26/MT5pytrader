# MT5pytrader
##### A trading assistant for seamless trade execution on MT5 platform

![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)

MT5pytrader is an MT5-based module for seamless trade execution. It is d

## Features

-     Functions:
        connect() - Connects to a specified account 
        open_buy() - Open a buy position 
        open_sell() - Open a sell position 
        close_buy() - close a buy position using the symbol or ticket_id
        close_sell() - Close a sell position using the symbol or ticket_id
        open_buy_limit() - Open a buy limit
        open_sell_limit() - Open a sell limit
        close_partial_buy() - Close a percentage of an open buy position(partial close)
        close_partial_sell() - Close a percentage of an open sell position(partial close)
        modify_sl() - Modify Stop loss of a position using the symbol or ticket_id
        modify_tp() - Modify Take profit of a position using the symbol or ticket_id
        get_open_positions() - Returns a list of all open position as a pandas Dataframe
        running_profit() - Returns the cummulative sum of all runnig trades (profit/loss)
        break_even() - Break even on a trade position running in profit


## Installation

Install the dependencies and devDependencies and start the server.

```sh
pip install MT5pytrader
```

```
#### Dependence
Please install the latest version of MetaTrader5 and numpy
```sh
pip install --upgrade numpy
pip install MetraTrader5
```

## Usage
```sh
>>> from MT5pytrader import Trader

#instantiate 
>>> trader = Trader()

Connect to a specified account
>>> trader.connect(account, password, server) 

open a buy position
>>> trader.open_buy(symbol:str, lot:int = 0.1, stop_loss:int = None, take_profit:int = None, magic:int = 260000, comment:str = "MT5pytrader")

#open buy position on GBPUSD with 1.0lot size and 200points stop loss with no take profit
>>> trader.open_buy(symbol = "GBPUSD", lot = 1.0, sl = 200) 
    
open a sell position
>>> trader.open_sell(symbol:str, lot:int = 0.1, stop_loss:int = None, take_profit:int = None, magic:int = 260000, comment:str = "MT5pytrader")

#open sell position on CADJPY with 0.5 lot size and 150points take profit with no stop loss 
>>> trader.open_sell(symbol = "CADJPY", lot = 0.5, tp = 150) 

```

## Development
MT5pytrader is in active development.

Want to contribute? Great! Please contact me via email with your ideas. 

## License

MIT

**Free Software, Enjoy and Feedback!**

