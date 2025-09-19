from flask import Flask, request, jsonify
import logging
from app.mt5_handler import MT5Handler
from app.config import Config

# ANSI Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Setup logging
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the MT5 handler - will be set in initialize_mt5()
mt5_handler = None

def log_health_check(message):
    """Log health check messages in ORANGE"""
    colored_message = f"{Colors.ORANGE}{message}{Colors.RESET}"
    logger.info(colored_message)

def log_success(message):
    """Log success messages in GREEN"""  
    colored_message = f"{Colors.GREEN}{message}{Colors.RESET}"
    logger.info(colored_message)

def log_error(message):
    """Log error messages in RED"""
    colored_message = f"{Colors.RED}{message}{Colors.RESET}"
    logger.error(colored_message)

def initialize_mt5():
    """Function to be called from main.py to connect to MT5."""
    global mt5_handler
    
    # Load configuration
    config = Config()
    
    # Create MT5 handler with proper arguments
    mt5_handler = MT5Handler(
        account=config.MT5_ACCOUNT,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
        path=config.MT5_PATH
    )
    
    # Connect to MT5
    return mt5_handler.connect()

@app.route('/trade', methods=['POST'])
def webhook():
    """Main webhook endpoint to process trading signals."""
    try:
        # Check if MT5 handler is initialized
        if mt5_handler is None:
            return jsonify({"error": "MT5 handler not initialized"}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        logger.info(f"Received webhook: {data}")

        action = data.get('action', '').upper()
        symbol = data.get('symbol')
        volume = data.get('volume')

        # Validate required fields
        if not symbol:
            return jsonify({"error": "Missing required field: symbol"}), 400
            
        if not volume:
            return jsonify({"error": "Missing required field: volume"}), 400

        # --- Handle flexible tp/sl key names ---
        tp = data.get('tp') or data.get('take_profit')
        sl = data.get('sl') or data.get('stop_loss')

        # Convert tp/sl to float if provided
        if tp:
            try:
                tp = float(tp)
            except ValueError:
                return jsonify({"error": "Invalid take_profit/tp value"}), 400
                
        if sl:
            try:
                sl = float(sl)
            except ValueError:
                return jsonify({"error": "Invalid stop_loss/sl value"}), 400

        # Convert volume to float
        try:
            volume = float(volume)
        except ValueError:
            return jsonify({"error": "Invalid volume value"}), 400

        # --- Market Orders ---
        if action in ['BUY', 'SELL', 'LONG', 'SHORT']:
            trade_action = 'BUY' if action in ['BUY', 'LONG'] else 'SELL'
            
            # Create signal dictionary for MT5Handler
            signal = {
                "symbol": symbol,
                "action": trade_action,
                "volume": volume
            }
            
            # Add optional fields
            if tp:
                signal["take_profit"] = tp
            if sl:
                signal["stop_loss"] = sl

            result = mt5_handler.send_order(signal)

            if result:
                return jsonify({"status": "success", "message": "Market order placed"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to place market order"}), 500

        # --- Pending Orders (LIMIT and STOP) ---
        elif action in ['BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP']:
            price = data.get('price')

            if not price:
                return jsonify({"error": "Missing required field for pending order: price"}), 400
            
            try:
                price = float(price)
            except ValueError:
                return jsonify({"error": "Invalid price value"}), 400
            
            # Create signal dictionary for MT5Handler
            signal = {
                "symbol": symbol,
                "action": action,
                "volume": volume,
                "price": price
            }
            
            # Add optional fields
            if tp:
                signal["take_profit"] = tp
            if sl:
                signal["stop_loss"] = sl
            
            result = mt5_handler.send_order(signal)
            
            if result:
                return jsonify({"status": "success", "message": "Pending order placed"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to place pending order"}), 500
        
        # --- Close Order ---
        elif action == 'CLOSE':
            result = mt5_handler.close_positions(symbol)
            if result:
                return jsonify({"status": "success", "message": "Close order executed"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to close position"}), 500

        # --- Unknown Action ---
        else:
            error_msg = f"Unknown or unsupported action: '{data.get('action')}'"
            log_error(error_msg)
            return jsonify({"error": error_msg}), 400

    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        log_error(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET', 'HEAD'])
def health_check():
    """Health check endpoint to verify the server is running."""
    # Log health check request in ORANGE color
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    method = request.method
    log_health_check(f'{client_ip} - "{method} /health HTTP/1.1" 200')
    
    mt5_status = mt5_handler.connected if mt5_handler else False
    return jsonify({
        "status": "ok", 
        "mt5_connected": mt5_status
    }), 200

@app.route('/positions', methods=['GET'])
def get_positions():
    """Get current open positions."""
    if not mt5_handler or not mt5_handler.connected:
        return jsonify({"error": "MT5 not connected"}), 500
    
    try:
        import MetaTrader5 as mt5
        positions = mt5.positions_get()
        
        if positions is None:
            return jsonify({"positions": []}), 200
        
        position_list = []
        for pos in positions:
            position_list.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": pos.volume,
                "profit": pos.profit,
                "open_price": pos.price_open
            })
        
        return jsonify({"positions": position_list}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get positions: {e}"}), 500

# Custom request logging with colors
@app.before_request
def log_request_info():
    """Log all incoming requests"""
    if request.endpoint != 'health_check':  # Don't double log health checks
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        logger.info(f'{client_ip} - "{request.method} {request.path} HTTP/1.1"')