#!/bin/bash

# 创建数据库（如果不存在）
mysql -h 127.0.0.1 -P 3306 -u dev -p'dev@123' <<EOF
CREATE DATABASE IF NOT EXISTS ops_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

# 设置环境变量
export FLASK_APP=src.web.app
export FLASK_ENV=development

# 初始化数据库
echo "初始化数据库..."
flask db init

# 创建迁移
echo "创建数据库迁移..."
flask db migrate -m "Initial migration"

# 应用迁移
echo "应用数据库迁移..."
flask db upgrade 