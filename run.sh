#!/bin/bash
set -e

# 设置默认值
FLASK_HOST=${FLASK_HOST:-0.0.0.0}
FLASK_PORT=${FLASK_PORT:-5000}
FLASK_ENV=${FLASK_ENV:-development}

# 设置环境变量
export FLASK_APP=src.web.app
export FLASK_ENV=$FLASK_ENV

# 数据库连接信息（从环境变量获取或使用默认值）
DB_HOST=${DB_HOST:-mysql}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-dev}
DB_PASS=${DB_PASS:-dev@123}
DB_NAME=${DB_NAME:-ops_platform}

# 检查数据库连接
echo "检查数据库连接..."
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p"$DB_PASS" $DB_NAME -e "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "数据库连接失败，请检查配置"
    exit 1
fi

# 启动监控服务（后台运行）
echo "启动系统监控服务..."
python -m src.main &

# 运行应用
echo "启动Web应用服务..."
if [ "$FLASK_ENV" = "development" ]; then
    echo "以开发模式运行..."
    python3 -m flask run --host=$FLASK_HOST --port=$FLASK_PORT
else
    echo "以生产模式运行..."
    if command -v gunicorn &> /dev/null; then
        gunicorn --bind $FLASK_HOST:$FLASK_PORT --workers=4 --timeout=120 "src.web.app:create_app()"
    else
        echo "警告: gunicorn未安装，使用Flask开发服务器运行生产环境"
        python3 -m flask run --host=$FLASK_HOST --port=$FLASK_PORT
    fi
fi