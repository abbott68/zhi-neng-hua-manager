FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    nmap \
    gcc \
    python3-dev \
    default-libmysqlclient-dev \
    default-mysql-client \
    redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/

# 设置脚本权限
RUN chmod +x /app/docker-entrypoint.sh \
    && chmod +x /app/healthcheck.sh

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV FLASK_APP=src.web.app
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 5000

# 设置入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 启动命令
CMD ["bash", "run.sh"]