# Docker 部署指南

本文档提供了使用 Docker 和 Docker Compose 部署智能化管理系统的详细说明。

## 目录

- [前提条件](#前提条件)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [数据持久化](#数据持久化)
- [环境变量](#环境变量)
- [常见问题](#常见问题)

## 前提条件

在开始之前，请确保您的系统已安装以下软件：

- Docker (20.10.0+)
- Docker Compose (2.0.0+)

可以通过以下命令检查版本：

```bash
docker --version
docker-compose --version
```

## 快速开始

1. 克隆代码库：

```bash
git clone https://your-repository-url/zhi-neng-hua-manager.git
cd zhi-neng-hua-manager
```

2. 配置环境：

复制示例配置文件并根据需要修改：

```bash
# 复制并配置应用配置文件
cp config.example.yml config.yml
# 编辑 config.yml 文件，根据需要修改配置

# 复制并配置环境变量文件
cp .env.example .env
# 编辑 .env 文件，根据需要修改环境变量
```

3. 启动服务：

```bash
docker-compose up -d
```

4. 访问应用：

打开浏览器，访问 http://localhost:5000

5. 查看日志：

```bash
docker-compose logs -f app
```

## 配置说明

### 服务组件

本系统使用 Docker Compose 配置了以下服务：

- **app**: 主应用服务，运行 Flask 应用和系统监控
- **mysql**: MySQL 数据库服务
- **redis**: Redis 缓存服务

### 健康检查

系统配置了自动健康检查机制，每 30 秒检查一次应用状态。健康检查会验证：

- Web 应用是否正常运行
- 数据库连接是否正常
- 系统资源使用情况

您可以通过以下命令查看容器健康状态：

```bash
docker-compose ps
```

或者查看详细的健康检查日志：

```bash
docker inspect --format='{{json .State.Health}}' zhi-neng-hua-manager | jq
```

您也可以直接访问健康检查 API 端点：

```bash
curl http://localhost:5000/health
```

### 配置文件

系统使用 `config.yml` 作为主要配置文件，该文件会被挂载到容器内。您可以根据需要修改此文件中的配置项。

## 数据持久化

系统使用 Docker 卷来持久化数据：

- **mysql-data**: 存储 MySQL 数据
- **redis-data**: 存储 Redis 数据
- **./data**: 应用数据目录，挂载到容器的 `/app/data`
- **./logs**: 日志目录，挂载到容器的 `/app/logs`

这些卷确保即使容器被删除，数据也不会丢失。

## 环境变量

您可以通过环境变量自定义系统行为。以下是可用的环境变量：

### 应用配置

- `FLASK_APP`: Flask 应用入口点 (默认: src.web.app)
- `FLASK_ENV`: 运行环境 (development/production, 默认: production)
- `FLASK_HOST`: 监听地址 (默认: 0.0.0.0)
- `FLASK_PORT`: 监听端口 (默认: 5000)

### 数据库配置

- `DB_HOST`: 数据库主机 (默认: mysql)
- `DB_PORT`: 数据库端口 (默认: 3306)
- `DB_USER`: 数据库用户名 (默认: dev)
- `DB_PASS`: 数据库密码 (默认: dev@123)
- `DB_NAME`: 数据库名称 (默认: ops_platform)

### Redis 配置

- `REDIS_HOST`: Redis 主机 (默认: redis)
- `REDIS_PORT`: Redis 端口 (默认: 6379)

您可以在 `docker-compose.yml` 文件的 `environment` 部分修改这些变量。

## 常见问题

### 数据库连接失败

如果遇到数据库连接问题，请检查：

1. MySQL 服务是否正常运行：

```bash
docker-compose ps mysql
```

2. 数据库连接配置是否正确：

```bash
docker-compose exec app env | grep DB_
```

### 应用无法启动

检查应用日志：

```bash
docker-compose logs app
```

### 如何备份数据

备份 MySQL 数据：

```bash
docker-compose exec mysql sh -c 'exec mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" ops_platform' > backup.sql
```

### 如何升级系统

1. 拉取最新代码：

```bash
git pull
```

2. 重新构建并启动容器：

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

---

如有更多问题，请参考项目主 README 文件或联系系统管理员。