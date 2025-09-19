import sys
import os
import time
import logging
from pyngrok import ngrok, conf

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.config import NGROK_AUTH_TOKEN, FLASK_PORT
from app.utils import setup_logging, save_webhook_url

# Set up logging
logger = setup_logging('ngrok')

def setup_ngrok():
    """Setup and start Ngrok tunnel"""
    # Check if token is set
    if not NGROK_AUTH_TOKEN or NGROK_AUTH_TOKEN == "your-ngrok-auth-token":
        logger.error("Ngrok auth token not set. Please set NGROK_AUTH_TOKEN in your .env file.")
        logger.error("You can get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken")
        return
    
    # Set Ngrok auth token
    conf.get_default().auth_token = NGROK_AUTH_TOKEN
    
    # Create tunnel
    logger.info(f"Starting Ngrok tunnel to port {FLASK_PORT}")
    try:
        # Kill any existing ngrok processes
        try:
            ngrok.kill()
            logger.info("Killed existing Ngrok processes")
        except:
            logger.info("No existing Ngrok processes found")
        
        # Create HTTP tunnel
        logger.info("Connecting to Ngrok...")
        http_tunnel = ngrok.connect(FLASK_PORT, "http")
        public_url = http_tunnel.public_url
        webhook_url = f"{public_url}/trade"
        
        logger.info(f"Ngrok tunnel established: {public_url}")
        logger.info(f"Use this URL as your TradingView webhook: {webhook_url}")
        
        # Save the URL to a file for reference
        save_webhook_url(webhook_url)
        
        # Print to console for visibility
        print("\n" + "="*50)
        print(f"WEBHOOK URL: {webhook_url}")
        print("Use this URL in your TradingView alert settings")
        print("="*50 + "\n")
        
        # Keep the tunnel open
        try:
            while True:
                time.sleep(30)  # Check more frequently
                tunnels = ngrok.get_tunnels()
                if not tunnels:
                    logger.warning("Ngrok tunnel closed unexpectedly, restarting...")
                    http_tunnel = ngrok.connect(FLASK_PORT, "http")
                    webhook_url = f"{http_tunnel.public_url}/trade"
                    logger.info(f"Ngrok tunnel re-established: {webhook_url}")
                    save_webhook_url(webhook_url)
                    
                    # Print to console for visibility
                    print("\n" + "="*50)
                    print(f"NEW WEBHOOK URL: {webhook_url}")
                    print("Use this URL in your TradingView alert settings")
                    print("="*50 + "\n")
        except KeyboardInterrupt:
            raise
                
    except KeyboardInterrupt:
        logger.info("Ngrok tunnel stopped by user")
    except Exception as e:
        logger.error(f"Error with Ngrok tunnel: {str(e)}", exc_info=True)
    finally:
        # Try to gracefully close ngrok
        try:
            ngrok.kill()
            logger.info("Ngrok tunnel closed")
        except:
            logger.warning("Failed to kill Ngrok process")


if __name__ == "__main__":
    setup_ngrok()