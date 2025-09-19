"""
Run only the Ngrok part of the application.
Useful when you want to run the Flask server separately.
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.ngrok_setup import setup_ngrok

if __name__ == "__main__":
    print("Starting Ngrok only...")
    print("This will create a tunnel to your locally running Flask server.")
    print("Make sure your Flask server is running on the port specified in your .env file.")
    print("Press Ctrl+C to stop Ngrok.\n")
    
    setup_ngrok()