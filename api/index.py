import os
import sys

# Add parent directory to path so imports work correctly inside Vercel lambdas
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import app
