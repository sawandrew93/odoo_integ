#!/bin/bash
# Ubuntu setup script for AI middleware

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Setup complete! To run:"
echo "source venv/bin/activate"
echo "python run.py"