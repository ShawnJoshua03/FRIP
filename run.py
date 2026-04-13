#!/usr/bin/env python3
"""
Run FRIP locally for development.
Usage: python run.py
"""
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n  FRIP is running at http://localhost:{port}\n")
    app.run(debug=True, host="0.0.0.0", port=port)