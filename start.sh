#!/bin/bash
# 短剧创作工具 - 一键启动脚本
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "=========================================="
echo "  短剧创作工具"
echo "=========================================="
echo ""

# Kill existing processes on ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend
echo "[1/2] 启动后端服务 (FastAPI)..."
cd "$BACKEND_DIR"
source venv/bin/activate
python run.py &
BACKEND_PID=$!
sleep 3

# Check backend
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  ✓ 后端启动成功 (http://localhost:8000)"
else
    echo "  ✗ 后端启动失败"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend
echo "[2/2] 启动前端服务 (Vite)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
sleep 2

echo ""
echo "=========================================="
echo "  启动完成!"
echo ""
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "=========================================="

# Wait for interrupt
trap "echo ''; echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
