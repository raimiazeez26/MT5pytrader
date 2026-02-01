import pandas as pd
import MetaTrader5 as mt5


class Trader:  # parent
    """
    MT5pytrader,
    Send Trade request to MT5 server based on defined parameters.

    Functions:
        MT5pytrader.open_buy() - Open a buy position
        MT5pytrader.open_sell() - Open a sell position
        MT5pytrader.close_buy() - close a buy position using the symbol or ticket_id
        MT5pytrader.close_sell() - Close a sell position using the symbol or ticket_id
        MT5pytrader.open_buy_limit() - Open a buy limit
        MT5pytrader.open_sell_limit() - Open a sell limit
        MT5pytrader.close_partial_buy() - Close a percentage of an open buy position(partial close)
        MT5pytrader.close_partial_sell() - Close a percentage of an open sell position(partial close)
        MT5pytrader.modify_sl() - Modify Stop loss of a position using the symbol or ticket_id
        MT5pytrader.modify_tp() - Modify Take profit of a position using the symbol or ticket_id
        MT5pytrader.get_open_positions() - Returns a list of all open position as a pandas Dataframe
        MT5pytrader.running_profit() - Returns the cummulative sum of all runnig trades (profit/loss)
        MT5pytrader.break_even() - Break even on a running position in profit

    """

    def __init__(
        self,
        comment="MT5pytrader",
        magic=260000,
        deviation=20,
        type_time=mt5.ORDER_TIME_GTC,
        type_filling=mt5.SYMBOL_TRADE_EXECUTION_INSTANT,
    ):
        # establish connection to the MetaTrader 5 terminal
        if not mt5.initialize():
            print("initialize() failed, error code =", mt5.last_error())
        else:
            print("successfully initialized. Please allow Auto trading")

        self.comment = comment
        self.magic = magic
        self.deviation = deviation
        self.type_time = type_time
        self.type_filling = type_filling

    def __repr__(self):
        return "MT5pytrader Instance"

    def _ensure_symbol(self, symbol):
        if not symbol:
            print("Symbol is required.")
            return False

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(symbol, "not found")
            return False

        if not symbol_info.visible:
            print(symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(symbol, True):
                print(f"symbol_select({symbol}) failed, exit")
                return False

        return True

    def _send_request(self, request, description):
        result = mt5.order_send(request)
        print(description)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = None if result is None else result.retcode
            print(f" - order_send failed, retcode={retcode}")

            if result is None:
                return None

            result_dict = result._asdict()
            for field, value in result_dict.items():
                print(f"   {field}={value}")
                if field == "request":
                    traderequest_dict = value._asdict()
                    for tradereq_field, tradereq_value in traderequest_dict.items():
                        print(
                            f"       traderequest: {tradereq_field}={tradereq_value}"
                        )
        else:
            print(f"Order Sent! {result.order}")

        return result

    def _calculate_sl_tp(self, price, point, stop_loss, take_profit, is_buy):
        sl_price = None
        tp_price = None

        if stop_loss is not None:
            sl_price = price - (stop_loss * point) if is_buy else price + (stop_loss * point)

        if take_profit is not None:
            tp_price = price + (take_profit * point) if is_buy else price - (
                take_profit * point
            )

        return sl_price, tp_price

    def _build_open_request(
        self,
        action,
        symbol,
        volume,
        order_type,
        price,
        sl=None,
        tp=None,
    ):
        request = {
            "action": action,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": self.comment,
            "type_time": self.type_time,
            "type_filling": self.type_filling,
        }

        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp

        return request

    def _build_close_request(self, symbol, volume, order_type, position, price):
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": position,
            "price": price,
            "deviation": self.deviation,
            "type_time": self.type_time,
            "type_filling": self.type_filling,
        }

    def _get_positions_by_ticket(self, ticket_id):
        positions = mt5.positions_get(ticket=ticket_id)
        if positions is None or len(positions) == 0:
            print(f"No positions on {ticket_id}, error code={mt5.last_error()}")
            return []
        return positions

    def _get_positions_by_symbol(self, symbol):
        positions = mt5.positions_get(symbol=symbol)
        if positions is None or len(positions) == 0:
            print(f"No positions on {symbol}, error code={mt5.last_error()}")
            return []
        return positions

    def _validate_partial_percent(self, percent):
        if percent is None or percent <= 0 or percent > 1:
            print("Percent must be between 0 and 1.")
            return False
        return True

    # def connect to mt5 account
    def connect(self, account, password, server):
        # connect to the trade account without specifying a password and a server
        self.account = account
        self.server = server
        self.password = password

        authorized = mt5.login(
            self.account, password=self.password, server=self.server
        )  # the terminal database password is applied if connection data is set to be remembered
        if authorized:
            print("connected to account #{}. Please Turn On Algo Trading".format(account))
        else:
            print(
                "failed to connect at account #{}, error code: {}".format(
                    account, mt5.last_error()
                )
            )

    # define open buy position
    def open_buy(
        self,
        symbol,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=260000,
        comment="MT5pytrader",
    ):
        """
        Opens a Buy Position with the input parameters.

        Parameters:
            symbol: Symbol to open position
            lot: Position size to open
            sl: stop loss in points
            tp: take profit in points
            comment: Custom comment for the trade position
            magic: custom magic number for the trade position

        """

        self.symbol = symbol
        self.lot = lot
        self.comment = comment
        self.magic = magic
        self.sl = stop_loss
        self.tp = take_profit

        if not self._ensure_symbol(self.symbol):
            return

        point = mt5.symbol_info(self.symbol).point
        price = mt5.symbol_info_tick(self.symbol).bid
        sl_price, tp_price = self._calculate_sl_tp(
            price, point, self.sl, self.tp, is_buy=True
        )

        request = self._build_open_request(
            mt5.TRADE_ACTION_DEAL,
            symbol,
            self.lot,
            mt5.ORDER_TYPE_BUY,
            price,
            sl=sl_price,
            tp=tp_price,
        )

        # send a trading request
        self._send_request(
            request,
            f"SENDING ORDER: BUY {self.symbol} {self.lot} lots at {price} "
            f"with deviation={self.deviation} points",
        )

    # define open sell position
    def open_sell(
        self,
        symbol,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=260000,
        comment="MT5pytrader",
    ):
        """
        Opens a Sell Position with the input parameters.

        Parameters:
            symbol: Symbol to open position
            lot: Position size to open
            sl: stop loss in points
            tp: take profit in points
            comment: Custom comment for the trade position
            magic: custom magic number for the trade position

        """

        self.symbol = symbol
        self.lot = lot
        self.comment = comment
        self.magic = magic
        self.sl = stop_loss
        self.tp = take_profit

        if not self._ensure_symbol(self.symbol):
            return

        point = mt5.symbol_info(self.symbol).point
        price = mt5.symbol_info_tick(self.symbol).ask
        sl_price, tp_price = self._calculate_sl_tp(
            price, point, self.sl, self.tp, is_buy=False
        )

        request = self._build_open_request(
            mt5.TRADE_ACTION_DEAL,
            symbol,
            self.lot,
            mt5.ORDER_TYPE_SELL,
            price,
            sl=sl_price,
            tp=tp_price,
        )

        # send a trading request
        self._send_request(
            request,
            f"SENDING ORDER: SELL {self.symbol} {self.lot} lots at {price} "
            f"with deviation={self.deviation} points",
        )

    # define open buy limit
    def open_buy_limit(
        self,
        symbol,
        price,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=260000,
        comment="MT5pytrader",
    ):
        """
        Opens a Buy Limit with the input parameters.

        Parameters:
            symbol: Symbol to place a buy limit
            price: price to open a buy limit
            lot: Position size to open
            sl: stop loss in points
            tp: take profit in points
            comment: Custom comment for the trade position
            magic: custom magic number for the trade position

        """

        self.symbol = symbol
        self.price = price
        self.lot = lot
        self.comment = comment
        self.magic = magic
        self.sl = stop_loss
        self.tp = take_profit

        if not self._ensure_symbol(self.symbol):
            return

        point = mt5.symbol_info(self.symbol).point
        sl_price, tp_price = self._calculate_sl_tp(
            self.price, point, self.sl, self.tp, is_buy=True
        )

        request = self._build_open_request(
            mt5.TRADE_ACTION_PENDING,
            symbol,
            self.lot,
            mt5.ORDER_TYPE_BUY_LIMIT,
            self.price,
            sl=sl_price,
            tp=tp_price,
        )

        # send a trading request
        self._send_request(
            request,
            f"SENDING ORDER: BUY LIMIT {self.symbol} {self.lot} lots at {self.price} "
            f"with deviation={self.deviation} points",
        )

    # define open SELL limit
    def open_sell_limit(
        self,
        symbol,
        price,
        lot=0.1,
        stop_loss=None,
        take_profit=None,
        magic=260000,
        comment="MT5pytrader",
    ):
        """
        Opens a Sell Limit with the input parameters.

        Parameters:
            symbol: Symbol to place a sell limit
            price: price to open a sell limit
            lot: Position size to open
            sl: stop loss in points
            tp: take profit in points
            comment: Custom comment for the trade position
            magic: custom magic number for the trade position

        """

        self.symbol = symbol
        self.price = price
        self.lot = lot
        self.comment = comment
        self.magic = magic
        self.sl = stop_loss
        self.tp = take_profit

        if not self._ensure_symbol(self.symbol):
            return

        point = mt5.symbol_info(self.symbol).point
        sl_price, tp_price = self._calculate_sl_tp(
            self.price, point, self.sl, self.tp, is_buy=False
        )

        request = self._build_open_request(
            mt5.TRADE_ACTION_PENDING,
            symbol,
            self.lot,
            mt5.ORDER_TYPE_SELL_LIMIT,
            self.price,
            sl=sl_price,
            tp=tp_price,
        )

        # send a trading request
        self._send_request(
            request,
            f"SENDING ORDER: SELL LIMIT {self.symbol} {self.lot} lots at {self.price} "
            f"with deviation={self.deviation} points",
        )

    # def close buy position
    def close_buy(self, symbol=None, ticket_id=None):
        """
        Close a Buy Position with the ticket_id and symbol.

        Parameters:
            symbol: Symbol to open position
            ticket_id: position id/ order_no

        """

        self.ticket_id = ticket_id
        self.symbol = symbol

        if self.ticket_id is not None:
            positions = self._get_positions_by_ticket(self.ticket_id)
            for position in positions:
                symbol = position.symbol
                if not self._ensure_symbol(symbol):
                    continue
                price = mt5.symbol_info_tick(symbol).bid
                request = self._build_close_request(
                    symbol,
                    position.volume,
                    mt5.ORDER_TYPE_SELL,
                    self.ticket_id,
                    price,
                )
                self._send_request(
                    request,
                    "close position #{}: sell {} {} lots at {} with deviation={} points".format(
                        self.ticket_id,
                        symbol,
                        position.volume,
                        price,
                        self.deviation,
                    ),
                )
            return

        if not self._ensure_symbol(self.symbol):
            return

        positions = self._get_positions_by_symbol(self.symbol)
        for position in positions:
            price = mt5.symbol_info_tick(self.symbol).bid
            request = self._build_close_request(
                self.symbol,
                position.volume,
                mt5.ORDER_TYPE_SELL,
                position.ticket,
                price,
            )
            self._send_request(
                request,
                "close position #{}: sell {} {} lots at {} with deviation={} points".format(
                    position.ticket,
                    self.symbol,
                    position.volume,
                    price,
                    self.deviation,
                ),
            )

    # def close sell position
    def close_sell(self, symbol=None, ticket_id=None):
        """
        Close a Sell Position with the ticket_id and symbol.

        Parameters:
            symbol: Symbol to open position
            ticket_id: position id/ order_no

        """

        self.ticket_id = ticket_id
        self.symbol = symbol

        if self.ticket_id is not None:
            positions = self._get_positions_by_ticket(self.ticket_id)
            for position in positions:
                symbol = position.symbol
                if not self._ensure_symbol(symbol):
                    continue
                price = mt5.symbol_info_tick(symbol).ask
                request = self._build_close_request(
                    symbol,
                    position.volume,
                    mt5.ORDER_TYPE_BUY,
                    self.ticket_id,
                    price,
                )
                self._send_request(
                    request,
                    "close position #{}: buy {} {} lots at {} with deviation={} points".format(
                        self.ticket_id,
                        symbol,
                        position.volume,
                        price,
                        self.deviation,
                    ),
                )
            return

        if not self._ensure_symbol(self.symbol):
            return

        positions = self._get_positions_by_symbol(self.symbol)
        for position in positions:
            price = mt5.symbol_info_tick(self.symbol).ask
            request = self._build_close_request(
                self.symbol,
                position.volume,
                mt5.ORDER_TYPE_BUY,
                position.ticket,
                price,
            )
            self._send_request(
                request,
                "close position #{}: buy {} {} lots at {} with deviation={} points".format(
                    position.ticket,
                    self.symbol,
                    position.volume,
                    price,
                    self.deviation,
                ),
            )

    # def close PARTIAL buy position
    def close_partial_buy(self, percent, symbol=None, ticket_id=None):
        """
        Close a Buy Position partialy with the input parameters.

        Parameters:
            symbol: Symbol to open position
            percent : percentage of volume to close, e.g - to close half of position = 0.5
            ticket_id: position id/ order_no of position

        """

        self.symbol = symbol
        self.ticket_id = ticket_id
        self.percent = percent

        if not self._validate_partial_percent(self.percent):
            return

        if self.ticket_id is not None:
            positions = self._get_positions_by_ticket(self.ticket_id)
            for position in positions:
                symbol = position.symbol
                if not self._ensure_symbol(symbol):
                    continue
                price = mt5.symbol_info_tick(symbol).bid
                request = self._build_close_request(
                    symbol,
                    round((position.volume * percent), 2),
                    mt5.ORDER_TYPE_SELL,
                    self.ticket_id,
                    price,
                )
                self._send_request(
                    request,
                    "close position #{}: sell {} {} lots at {} with deviation={} points".format(
                        self.ticket_id,
                        symbol,
                        position.volume,
                        price,
                        self.deviation,
                    ),
                )
            return

        if not self._ensure_symbol(self.symbol):
            return

        positions = self._get_positions_by_symbol(self.symbol)
        for position in positions:
            price = mt5.symbol_info_tick(self.symbol).bid
            request = self._build_close_request(
                self.symbol,
                round((position.volume * percent), 2),
                mt5.ORDER_TYPE_SELL,
                position.ticket,
                price,
            )
            self._send_request(
                request,
                "close position #{}: sell {} {} lots at {} with deviation={} points".format(
                    position.ticket,
                    self.symbol,
                    position.volume,
                    price,
                    self.deviation,
                ),
            )

    # def close partial sell position
    def close_partial_sell(self, percent, symbol=None, ticket_id=None):
        """
        Close a Sell Position partially with the ticket_id and symbol.

        Parameters:
            symbol: Symbol to open position
            percent : percentage of volume to close, e.g - to close half of position = 0.5
            ticket_id: position id/ order_no of position

        """

        self.ticket_id = ticket_id
        self.symbol = symbol
        self.percent = percent

        if not self._validate_partial_percent(self.percent):
            return

        if self.ticket_id is not None:
            positions = self._get_positions_by_ticket(self.ticket_id)
            for position in positions:
                symbol = position.symbol
                if not self._ensure_symbol(symbol):
                    continue
                price = mt5.symbol_info_tick(symbol).ask
                request = self._build_close_request(
                    symbol,
                    round((position.volume * percent), 2),
                    mt5.ORDER_TYPE_BUY,
                    self.ticket_id,
                    price,
                )
                self._send_request(
                    request,
                    "close position #{}: buy {} {} lots at {} with deviation={} points".format(
                        self.ticket_id,
                        symbol,
                        position.volume,
                        price,
                        self.deviation,
                    ),
                )
            return

        if not self._ensure_symbol(self.symbol):
            return

        positions = self._get_positions_by_symbol(self.symbol)
        for position in positions:
            price = mt5.symbol_info_tick(self.symbol).ask
            request = self._build_close_request(
                self.symbol,
                round((position.volume * percent), 2),
                mt5.ORDER_TYPE_BUY,
                position.ticket,
                price,
            )
            self._send_request(
                request,
                "close position #{}: buy {} {} lots at {} with deviation={} points".format(
                    position.ticket,
                    self.symbol,
                    position.volume,
                    price,
                    self.deviation,
                ),
            )

    # get all open positions
    def get_open_positions(self):
        """
        Get all open positions in the MT5 terminal.

        Returns:
            An float of cummulative running profit/loss

        """

        positions = mt5.positions_get()

        if positions is None or len(positions) == 0:
            print("No Open Position")
            return None

        df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())
        df.drop(
            [
                "magic",
                "time_msc",
                "time_update_msc",
                "time_update",
                "external_id",
                "identifier",
                "reason",
            ],
            axis=1,
            inplace=True,
        )
        df["time"] = pd.to_datetime(df["time"], unit="s")

        return df

    # get sum of running trades proft/loss
    def running_profit(self):
        """
        Get cummulative sum of all running trades (profit/loss).

        Returns:
            An float of cummulative running profit/loss

        """

        df = self.get_open_positions()
        if df is None:
            return 0.0

        return round(df["profit"].sum(), 2)

    # def modify stop loss
    def modify_sl(self, symbol=None, ticket_id=None, sl=None):
        """
        Modify a Position with the input parameters.

        Parameters:
            symbol: Symbol to open position
            ticket: position_id/order number of the trade to modify
            sl: stop loss price

        """

        self.symbol = symbol
        self.ticket_id = ticket_id
        self.sl = sl

        if self.ticket_id is not None:
            positions = self._get_positions_by_ticket(self.ticket_id)
        elif self.symbol is not None:
            if not self._ensure_symbol(self.symbol):
                return
            positions = self._get_positions_by_symbol(self.symbol)
        else:
            print("Symbol or ticket_id is required.")
            return

        for position in positions:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": position.ticket,
                "sl": self.sl,
                "tp": position.tp,
                "comment": self.comment,
                "type_time": self.type_time,
                "type_filling": self.type_filling,
            }
            self._send_request(request, "order sending")

    # def modify take profit
    def modify_tp(self, symbol=None, ticket_id=None, tp=None):
        """
        Modify a Position with the input parameters.

        Parameters:
            symbol: Symbol to open position
            ticket: position_id/order number of the trade to modify
            tp: take profit price

        """

        self.symbol = symbol
        self.ticket_id = ticket_id
        self.tp = tp

        if self.ticket_id is not None:
            positions = self._get_positions_by_ticket(self.ticket_id)
        elif self.symbol is not None:
            if not self._ensure_symbol(self.symbol):
                return
            positions = self._get_positions_by_symbol(self.symbol)
        else:
            print("Symbol or ticket_id is required.")
            return

        for position in positions:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": position.ticket,
                "sl": position.sl,
                "tp": self.tp,
                "comment": self.comment,
                "type_time": self.type_time,
                "type_filling": self.type_filling,
            }
            self._send_request(request, "order sending")

    # def break even on profit trade
    def break_even(self, symbol=None, ticket_id=None):
        """
        Break even on a profit Position using position ticket_id or symbol.

        Parameters:
            symbol: Symbol to open position
            ticket: position_id/order number of the trade to modify

        """
        self.symbol = symbol
        self.ticket = ticket_id

        if self.ticket is not None:
            positions = self._get_positions_by_ticket(self.ticket)
        elif self.symbol is not None:
            if not self._ensure_symbol(self.symbol):
                return
            positions = self._get_positions_by_symbol(self.symbol)
        else:
            print("Symbol or ticket_id is required.")
            return

        for position in positions:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": position.ticket,
                "sl": position.price_open,
                "comment": self.comment,
                "type_time": self.type_time,
                "type_filling": self.type_filling,
            }
            self._send_request(request, "order sending")
