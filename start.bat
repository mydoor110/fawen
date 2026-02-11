@echo off
REM 公文文件号管理系统启动脚本 (Windows)

echo === 公文文件号管理系统启动脚本 ===
echo.

echo 1. 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python 3，请先安装 Python 3.11+
    pause
    exit /b 1
)

echo 2. 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo 虚拟环境创建成功
) else (
    echo 虚拟环境已存在
)

echo 3. 激活虚拟环境...
call venv\Scripts\activate.bat

echo 4. 安装依赖...
pip install -r requirements.txt

echo 5. 检查配置文件...
if not exist "config.yaml" (
    echo 错误: 未找到 config.yaml 文件
    pause
    exit /b 1
)

echo 6. 检查数据库配置...
findstr /C:"postgresql://fawen:fawen@localhost:5432/fawen" config.yaml >nul
if not errorlevel 1 (
    echo 警告: 使用默认数据库配置，请根据实际情况修改 config.yaml
)

echo 7. 创建存储目录...
if not exist "storage\documents" mkdir storage\documents
if not exist "storage\destroyed" mkdir storage\destroyed

echo.
echo === 启动完成 ===
echo.
echo 使用以下命令启动服务:
echo   venv\Scripts\activate.bat  # 激活虚拟环境
echo   uvicorn app.main:app --reload  # 启动服务
echo.
echo API 文档地址:
echo   Swagger UI: http://localhost:8000/docs
echo   ReDoc: http://localhost:8000/redoc
echo.
pause
