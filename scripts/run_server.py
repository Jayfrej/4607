"""
Run only the Flask server part of the application.
Useful when you want to run Ngrok separately or use another tunnel method.
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mt5_handler import MT5Handler
from app.server import run_server
from app.utils import setup_logging

# Set up logging
logger = setup_logging('flask_server')

if __name__ == "__main__":
    try:
        print("Starting Flask server only...")
        print("If you need to expose this server to the internet, run Ngrok separately.")
        print("Press Ctrl+C to stop the server.\n")
        
        # Create MT5 handler
        mt5_handler = MT5Handler()
        
        # Run the server
        run_server(mt5_handler)
        
    except KeyboardInterrupt:
        logger.info("Server terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        logger.info("Shutting down server")
        try:
            if 'mt5_handler' in locals():
                mt5_handler.close_session()
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")