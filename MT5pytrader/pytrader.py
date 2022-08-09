import numpy as np
import pandas as pd
import datetime 
import time
import MetaTrader5 as mt5
    
class Trader: #parent
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
    
    def __init__(self, comment = "MT5pytrader", magic = 260000, deviation = 20, type_time = mt5.ORDER_TIME_GTC, type_filling = mt5.SYMBOL_TRADE_EXECUTION_INSTANT):
        
        # establish connection to the MetaTrader 5 terminal
        if not mt5.initialize():
            print("initialize() failed, error code =",mt5.last_error())

        else:
            print("successfully initialized. Please allow Auto trading")
            #quit()
            
        self.comment = comment #"MT5pytrader"
        self.magic = magic #260000
        self.deviation = deviation #20
        self.type_time = type_time #mt5.ORDER_TIME_GTC
        self.type_filling = type_filling #mt5.SYMBOL_TRADE_EXECUTION_INSTANT
        
    def __repr__(self):
        return "MT5pytrader Instance"
        #return f"MT5pytrader(symbol: {self.symbol}, Lot_size: {self.lot}, Stop_loss: {self.sl}, Take_profit: {self.tp})"
    
    #def connect to mt5 account
    def connect(self, account, password, server):
        # connect to the trade account without specifying a password and a server
        self.account = account
        self.server = server
        self.password = password

        authorized=mt5.login(self.account, password = self.password, server = self.server)  # the terminal database password is applied if connection data is set to be remembered
        if authorized:
            print("connected to account #{}. Please Turn On Algo Trading".format(account))
        else:
            print("failed to connect at account #{}, error code: {}".format(account, mt5.last_error()))

    
    # define open buy position
    def open_buy(self, symbol, lot = 0.1, stop_loss = None, take_profit = None, magic = 260000, comment = "MT5pytrader"):
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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        point = mt5.symbol_info(self.symbol).point
        price = mt5.symbol_info_tick(self.symbol).bid
        
        
        if self.sl != None and self.tp == None:  #if sl only is defined
        
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "sl": price - (self.sl * point), 
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }

        elif self.tp != None and self.sl == None:  #if tp only is defined
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "tp": price + (self.tp * point),
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling,}

        elif self.sl == None and self.tp == None:  #if sl and tp are not defined

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }
            
        elif self.sl != None and self.tp != None:  #if sl and tp are defined

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic,
                "sl": price - (self.sl * point),
                "tp": price + (self.tp * point),
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }


        # send a trading request
        result = mt5.order_send(request)
        # check the execution result
        print("SENDING ORDER: BUY {} {} lots at {} with deviation={} points".format(self.symbol,self.lot,price,self.deviation));
        if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
            print(" - order_send failed, retcode={}".format(result.retcode))

            # request the result as a dictionary and display it element by element
            result_dict=result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
        else:
            print(f"Order Sent! {result.order}")
            
    
    # define open sell position
    def open_sell(self, symbol, lot = 0.1, stop_loss = None, take_profit = None, magic = 260000, comment = "MT5pytrader"):
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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        point = mt5.symbol_info(self.symbol).point
        price = mt5.symbol_info_tick(self.symbol).ask     
        
        if self.sl != None and self.tp == None:  #if sl only is defined
        
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": price + (self.sl * point), 
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }

        elif self.tp != None and self.sl == None:  #if tp only is defined
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "tp": price - (self.tp * point),
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling,
            }

        elif self.sl == None and self.tp == None:  #if sl and tp are not defined

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }
            
        elif self.sl != None and self.tp != None:  #if sl and tp are defined

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic,
                "sl": price + (self.sl * point),
                "tp": price - (self.tp * point),
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }


        # send a trading request
        result = mt5.order_send(request)
        # check the execution result
        print("SENDING ORDER: SELL {} {} lots at {} with deviation={} points".format(self.symbol,self.lot,price,self.deviation));
        if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
            print(" - order_send failed, retcode={}".format(result.retcode))

            # request the result as a dictionary and display it element by element
            result_dict=result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
        else:
            print(f"Order Sent! {result.order}")



    # define open buy limit 
    def open_buy_limit(self, symbol, price, lot = 0.1, stop_loss = None, take_profit = None, magic = 260000, comment = "MT5pytrader"):
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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        point = mt5.symbol_info(self.symbol).point
        
        
        if self.sl != None and self.tp == None:  #if sl only is defined
        
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": self.price,
                "sl": self.price - (self.sl * point), 
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling,
            }

        elif self.tp != None and self.sl == None:  #if tp only is defined
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": self.price,
                "tp": self.price + (self.tp * point),
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling,}

        elif self.sl == None and self.tp == None:  #if sl and tp are not defined

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": self.price,
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }
            
        elif self.sl != None and self.tp != None:  #if sl and tp are defined

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": self.price,
                "deviation": self.deviation,
                "magic": self.magic,
                "sl": self.price - (self.sl * point),
                "tp": self.price + (self.tp * point),
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling,
            }


        # send a trading request
        result = mt5.order_send(request)
        # check the execution result
        print("SENDING ORDER: BUY LIMIT {} {} lots at {} with deviation={} points".format(self.symbol,self.lot,self.price,self.deviation));
        if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
            print(" - order_send failed, retcode={}".format(result.retcode))

            # request the result as a dictionary and display it element by element
            result_dict=result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
        else:
            print(f"Order Sent! {result.order}")
            
            

    # define open SELL limit 
    def open_sell_limit(self, symbol, price, lot = 0.1, stop_loss = None, take_profit = None, magic = 260000, comment = "MT5pytrader"):
        """
        Opens a sell Limit with the input parameters.

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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        point = mt5.symbol_info(self.symbol).point       
        
        if self.sl != None and self.tp == None:  #if sl only is defined
        
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL_LIMIT,
                "price": self.price,
                "sl": self.price + (self.sl * point), 
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }

        elif self.tp != None and self.sl == None:  #if tp only is defined
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL_LIMIT,
                "price": self.price,
                "tp": self.price - (self.tp * point),
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling,}

        elif self.sl == None and self.tp == None:  #if sl and tp are not defined

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL_LIMIT,
                "price": self.price,
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }
            
        elif self.sl != None and self.tp != None:  #if sl and tp are defined

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": self.lot,
                "type": mt5.ORDER_TYPE_SELL_LIMIT,
                "price": self.price,
                "deviation": self.deviation,
                "magic": self.magic,
                "sl": self.price + (self.sl * point),
                "tp": self.price - (self.tp * point),
                "comment": self.comment,
                "type_time":self.type_time,
                "type_filling": self.type_filling, 
            }


        # send a trading request
        result = mt5.order_send(request)
        # check the execution result
        print("SENDING ORDER: SELL LIMIT {} {} lots at {} with deviation={} points".format(self.symbol,self.lot, self.price,self.deviation));
        if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
            print(" - order_send failed, retcode={}".format(result.retcode))

            # request the result as a dictionary and display it element by element
            result_dict=result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
        else:
            print(f"Order Sent! {result.order}")
            
            
    #def close buy position
    def close_buy(self, symbol = None, ticket_id = None):
        
        """
        Close a Buy Position with the ticket_id and symbol.

        Parameters:
            symbol: Symbol to open position
            ticket_id: position id/ order_no
            
            """
        
        self.ticket_id = ticket_id
        self.symbol = symbol
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        #get position using position_id
        if self.ticket_id != None:
            
            positions=mt5.positions_get(ticket = self.ticket_id)
            if len(positions) == 0:
                print(f"No positions on {self.ticket_id}, error code={mt5.last_error()}")
                pass
            elif len(positions) > 0:
                for position in positions:

                    # create a close request
                    symbol = position.symbol
                    price=mt5.symbol_info_tick(symbol).ask
                    
                    request={
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": position.volume,
                        "type": mt5.ORDER_TYPE_SELL,
                        "position": self.ticket_id,
                        "price": price,
                        "deviation": self.deviation,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }
                    # send a trading request
                    result=mt5.order_send(request)
                    # check the execution result
                    print("close position #{}: sell {} {} lots at {} with deviation={} points".format(self.ticket_id,symbol,position.volume,price,self.deviation));
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print("Close Position failed, retcode={}".format(result.retcode))
                        #print("   result",result)
                    else:
                        print(f"position #{self.ticket_id} closed, {result}")
                        # request the result as a dictionary and display it element by element
                
        elif self.ticket_id == None:
            # get open positions by symbol
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                pass
            elif len(positions)>0:
                print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    #print(position)
                    position_id= position.identifier

                # create a close request
                price=mt5.symbol_info_tick(self.symbol).ask

                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": position.volume,
                    "type": mt5.ORDER_TYPE_SELL,
                    "position": position_id,
                    "price": price,
                    "deviation": self.deviation,
                    "type_time":self.type_time,
                    "type_filling": self.type_filling,
                }
                # send a trading request
                result=mt5.order_send(request)
                # check the execution result
                print("close position #{}: sell {} {} lots at {} with deviation={} points".format(position_id,self.symbol,position.volume,price,self.deviation));
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print("Close Position failed, retcode={}".format(result.retcode))
                    #print("   result",result)
                else:
                    print(f"position #{position_id} closed, {result}")
                    # request the result as a dictionary and display it element by element                

    
    #def close sell position
    def close_sell(self, symbol = None, ticket_id = None):
        
        """
        Close a Sell Position with the ticket_id and symbol.

        Parameters:
            symbol: Symbol to open position
            ticket_id: position id/ order_no
            
            """
        
        self.ticket_id = ticket_id
        self.symbol = symbol
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        #get position using position_id
        if self.ticket_id != None:
            
            positions=mt5.positions_get(ticket = self.ticket_id)
            if len(positions) == 0:
                print(f"No positions on {self.ticket_id}, error code={mt5.last_error()}")
                pass
            
            elif len(positions) > 0:
                for position in positions:

                    # create a close request
                    symbol = position.symbol
                    price=mt5.symbol_info_tick(symbol).ask
                    
                    request={
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": position.volume,
                        "type": mt5.ORDER_TYPE_BUY,
                        "position": self.ticket_id,
                        "price": price,
                        "deviation": self.deviation,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }
                    
                    # send a trading request
                    result=mt5.order_send(request)
                    # check the execution result
                    print("close position #{}: buy {} {} lots at {} with deviation={} points".format(self.ticket_id,symbol,position.volume,price,self.deviation));
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print("Close Position failed, retcode={}".format(result.retcode))
                        #print("   result",result)
                    else:
                        print(f"position #{self.ticket_id} closed, {result}")
                        # request the result as a dictionary and display it element by element
                
        elif self.ticket_id is None:
            # get open positions by symbol
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                pass
            elif len(positions)>0:
                print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    #print(position)
                    lot = position.volume
                    position_id= position.identifier

                # create a close request
                price=mt5.symbol_info_tick(self.symbol).bid
                deviation=20
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_BUY,
                    "position": position_id,
                    "price": price,
                    "deviation": self.deviation,
                    "type_time":self.type_time,
                    "type_filling": self.type_filling,
                }
                # send a trading request
                result=mt5.order_send(request)
                # check the execution result
                print("close position #{}: buy {} {} lots at {} with deviation={} points".format(position_id,self.symbol,position.volume,price,self.deviation));
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print("Close Position failed, retcode={}".format(result.retcode))
                    #print("   result",result)
                else:
                    print(f"position #{position_id} closed, {result}")
                    
                    
    #def close PARTIAL buy position
    def close_partial_buy(self, percent, symbol = None, ticket_id = None):
        
        """"
        
        Close a Buy Position partialy with the input parameters.

        Parameters:
            symbol: Symbol to open position
            percent : percentage of volume to close, e.g - to close half of position = 0.5
            ticket_id: position id/ order_no of position
            
            """
    
        self.symbol = symbol
        self.ticket_id = ticket_id
        self.percent = percent
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        #get position using position_id
        if self.ticket_id != None:
            
            positions=mt5.positions_get(ticket = self.ticket_id)
            if len(positions) == 0:
                print(f"No positions on {self.ticket_id}, error code={mt5.last_error()}")
                pass
            elif len(positions) > 0:
                for position in positions:

                    # create a close request
                    symbol = position.symbol
                    price=mt5.symbol_info_tick(symbol).ask
                    lot = position.volume
                    
                    request={
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": round((lot * percent), 2),
                        "type": mt5.ORDER_TYPE_SELL,
                        "position": self.ticket_id,
                        "price": price,
                        "deviation": self.deviation,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }
                    # send a trading request
                    result=mt5.order_send(request)
                    # check the execution result
                    print("close position #{}: sell {} {} lots at {} with deviation={} points".format(self.ticket_id,symbol,position.volume,price,self.deviation));
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print("Close Position failed, retcode={}".format(result.retcode))
                        #print("   result",result)
                    else:
                        print(f"position #{self.ticket_id} closed, {result}")
                        # request the result as a dictionary and display it element by element
                
        elif self.ticket_id == None:
            # get open positions by symbol
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                pass
            elif len(positions)>0:
                print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    #print(position)
                    position_id= position.identifier
                    lot = position.volume

                    # create a close request
                    price=mt5.symbol_info_tick(self.symbol).ask
                    deviation=20
                    request={
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": self.symbol,
                        "volume": round((lot * percent), 2),
                        "type": mt5.ORDER_TYPE_SELL,
                        "position": position_id,
                        "price": price,
                        "deviation": self.deviation,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }
                # send a trading request
                result=mt5.order_send(request)
                # check the execution result
                print("close position #{}: sell {} {} lots at {} with deviation={} points".format(position_id,self.symbol,lot,price,self.deviation));
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print("Close Position failed, retcode={}".format(result.retcode))
                    #print("   result",result)
                else:
                    print(f"position #{position_id} closed, {result}")
                    # request the result as a dictionary and display it element by element      
            
            
    #def close partial sell position
    def close_partial_sell(self,  percent, symbol = None, ticket_id = None):
        
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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
        
        #get position using position_id
        if self.ticket_id != None:
            
            positions=mt5.positions_get(ticket = self.ticket_id)
            if len(positions) == 0:
                print(f"No positions on {self.ticket_id}, error code={mt5.last_error()}")
                pass
            
            elif len(positions) > 0:
                for position in positions:

                    # create a close request
                    symbol = position.symbol
                    price=mt5.symbol_info_tick(symbol).bid
                    lot = position.volume
                    
                    request={
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": round((lot * percent), 2),
                        "type": mt5.ORDER_TYPE_BUY,
                        "position": self.ticket_id,
                        "price": price,
                        "deviation": self.deviation,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }
                    
                # send a trading request
                result=mt5.order_send(request)
                # check the execution result
                print("close position #{}: buy {} {} lots at {} with deviation={} points".format(self.ticket_id,symbol,position.volume,price,self.deviation));
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print("Close Position failed, retcode={}".format(result.retcode))
                    #print("   result",result)
                else:
                    print(f"position #{self.ticket_id} closed, {result}")
                    # request the result as a dictionary and display it element by element
                
        elif self.ticket_id is None:
            # get open positions by symbol
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                pass
            elif len(positions)>0:
                print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    #print(position)
                    position_id= position.identifier
                    lot = position.volume

                # create a close request
                price=mt5.symbol_info_tick(self.symbol).bid
                deviation=20
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": round((lot * percent), 2),
                    "type": mt5.ORDER_TYPE_BUY,
                    "position": position_id,
                    "price": price,
                    "deviation": self.deviation,
                    "type_time":self.type_time,
                    "type_filling": self.type_filling,
                }
                # send a trading request
                result=mt5.order_send(request)
                # check the execution result
                print("close position #{}: buy {} {} lots at {} with deviation={} points".format(position_id,self.symbol,lot,price,self.deviation));
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print("Close Position failed, retcode={}".format(result.retcode))
                    #print("   result",result)
                else:
                    print(f"position #{position_id} closed, {result}")
                    
               
    #get all open positions
    def get_open_positions(self):
        """"
        Get all open positions in the MT5 terminal.
        
        Returns:
            An float of cummulative running profit/loss
            
            """
        
        symbols = mt5.symbols_get() #get all symbols in marcket watch

        open_pos = []
        for symbol in symbols:
            positions=mt5.positions_get(symbol = symbol.name)

            if positions == None:
                #print("No open positions")
                pass

            elif positions != None:
                for position in positions:
                    open_pos.append(position)
                    #print(position)

        if len(open_pos) == 0:
            print("No Open Position")
            df = None

        elif len(open_pos) > 0:
            #print (f"open positions = {len(open_pos)}")

            # display running trades as a table using pandas.DataFrame
            df= pd.DataFrame(open_pos, columns=position._asdict().keys())
            df.drop(['magic', 'time_msc', 'time_update_msc','time_update','external_id', 'identifier','reason'], axis=1, inplace=True)
            #df['time_msc'] = pd.to_datetime(df['time_msc'], unit='s')
            df['time'] = pd.to_datetime(df['time'], unit='s')

        return df
    
    
    #get sum of running trades proft/loss
    def running_profit(self):
        """"
        Get cummulative sum of all running trades (profit/loss).
           
        Returns:
            An float of cummulative running profit/loss
            
            """

        profit = []

        if self.get_open_positions() is None:
            pass
            #print ("No running trades")

        else:
            df = self.get_open_positions()
            for index, row in df.iterrows():
                profit.append(row[9])

        return round(sum(profit),2)
    
    
    #def modify stop loss    
    def modify_sl(self, symbol = None, ticket_id = None, sl = None):
        
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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
                
        
        if self.ticket_id is not None: 
            # prepare the request
            positions=mt5.positions_get(ticket = self.ticket_id)
            
            if len(positions) == 0 :
                print(f"No positions with position_id {self.ticket_id}, error code={mt5.last_error()}")
                pass
            
            elif len(positions)>0:
                #print(f"Total positions on {self.symbol} =",len(positions))
                
                # display all open positions
                for position in positions:
                    #print(position)
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": position.symbol,
                        "position": self.ticket_id,
                        "sl": self.sl,
                        "tp": position.tp,
                        "comment": self.comment,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }

                # send a trading request
                result = mt5.order_send(request)
                # check the execution result
                print ("order sending")
                
                if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
                    print(" - order_send failed, retcode={}".format(result.retcode))

                    # request the result as a dictionary and display it element by element
                    result_dict=result._asdict()
                    for field in result_dict.keys():
                        print("   {}={}".format(field,result_dict[field]))
                        # if this is a trading request structure, display it element by element as well
                        if field=="request":
                            traderequest_dict=result_dict[field]._asdict()
                            for tradereq_filed in traderequest_dict:
                                print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
                else:
                    print(f"Order Sent! {result.order}")
        
        
        elif self.symbol is not None: 
        
            # prepare the request
            
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                #pass
            
            elif len(positions)>0:
                print(f"Total positions on {self.symbol} =",len(positions))
                
                # display all open positions
                for position in positions:
                    #print(position)
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": self.symbol,
                        "position": position.ticket,
                        "sl": self.sl,
                        "tp": position.tp,
                        "comment": self.comment,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }

                # send a trading request
                result = mt5.order_send(request)
                # check the execution result
                print ("order sending")
                
                if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
                    print(" - order_send failed, retcode={}".format(result.retcode))

                    # request the result as a dictionary and display it element by element
                    result_dict=result._asdict()
                    for field in result_dict.keys():
                        print("   {}={}".format(field,result_dict[field]))
                        # if this is a trading request structure, display it element by element as well
                        if field=="request":
                            traderequest_dict=result_dict[field]._asdict()
                            for tradereq_filed in traderequest_dict:
                                print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
                else:
                    print(f"Order Sent! {result.order}")
               
            
    #def modify take profit      
    def modify_tp(self, symbol = None, ticket_id = None, tp = None):
        
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
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
                
        
        if self.ticket_id is not None: 
            # prepare the request
            positions=mt5.positions_get(ticket = self.ticket_id)
            if len(positions) == 0:
                print(f"No positions with position_id {self.ticket_id}, error code={mt5.last_error()}")
                pass
            
            elif len(positions)>0:
                #print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    #print(position)
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": position.symbol,
                        "position": self.ticket_id,
                        "sl" : position.sl,
                        "tp": self.tp,
                        "comment": self.comment,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }

            # send a trading request
            result = mt5.order_send(request)
            # check the execution result
            print ("order sending")
            
            if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
                print(" - order_send failed, retcode={}".format(result.retcode))

                # request the result as a dictionary and display it element by element
                result_dict=result._asdict()
                for field in result_dict.keys():
                    print("   {}={}".format(field,result_dict[field]))
                    # if this is a trading request structure, display it element by element as well
                    if field=="request":
                        traderequest_dict=result_dict[field]._asdict()
                        for tradereq_filed in traderequest_dict:
                            print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
            else:
                print(f"Order Sent! {result.order}")
        
        
        elif self.symbol is not None: 
        
            # prepare the request
            
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                pass
            
            elif len(positions)>0:
                #print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    #print(position)
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": self.symbol,
                        "position": position.ticket,
                        "sl": position.sl,
                        "tp": self.tp,
                        "comment": self.comment,
                        "type_time":self.type_time,
                        "type_filling": self.type_filling,
                    }

                        # send a trading request
            result = mt5.order_send(request)
            # check the execution result
            print ("order sending")
            
            if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
                print(" - order_send failed, retcode={}".format(result.retcode))

                # request the result as a dictionary and display it element by element
                result_dict=result._asdict()
                for field in result_dict.keys():
                    print("   {}={}".format(field,result_dict[field]))
                    # if this is a trading request structure, display it element by element as well
                    if field=="request":
                        traderequest_dict=result_dict[field]._asdict()
                        for tradereq_filed in traderequest_dict:
                            print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
            else:
                print(f"Order Sent! {result.order}")
                
    

    #def break even on profit trade
    def break_even(self, symbol = None, ticket_id = None):
        
        """"
        Break even on a profit Position using position ticket_id or symbol.
    
        Parameters:
            symbol: Symbol to open position
            ticket: position_id/order number of the trade to modify

            """
        self.symbol = symbol
        self.ticket = ticket_id
        
        #get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(self.symbol, "not found")
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(self.symbol,True):
                print("symbol_select({}}) failed, exit",syself.symbol)
                
        
        if self.ticket != None: 
            # prepare the request
            positions=mt5.positions_get(ticket = self.ticket)
            if len(positions) == 0:
                print(f"No positions with position_id {self.ticket}, error code={mt5.last_error()}")
                pass
            
            elif len(positions)>0:
                #print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": position.symbol,
                    "position": position.ticket,
                    "sl": position.price_open,
                    "comment": self.comment,
                    "type_time":self.type_time,
                    "type_filling": self.type_filling,
                }
                    
                # send a trading request
                result = mt5.order_send(request)
                # check the execution result
                print ("order sending")
                
                if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
                    print(" - order_send failed, retcode={}".format(result.retcode))

                    # request the result as a dictionary and display it element by element
                    result_dict=result._asdict()
                    for field in result_dict.keys():
                        print("   {}={}".format(field,result_dict[field]))
                        # if this is a trading request structure, display it element by element as well
                        if field=="request":
                            traderequest_dict=result_dict[field]._asdict()
                            for tradereq_filed in traderequest_dict:
                                print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
                else:
                    print(f"Order Sent! {result.order}")
        
        elif symbol != None: 
        
            # prepare the request
            
            positions=mt5.positions_get(symbol = self.symbol)
            if len(positions) == 0:
                print(f"No positions on {self.symbol}, error code={mt5.last_error()}")
                pass
            
            elif len(positions)>0:
                #print(f"Total positions on {self.symbol} =",len(positions))
                # display all open positions
                for position in positions:
                    request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "position": position.ticket,
                    "sl": position.price_open,
                    "comment": self.comment,
                    "type_time":self.type_time,
                    "type_filling": self.type_filling,
                }
                    
                # send a trading request
                result = mt5.order_send(request)
                # check the execution result
                print ("order sending")
                
                if result.retcode != mt5.TRADE_RETCODE_DONE or result.retcode == None:
                    print(" - order_send failed, retcode={}".format(result.retcode))

                    # request the result as a dictionary and display it element by element
                    result_dict=result._asdict()
                    for field in result_dict.keys():
                        print("   {}={}".format(field,result_dict[field]))
                        # if this is a trading request structure, display it element by element as well
                        if field=="request":
                            traderequest_dict=result_dict[field]._asdict()
                            for tradereq_filed in traderequest_dict:
                                print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
                else:
                    print(f"Order Sent! {result.order}")
        