#!/usr/bin/env python3
"""
TradingView to MetaTrader 5 Bridge
Main entry point for the application
"""

import logging
import sys
import os
from threading import Thread
import time
import subprocess
import requests

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import Config
from app.server import app, initialize_mt5

# Configure logging with UTF-8 encoding to prevent Unicode errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Set encoding for console output to prevent Unicode errors
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='ignore')

logger = logging.getLogger(__name__)

def setup_ngrok(auth_token, port):
    """Setup and run Ngrok tunnel"""
    try:
        # Set auth token
        subprocess.run(['ngrok', 'config', 'add-authtoken', auth_token], check=True)
        
        # Start tunnel
        logger.info(f"NGROK_SETUP: Starting tunnel on port {port}")
        process = subprocess.Popen(['ngrok', 'http', str(port), '--log=stdout'], 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for tunnel to be ready
        time.sleep(5)
        
        # Get tunnel URL
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            if response.status_code == 200:
                tunnels = response.json().get('tunnels', [])
                if tunnels:
                    tunnel_url = tunnels[0]['public_url']
                    webhook_url = f"{tunnel_url}/trade"
                    
                    # Save webhook URL to file
                    with open('webhook_url.txt', 'w', encoding='utf-8') as f:
                        f.write(webhook_url)
                    
                    logger.info(f"NGROK_SUCCESS: Tunnel active at {tunnel_url}")
                    logger.info(f"WEBHOOK_URL: {webhook_url}")
                    logger.info(f"WEBHOOK_SAVED: URL saved to webhook_url.txt")
                    
                    print("\n" + "="*60)
                    print(f"WEBHOOK URL FOR TRADINGVIEW:")
                    print(f"{webhook_url}")
                    print("="*60 + "\n")
                    
        except Exception as e:
            logger.warning(f"NGROK_WARNING: Could not get tunnel URL - {e}")
            logger.info("NGROK_INFO: Check dashboard at http://localhost:4040")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"NGROK_ERROR: Failed to setup Ngrok - {e}")
    except FileNotFoundError:
        logger.error("NGROK_ERROR: Ngrok not found. Please install Ngrok and add it to PATH")
    except Exception as e:
        logger.error(f"NGROK_ERROR: Unexpected error - {e}")

def run_server():
    """Run the Flask server"""
    try:
        config = Config()
        
        # Validate configuration
        all_errors = config.validate()
        fatal_errors = []
        email_warnings = []
        email_related_keys = ["SENDER_EMAIL", "SENDER_PASSWORD", "RECEIVER_EMAIL"]

        if all_errors:
            for error in all_errors:
                # Check if the error message is for an email setting
                if any(key in error for key in email_related_keys):
                    email_warnings.append(error)
                else:
                    fatal_errors.append(error)

        # If email settings are missing, show a warning but continue
        if email_warnings:
            logger.warning("CONFIG_WARNING: Email configuration incomplete. Email alerts disabled.")

        # If there are other critical errors, stop the application
        if fatal_errors:
            logger.error("CONFIG_ERROR: Fatal configuration errors found:")
            for error in fatal_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("SERVER_STARTUP: Starting TradingView to MT5 Bridge...")
        logger.info("CONFIG_INFO: Configuration loaded successfully")
        
        # Initialize MT5 connection
        logger.info("MT5_INIT: Initializing MT5 connection...")
        if not initialize_mt5():
            logger.error("MT5_ERROR: Failed to initialize MT5 connection")
            return False
        
        logger.info("MT5_SUCCESS: MT5 connection established")
        
        # Start Flask server
        logger.info(f"SERVER_START: Starting Flask server on {config.SERVER_HOST}:{config.SERVER_PORT}")
        app.run(
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.DEBUG,
            threaded=True
        )
        
        return True
        
    except Exception as e:
        logger.error(f"SERVER_ERROR: Error running server - {e}")
        return False

def run_with_ngrok():
    """Run server with Ngrok tunnel"""
    try:
        config = Config()
        
        # Start Ngrok in a separate thread
        logger.info("NGROK_INIT: Setting up Ngrok tunnel...")
        ngrok_thread = Thread(target=setup_ngrok, args=(config.NGROK_AUTH_TOKEN, config.SERVER_PORT))
        ngrok_thread.daemon = True
        ngrok_thread.start()
        
        # Wait a bit for Ngrok to start
        time.sleep(3)
        
        # Start the main server
        return run_server()
        
    except Exception as e:
        logger.error(f"NGROK_ERROR: Error running with Ngrok - {e}")
        return False

if __name__ == "__main__":
    try:
        # Check if user wants to run with Ngrok
        if len(sys.argv) > 1 and sys.argv[1] == "--no-ngrok":
            logger.info("STARTUP: Running without Ngrok tunnel")
            success = run_server()
        else:
            logger.info("STARTUP: Running with Ngrok tunnel")
            success = run_with_ngrok()
        
        if not success:
            logger.error("STARTUP_ERROR: Application failed to start")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("SHUTDOWN: Application stopped by user")
    except Exception as e:
        logger.error(f"STARTUP_ERROR: Unexpected error - {e}")
        sys.exit(1)