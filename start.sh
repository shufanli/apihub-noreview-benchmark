#!/bin/bash
set -e

export FRONTEND_URL=${FRONTEND_URL:-"https://teamocode.teamolab.com/apihubnoreview"}
export DATABASE_PATH=${DATABASE_PATH:-"/app/data/apihub.db"}

# Start backend on port 8000
cd /app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Start frontend on port 8080 (main port)
cd /app/frontend
PORT=8080 npx next start -p 8080 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
