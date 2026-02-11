#!/bin/bash

set -e

echo "=== 公文文件号管理系统启动脚本 ==="

echo ""
echo "1. 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python 3，请先安装 Python 3.11+"
    exit 1
fi

echo "2. 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境创建成功"
else
    echo "虚拟环境已存在"
fi

echo "3. 激活虚拟环境..."
source venv/bin/activate

echo "4. 安装后端依赖..."
pip install -r requirements.txt

echo "5. 检查配置文件..."
if [ ! -f "config.yaml" ]; then
    echo "错误: 未找到 config.yaml 文件"
    exit 1
fi

echo "6. 创建存储目录..."
mkdir -p storage/documents
mkdir -p storage/destroyed
mkdir -p logs

echo "7. 安装前端依赖..."
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi
cd frontend
npm install
cd ..

echo ""
echo "=== 环境准备完成 ==="
echo ""
echo "8. 启动服务..."
echo ""
echo "  默认管理员账号: admin / admin123"
echo "  后端地址:  http://localhost:5000"
echo "  API 文档:  http://localhost:5000/docs"
echo "  前端地址:  http://localhost:8000"
echo ""

# 用 trap 确保退出时杀掉所有子进程
cleanup() {
    echo ""
    echo "正在停止所有服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "所有服务已停止"
}
trap cleanup EXIT INT TERM

# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload &
BACKEND_PID=$!

# 启动前端
cd frontend
npx vite --host 0.0.0.0 --port 8000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "=== 后端 (PID: $BACKEND_PID) 和前端 (PID: $FRONTEND_PID) 已启动 ==="
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待任一子进程退出
wait -n $BACKEND_PID $FRONTEND_PID
