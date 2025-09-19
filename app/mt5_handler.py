import MetaTrader5 as mt5
import logging
from difflib import get_close_matches
import re

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

logger = logging.getLogger(__name__)


class MT5Handler:
    def __init__(self, account, password, server, path):
        self.account = account
        self.password = password
        self.server = server
        self.path = path
        self.connected = False
        self.symbol_cache = {}  # Cache to speed up repeated lookups
        self.broker_symbols = []  # Cache broker symbols list

    # ---------------- Colored Logging Methods ----------------
    def log_success(self, message):
        """Log success messages in GREEN"""
        colored_message = f"{Colors.GREEN}{message}{Colors.RESET}"
        logger.info(colored_message)
        
    def log_health_check(self, message):
        """Log health check messages in ORANGE"""
        colored_message = f"{Colors.ORANGE}{message}{Colors.RESET}"
        logger.info(colored_message)
        
    def log_error(self, message):
        """Log error messages in RED"""
        colored_message = f"{Colors.RED}{message}{Colors.RESET}"
        logger.error(colored_message)
        
    def log_warning(self, message):
        """Log warning messages in YELLOW"""
        colored_message = f"{Colors.YELLOW}{message}{Colors.RESET}"
        logger.warning(colored_message)

    # ---------------- MT5 Connection ----------------
    def connect(self):
        """Connect to MT5 using provided credentials"""
        try:
            if not mt5.initialize(self.path):
                self.log_error(f"Failed to initialize MT5: {mt5.last_error()}")
                return False

            if not mt5.login(self.account, self.password, self.server):
                self.log_error(f"Failed to login to MT5: {mt5.last_error()}")
                return False

            self.connected = True
            # Cache broker symbols on connection
            self._cache_broker_symbols()
            self.log_success("SUCCESS: Connected to MT5")
            return True

        except Exception as e:
            self.log_error(f"Error connecting to MT5: {e}")
            return False

    def disconnect(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        self.connected = False
        self.broker_symbols = []
        logger.info("DISCONNECTED: MT5 connection closed")

    def _cache_broker_symbols(self):
        """Cache all available broker symbols"""
        try:
            symbols = mt5.symbols_get()
            self.broker_symbols = [s.name for s in symbols] if symbols else []
            logger.info(f"SYMBOL_CACHE: Cached {len(self.broker_symbols)} broker symbols")
        except Exception as e:
            self.log_error(f"SYMBOL_CACHE_ERROR: Failed to cache symbols - {e}")
            self.broker_symbols = []

    # ---------------- Enhanced Symbol Mapping ----------------
    def map_symbol(self, symbol: str) -> str:
        """
        Advanced auto-mapping of TradingView symbol to broker's MT5 symbol.
        Uses multiple strategies to find the best match.
        """
        if not symbol:
            self.log_error("SYMBOL_MAP_ERROR: Empty symbol provided")
            return symbol

        symbol = symbol.strip()
        logger.info(f"SYMBOL_MAPPING: '{symbol}'")
        
        # Check cache first
        if symbol in self.symbol_cache:
            cached_symbol = self.symbol_cache[symbol]
            logger.info(f"RESULT: Using cached '{symbol}' -> '{cached_symbol}'")
            return cached_symbol

        # Refresh broker symbols if empty
        if not self.broker_symbols:
            self._cache_broker_symbols()

        if not self.broker_symbols:
            self.log_warning("SYMBOL_MAP_WARNING: No broker symbols available")
            self.symbol_cache[symbol] = symbol
            return symbol

        # Strategy 1: Exact match
        if symbol in self.broker_symbols:
            self.symbol_cache[symbol] = symbol
            logger.info(f"RESULT: Exact match '{symbol}' -> '{symbol}'")
            return symbol

        # Strategy 2: Case-insensitive match
        for s in self.broker_symbols:
            if s.upper() == symbol.upper():
                self.symbol_cache[symbol] = s
                logger.info(f"RESULT: Case match '{symbol}' -> '{s}'")
                return s

        # Strategy 3: Normalized match (remove common suffixes/prefixes)
        normalized_symbol = self.normalize(symbol)
        for s in self.broker_symbols:
            if self.normalize(s) == normalized_symbol:
                self.symbol_cache[symbol] = s
                logger.info(f"RESULT: Normalized match '{symbol}' -> '{s}' (normalized: '{normalized_symbol}')")
                return s

        # Strategy 4: Startswith match (handles suffixes like XAUUSD -> XAUUSDm)
        for s in self.broker_symbols:
            if s.upper().startswith(symbol.upper()):
                self.symbol_cache[symbol] = s
                logger.info(f"RESULT: Prefix match '{symbol}' -> '{s}'")
                return s

        # Strategy 5: Contains match (e.g. BTCUSD -> BTCUSD.pro)
        for s in self.broker_symbols:
            if symbol.upper() in s.upper():
                self.symbol_cache[symbol] = s
                logger.info(f"RESULT: Contains match '{symbol}' -> '{s}'")
                return s

        # Strategy 6: Fuzzy matching (similarity-based)
        fuzzy_match = self.fuzzy_map(symbol, self.broker_symbols)
        if fuzzy_match:
            self.symbol_cache[symbol] = fuzzy_match
            logger.info(f"RESULT: Fuzzy match '{symbol}' -> '{fuzzy_match}'")
            return fuzzy_match

        # Strategy 7: Description-based matching
        desc_match = self.description_match(symbol)
        if desc_match:
            self.symbol_cache[symbol] = desc_match
            logger.info(f"RESULT: Description match '{symbol}' -> '{desc_match}'")
            return desc_match

        # Strategy 8: Common symbol transformations
        transformed_match = self.transform_symbol(symbol)
        if transformed_match and transformed_match in self.broker_symbols:
            self.symbol_cache[symbol] = transformed_match
            logger.info(f"RESULT: Transform match '{symbol}' -> '{transformed_match}'")
            return transformed_match

        # Strategy 9: Fallback - use original symbol
        self.log_warning(f"RESULT: No mapping found for '{symbol}', using as-is")
        self.symbol_cache[symbol] = symbol
        return symbol

    def normalize(self, s: str) -> str:
        """Remove common suffixes/prefixes and normalize the symbol"""
        if not s:
            return s
            
        # Convert to uppercase
        normalized = s.upper()
        
        # Remove common suffixes and prefixes
        suffixes_to_remove = ['M', 'PRO', '.PRO', '_PRO', '.M', '_M', '.', '-', '_']
        prefixes_to_remove = ['MT5_', 'FX_']
        
        # Remove suffixes
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        # Remove prefixes
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Remove any remaining special characters
        normalized = re.sub(r'[^A-Z0-9]', '', normalized)
        
        return normalized

    def fuzzy_map(self, symbol: str, broker_symbols: list) -> str:
        """Use fuzzy matching to find the closest symbol"""
        try:
            # Get close matches with different cutoff values
            matches = get_close_matches(
                symbol.upper(), 
                [s.upper() for s in broker_symbols], 
                n=3, 
                cutoff=0.6
            )
            
            if matches:
                # Find the actual symbol name from broker_symbols
                for match in matches:
                    for s in broker_symbols:
                        if s.upper() == match:
                            return s
            return None
        except Exception as e:
            self.log_error(f"FUZZY_MATCH_ERROR: {e}")
            return None

    def description_match(self, symbol: str) -> str:
        """Try to match symbol using MT5 symbol descriptions"""
        try:
            for s in self.broker_symbols:
                info = mt5.symbol_info(s)
                if info and hasattr(info, 'description') and info.description:
                    desc = info.description.upper()
                    if symbol.upper() in desc or desc in symbol.upper():
                        return s
            return None
        except Exception as e:
            self.log_error(f"DESCRIPTION_MATCH_ERROR: {e}")
            return None

    def transform_symbol(self, symbol: str) -> str:
        """Apply common symbol transformations"""
        transformations = {
            # Common forex pairs
            'EURUSD': ['EUR/USD', 'EURUSD', 'EURUSDm'],
            'GBPUSD': ['GBP/USD', 'GBPUSD', 'GBPUSDm'],
            'USDJPY': ['USD/JPY', 'USDJPY', 'USDJPYm'],
            'AUDUSD': ['AUD/USD', 'AUDUSD', 'AUDUSDm'],
            'USDCAD': ['USD/CAD', 'USDCAD', 'USDCADm'],
            'USDCHF': ['USD/CHF', 'USDCHF', 'USDCHFm'],
            'NZDUSD': ['NZD/USD', 'NZDUSD', 'NZDUSDm'],
            
            # Precious metals
            'XAUUSD': ['GOLD', 'XAU/USD', 'XAUUSDm'],
            'XAGUSD': ['SILVER', 'XAG/USD', 'XAGUSDm'],
            
            # Crypto
            'BTCUSD': ['Bitcoin', 'BTC/USD', 'BTCUSDm'],
            'ETHUSD': ['Ethereum', 'ETH/USD', 'ETHUSDm'],
        }
        
        # Check if we have predefined transformations
        if symbol.upper() in transformations:
            for variant in transformations[symbol.upper()]:
                if variant in self.broker_symbols:
                    return variant
        
        # Try common variations
        variations = [
            f"{symbol}m",
            f"{symbol}.pro",
            f"{symbol}_pro",
            f"{symbol}.m",
            f"{symbol}_m",
            symbol.replace('/', ''),
            symbol.replace('-', ''),
            symbol.replace('_', ''),
        ]
        
        for variant in variations:
            if variant in self.broker_symbols:
                return variant
        
        return None

    def get_symbol_info(self, symbol: str) -> dict:
        """Get detailed information about a mapped symbol"""
        mapped_symbol = self.map_symbol(symbol)
        
        try:
            info = mt5.symbol_info(mapped_symbol)
            if info:
                return {
                    'name': info.name,
                    'description': getattr(info, 'description', 'N/A'),
                    'currency_base': getattr(info, 'currency_base', 'N/A'),
                    'currency_profit': getattr(info, 'currency_profit', 'N/A'),
                    'point': getattr(info, 'point', 0),
                    'digits': getattr(info, 'digits', 0),
                    'trade_contract_size': getattr(info, 'trade_contract_size', 0),
                    'minimum_volume': getattr(info, 'volume_min', 0),
                    'maximum_volume': getattr(info, 'volume_max', 0),
                    'volume_step': getattr(info, 'volume_step', 0),
                }
            return None
        except Exception as e:
            self.log_error(f"SYMBOL_INFO_ERROR: {e}")
            return None

    # ---------------- Trading with Colored Output ----------------
    def send_order(self, signal: dict):
        """Send order to MT5 based on TradingView signal"""
        if not self.connected:
            self.log_error("TRADE_ERROR: MT5 is not connected")
            return False

        try:
            logger.info("NEW WEBHOOK RECEIVED")
            logger.info("=" * 60)
            
            # Log the incoming webhook data
            logger.info(f"{signal}")
            
            action = signal.get("action")
            original_symbol = signal.get("symbol")
            volume = float(signal.get("volume", 0.1))
            price = float(signal.get("price", 0.0))
            sl = float(signal.get("stop_loss", 0.0))
            tp = float(signal.get("take_profit", 0.0))

            # Use enhanced symbol mapping
            mapped_symbol = self.map_symbol(original_symbol)
            
            # Verify symbol exists and is tradeable
            if not self.verify_symbol(mapped_symbol):
                self.log_error(f"SYMBOL_ERROR: Symbol '{mapped_symbol}' is not tradeable")
                return False

            # Convert action to MT5 order type
            order_type = None
            if action == "BUY" or action == "Long":
                order_type = mt5.ORDER_TYPE_BUY
            elif action == "SELL" or action == "Short":
                order_type = mt5.ORDER_TYPE_SELL
            elif action == "BUY_LIMIT":
                order_type = mt5.ORDER_TYPE_BUY_LIMIT
            elif action == "SELL_LIMIT":
                order_type = mt5.ORDER_TYPE_SELL_LIMIT
            elif action == "BUY_STOP":
                order_type = mt5.ORDER_TYPE_BUY_STOP
            elif action == "SELL_STOP":
                order_type = mt5.ORDER_TYPE_SELL_STOP
            else:
                self.log_error(f"UNSUPPORTED ACTION: {action}")
                return False

            # Get current market price if not provided
            if price <= 0:
                tick = mt5.symbol_info_tick(mapped_symbol)
                if tick is None:
                    self.log_error(f"PRICE ERROR: Cannot get price for {mapped_symbol}")
                    return False
                
                if order_type == mt5.ORDER_TYPE_BUY:
                    price = tick.ask
                else:
                    price = tick.bid

            # Build order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL
                if order_type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL]
                else mt5.TRADE_ACTION_PENDING,
                "symbol": mapped_symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 123456,
                "comment": "TradingView Auto-Signal",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            logger.info("SENDING ORDER TO MT5...")
            
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.log_error(f"ORDER FAILED (Error: {result.retcode}, {result.comment})")
                return False

            # SUCCESS message in GREEN color
            self.log_success(f"SUCCESS (Ticket: {result.order})")
            logger.info("=" * 60)
            
            return True

        except Exception as e:
            self.log_error(f"EXCEPTION ERROR: {e}")
            logger.info("=" * 60)
            return False

    def verify_symbol(self, symbol: str) -> bool:
        """Verify that a symbol exists and is tradeable"""
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return False
            
            # Check if symbol is visible in Market Watch
            if not info.visible:
                # Try to make it visible
                if not mt5.symbol_select(symbol, True):
                    self.log_warning(f"SYMBOL_WARNING: Could not add {symbol} to Market Watch")
                    return False
            
            return True
        except Exception as e:
            self.log_error(f"SYMBOL_VERIFY_ERROR: {e}")
            return False

    # ---------------- Utility ----------------
    def close_positions(self, symbol=None):
        """Close all open positions (or for one symbol)"""
        try:
            # Map the symbol if provided
            if symbol:
                symbol = self.map_symbol(symbol)
                
            logger.info(f"CLOSE_REQUEST: Closing positions for symbol '{symbol}'" if symbol else "CLOSE_REQUEST: Closing all positions")
            
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                logger.info("CLOSE_INFO: No positions to close")
                return True

            logger.info(f"CLOSE_INFO: Found {len(positions)} positions to close")

            for pos in positions:
                order_type = (
                    mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                )
                price = (
                    mt5.symbol_info_tick(pos.symbol).bid
                    if order_type == mt5.ORDER_TYPE_SELL
                    else mt5.symbol_info_tick(pos.symbol).ask
                )

                logger.info(f"CLOSE_SETUP: Position {pos.ticket} - Symbol={pos.symbol}, Volume={pos.volume}, Type={'BUY' if pos.type == 0 else 'SELL'}")

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": order_type,
                    "position": pos.ticket,
                    "price": price,
                    "deviation": 20,
                    "magic": 123456,
                    "comment": "Auto-close position",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }

                result = mt5.order_send(request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.log_error(f"CLOSE_ERROR: Failed to close position {pos.ticket} - {result.comment}")
                else:
                    self.log_success(f"CLOSE_SUCCESS: Closed position {pos.ticket}")

            return True

        except Exception as e:
            self.log_error(f"CLOSE_ERROR: Exception occurred - {e}")
            return False

    def clear_symbol_cache(self):
        """Clear the symbol mapping cache (useful for debugging)"""
        self.symbol_cache.clear()
        logger.info("SYMBOL_CACHE: Cache cleared")

    def get_cache_stats(self) -> dict:
        """Get statistics about the symbol cache"""
        return {
            'cached_mappings': len(self.symbol_cache),
            'broker_symbols_count': len(self.broker_symbols),
            'cache_contents': dict(self.symbol_cache)
        }