#!/bin/bash
# Run this from the portfolio-tracker/ root directory

echo "🚀 Starting Portfolio Tracker..."

# Start backend
cd backend
pip install -r requirements.txt -q
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "✅ Backend running at http://localhost:8000 (PID: $BACKEND_PID)"

# Start frontend
cd ../frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!
echo "✅ Frontend running at http://localhost:3000 (PID: $FRONTEND_PID)"

echo ""
echo "📊 Open http://localhost:3000 in your browser"
echo "📚 API docs at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and clean up on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
