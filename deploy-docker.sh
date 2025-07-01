#!/bin/bash
set -e

# 颜色定义
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

echo -e "${GREEN}智能化管理系统 - Docker 部署脚本${NC}"
echo "====================================="

# 检查 Docker 和 Docker Compose 是否已安装
check_dependencies() {
  echo -e "${YELLOW}检查依赖...${NC}"
  
  if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
  fi
  
  if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
  fi
  
  echo -e "${GREEN}依赖检查通过!${NC}"
}

# 准备配置文件
prepare_config() {
  echo -e "${YELLOW}准备配置文件...${NC}"
  
  # 检查并创建配置文件
  if [ ! -f "config.yml" ]; then
    if [ -f "config.example.yml" ]; then
      echo "创建 config.yml 配置文件..."
      cp config.example.yml config.yml
      echo -e "${GREEN}已创建 config.yml 文件，请根据需要修改配置${NC}"
    else
      echo -e "${RED}错误: 未找到 config.example.yml 文件${NC}"
      exit 1
    fi
  else
    echo "config.yml 文件已存在"
  fi
  
  # 检查并创建环境变量文件
  if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
      echo "创建 .env 环境变量文件..."
      cp .env.example .env
      echo -e "${GREEN}已创建 .env 文件，请根据需要修改环境变量${NC}"
    else
      echo -e "${RED}错误: 未找到 .env.example 文件${NC}"
      exit 1
    fi
  else
    echo ".env 文件已存在"
  fi
  
  # 创建数据目录
  if [ ! -d "data" ]; then
    echo "创建数据目录..."
    mkdir -p data
  fi
  
  # 创建日志目录
  if [ ! -d "logs" ]; then
    echo "创建日志目录..."
    mkdir -p logs
  fi
  
  echo -e "${GREEN}配置文件准备完成!${NC}"
}

# 构建并启动容器
build_and_start() {
  echo -e "${YELLOW}构建并启动容器...${NC}"
  
  # 构建镜像
  echo "构建 Docker 镜像..."
  docker-compose build
  
  # 启动容器
  echo "启动容器..."
  docker-compose up -d
  
  echo -e "${GREEN}容器已成功启动!${NC}"
}

# 显示状态
show_status() {
  echo -e "${YELLOW}检查服务状态...${NC}"
  
  # 等待服务启动
  echo "等待服务启动..."
  sleep 10
  
  # 显示容器状态
  docker-compose ps
  
  # 检查应用健康状态
  echo "\n检查应用健康状态..."
  curl -s http://localhost:5000/health | grep -q '"status":"healthy"'
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}应用健康状态: 正常${NC}"
  else
    echo -e "${RED}应用健康状态: 异常${NC}"
    echo "请检查日志获取更多信息: docker-compose logs app"
  fi
  
  echo -e "\n${GREEN}部署完成!${NC}"
  echo "应用访问地址: http://localhost:5000"
  echo "默认管理员账号: admin / admin"
}

# 主函数
main() {
  check_dependencies
  prepare_config
  build_and_start
  show_status
}

# 运行主函数
main