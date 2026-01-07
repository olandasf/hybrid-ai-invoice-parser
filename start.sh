#!/bin/bash
# Start the Flask application (Linux/macOS)
# Usage: ./start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Hybrid AI Invoice Parser..."

# Check if virtual environment exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Using system Python."
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found!"
    exit 1
fi

# Start Flask application
echo "Starting Flask server..."
echo "Application will be available at: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
