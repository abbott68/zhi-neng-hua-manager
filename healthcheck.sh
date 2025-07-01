#!/bin/bash
set -e

# 设置默认值
HEALTH_CHECK_URL=${HEALTH_CHECK_URL:-http://localhost:5000/health}
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_INTERVAL=${RETRY_INTERVAL:-5}

# 检查应用健康状态
check_health() {
  echo "检查应用健康状态: $HEALTH_CHECK_URL"
  
  for i in $(seq 1 $MAX_RETRIES); do
    response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_CHECK_URL || echo "000")
    
    if [ "$response" = "200" ]; then
      echo "应用健康状态正常 (HTTP 200)"
      return 0
    else
      echo "尝试 $i/$MAX_RETRIES: 应用健康状态异常 (HTTP $response)"
      
      if [ $i -lt $MAX_RETRIES ]; then
        echo "等待 $RETRY_INTERVAL 秒后重试..."
        sleep $RETRY_INTERVAL
      fi
    fi
  done
  
  echo "应用健康检查失败，请检查日志获取更多信息"
  return 1
}

# 主函数
main() {
  check_health
  exit $?
}

# 运行主函数
main