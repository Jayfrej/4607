import os
import logging
import json
from datetime import datetime
from .config import LOG_DIR, LOG_FORMAT, LOG_LEVEL

def setup_logging(name, log_to_file=True):
    """
    Set up logging configuration
    
    Args:
        name (str): Logger name
        log_to_file (bool): Whether to log to a file
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if logging to file
    if log_to_file:
        log_file = os.path.join(LOG_DIR, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def save_webhook_url(webhook_url):
    base_url = webhook_url.rsplit('/', 1)[0]
    with open('webhook_url.txt', 'w') as f:
        f.write('base URL (optional: only needed if you are testing with Postman - `ngrokUrl` environment variable)\n')
        f.write('===============\n')
        f.write(base_url + '\n')
        f.write('\n')
        f.write('\n')
        f.write('paste this URL in TradingView alerts Webhook URL section\n')
        f.write('===============\n')
        f.write(webhook_url + '\n')
    print('Webhook URL saved to webhook_url.txt')
    return

def parse_tradingview_webhook(data):
    """
    Parse and validate TradingView webhook data
    
    Args:
        data (dict): Webhook data from TradingView
        
    Returns:
        dict: Validated and processed webhook data
    """
    required_fields = ['symbol', 'side']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Get symbol from data
    symbol = str(data['symbol'])
    
    # Remove any existing suffix if present (shouldn't be in TradingView data)
    from .config import MT5_DEFAULT_SUFFIX
    if MT5_DEFAULT_SUFFIX and symbol.endswith(MT5_DEFAULT_SUFFIX):
        symbol = symbol[:-len(MT5_DEFAULT_SUFFIX)]
    
    # Normalize and validate fields
    result = {
        'symbol': symbol,  # Symbol without suffix - suffix will be added in the MT5 handler
        'side': str(data['side']).upper(),  # Uppercase side for consistency
        'volume': float(data.get('volume', 0.01)),
        'price': float(data.get('price', 0)),
        'stop_loss': float(data.get('stop_loss', 100)),
        'take_profit': float(data.get('take_profit', 200)),
        'comment': str(data.get('comment', 'TradingView Signal'))
    }
    
    # Additional validation
    if result['volume'] <= 0:
        raise ValueError(f"Invalid volume: {result['volume']}")
    
    if result['side'] not in ['BUY', 'SELL', 'LONG', 'SHORT']:
        raise ValueError(f"Invalid side: {result['side']}")
    
    return result