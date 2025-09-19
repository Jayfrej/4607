import sys
import os
import pandas as pd
import time

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.utils import setup_logging
from app.config import MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER, MT5_PATH

# Try to import MetaTrader5
try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not found. Please install it using: pip install MetaTrader5")
    sys.exit(1)

# Set up logging
logger = setup_logging('mt5_test')

def test_mt5_connection():
    """Test connection to MetaTrader 5"""
    print("Testing MT5 connection...")
    
    # Connect to MT5
    if not mt5.initialize(path=MT5_PATH):
        print(f"MT5 initialize() failed. Error code: {mt5.last_error()}")
        return False
    
    # Attempt to login
    authorized = mt5.login(MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER)
    if not authorized:
        print(f"MT5 login failed. Error code: {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    # Display account info
    account_info = mt5.account_info()
    if account_info is None:
        print("Failed to get account info")
        mt5.shutdown()
        return False
    
    # Convert the account info to a dictionary
    account_dict = account_info._asdict()
    
    # Print account details
    print("\n=== Account Information ===")
    print(f"Name: {account_dict['name']}")
    print(f"Server: {account_dict['server']}")
    print(f"Balance: {account_dict['balance']}")
    print(f"Equity: {account_dict['equity']}")
    print(f"Margin: {account_dict['margin']}")
    print(f"Free Margin: {account_dict['margin_free']}")
    print(f"Leverage: 1:{account_dict['leverage']}")
    
    # Get available symbols
    symbols = mt5.symbols_get()
    print(f"\n=== Symbol Information ===")
    print(f"Total symbols available: {len(symbols)}")
    
    # Print first few symbols
    print("\nSample symbols:")
    for i, symbol in enumerate(symbols[:10]):
        print(f"{i+1}. {symbol.name}")
    
    # Test market data retrieval for a common symbol
    symbol = "EURUSD"
    print(f"\n=== Market Data Test for {symbol} ===")
    
    # Ensure the symbol is selected in Market Watch
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"Failed to select {symbol}")
    else:
        # Get current tick
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"Failed to get tick data for {symbol}")
        else:
            print(f"Current bid/ask: {tick.bid:.5f}/{tick.ask:.5f}")
        
        # Get recent OHLC data
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 5)
        if rates is None or len(rates) == 0:
            print(f"Failed to get rate data for {symbol}")
        else:
            # Convert to pandas dataframe for better display
            rates_df = pd.DataFrame(rates)
            rates_df['time'] = pd.to_datetime(rates_df['time'], unit='s')
            print("\nRecent 1-minute candles:")
            
            # Check for column name differences (some brokers use 'tick_volume' instead of 'volume')
            volume_col = 'volume' if 'volume' in rates_df.columns else 'tick_volume'
            
            # Print available columns
            print(f"Available columns: {list(rates_df.columns)}")
            
            # Display data with available columns
            display_cols = ['time', 'open', 'high', 'low', 'close'] 
            if volume_col in rates_df.columns:
                display_cols.append(volume_col)
                
            print(rates_df[display_cols])
    
    # Test open positions
    positions = mt5.positions_get()
    if positions is None:
        print("\n=== Open Positions ===")
        print("No open positions or error getting positions")
    else:
        print("\n=== Open Positions ===")
        print(f"Total open positions: {len(positions)}")
        if len(positions) > 0:
            for i, position in enumerate(positions[:5]):  # Show first 5 positions
                pos_dict = position._asdict()
                print(f"{i+1}. Symbol: {pos_dict['symbol']}, Type: {'Buy' if pos_dict['type'] == 0 else 'Sell'}, Volume: {pos_dict['volume']}, Profit: {pos_dict['profit']}")
    
    # Test market order function (commented out by default)
    # test_market_order(symbol)
    
    # Shutdown MT5 connection
    mt5.shutdown()
    print("\nMT5 connection test completed successfully!")
    return True

def test_market_order(symbol, volume=0.01):
    """
    Test placing a market order
    
    WARNING: This will place a real order. Only uncomment for testing with small volume.
    
    Args:
        symbol (str): Symbol to trade
        volume (float): Trade volume in lots
    """
    print(f"\n=== Testing Market Order ===")
    print(f"CAUTION: This will place a real order for {symbol} (volume: {volume})")
    confirm = input("Do you want to continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Market order test skipped")
        return False
    
    # Get current price
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to get price for {symbol}")
        return False
    
    # Prepare a request for a BUY market order
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": 10,
        "magic": 123456,
        "comment": "MT5 Connection Test",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Send the order
    result = mt5.order_send(request)
    
    # Check the result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed. Error code: {result.retcode}")
        print(f"Error description: {mt5.last_error()}")
        return False
    
    print(f"Order placed successfully. Order ID: {result.order}")
    
    # Wait a moment and then close the position
    print("Waiting 2 seconds before closing the position...")
    time.sleep(2)
    
    # Prepare a request to close the position
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL,
        "position": result.order,
        "price": tick.bid,
        "deviation": 10,
        "magic": 123456,
        "comment": "Close test order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Send the close order
    close_result = mt5.order_send(close_request)
    
    # Check the result
    if close_result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Close order failed. Error code: {close_result.retcode}")
        print(f"Error description: {mt5.last_error()}")
        return False
    
    print(f"Position closed successfully. Order ID: {close_result.order}")
    return True

if __name__ == "__main__":
    test_mt5_connection()