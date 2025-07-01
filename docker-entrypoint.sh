#!/bin/bash
set -e

# 等待MySQL服务准备就绪
wait_for_mysql() {
  echo "等待MySQL服务准备就绪..."
  until mysql -h mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &> /dev/null
  do
    echo "MySQL服务尚未准备就绪 - 等待..."
    sleep 2
  done
  echo "MySQL服务已准备就绪!"
}

# 等待Redis服务准备就绪
wait_for_redis() {
  echo "等待Redis服务准备就绪..."
  until redis-cli -h redis ping &> /dev/null
  do
    echo "Redis服务尚未准备就绪 - 等待..."
    sleep 2
  done
  echo "Redis服务已准备就绪!"
}

# 初始化数据库
initialize_database() {
  echo "初始化数据库..."
  flask db init || true
  flask db migrate -m "初始化数据库"
  flask db upgrade
  echo "数据库初始化完成!"
}

# 主函数
main() {
  # 如果依赖服务配置存在，则等待它们
  if [[ -n "$MYSQL_USER" && -n "$MYSQL_PASSWORD" ]]; then
    wait_for_mysql
  fi
  
  if [[ -n "$REDIS_HOST" ]]; then
    wait_for_redis
  fi
  
  # 初始化数据库
  initialize_database
  
  # 执行传入的命令
  exec "$@"
}

# 运行主函数
main "$@"