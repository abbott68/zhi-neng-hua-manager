#!/bin/bash

# 激活虚拟环境（如果有的话）
# source venv/bin/activate

# 设置环境变量
export FLASK_APP=src.web.app
export FLASK_ENV=development

# 检查数据库连接
echo "检查数据库连接..."
mysql -h 127.0.0.1 -P 3306 -u dev -p'dev@123' ops_platform -e "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "数据库连接失败，请检查配置"
    exit 1
fi

# 运行应用
echo "启动应用..."
python3 -m flask run --host=0.0.0.0 --port=5000 