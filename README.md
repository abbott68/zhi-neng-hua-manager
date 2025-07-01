# 智能化管理系统

智能化管理系统是一个全面的系统监控和管理平台，用于监控服务器性能、分析系统指标、发送告警通知，并提供可视化仪表板。系统采用Python Flask框架开发，支持多种数据库后端，提供Web界面和API接口，适用于中小型企业的IT基础设施监控和管理。

## 功能特点

- **系统监控**：实时监控CPU、内存、磁盘使用率和网络流量
- **智能分析**：使用机器学习算法分析系统指标趋势并预测未来状态
- **告警管理**：当系统指标超过阈值时自动发送告警邮件
- **数据可视化**：生成直观的仪表板展示系统性能数据
- **资产管理**：管理和监控网络中的服务器和设备
- **备份管理**：管理系统备份任务和记录
- **数据导出**：支持将监控数据导出为CSV或JSON格式
- **多数据库支持**：支持SQLite、MySQL、MongoDB等多种数据库

## 系统架构

系统由以下主要模块组成：

- **监控模块** (`monitor/system_monitor.py`)：收集系统指标（CPU、内存、磁盘、网络）和进程信息，支持阈值检查
- **分析模块** (`analysis/metrics_analyzer.py`)：分析指标趋势和预测未来状态，使用机器学习算法进行预测
- **告警模块** (`alert/alert_manager.py`)：处理告警规则和发送邮件通知
- **可视化模块** (`visualization/data_visualizer.py`)：生成数据仪表板，支持多种图表类型
- **导出模块** (`export/data_exporter.py`)：将监控数据导出为CSV或JSON格式
- **网络检查模块** (`utils/network_checker.py`)：检查网络连接和服务状态
- **数据库模块** (`database/db_manager.py`)：管理多种数据库（SQLite、MySQL、MongoDB）的连接和操作
- **Web界面** (`web/`)：基于Flask的用户交互界面，包含认证、路由和API
- **数据模型** (`models.py`)：定义系统的数据结构和关系

## 安装指南

### 前提条件

- Python 3.6+
- MySQL数据库（可选，默认使用SQLite）
- MongoDB（可选）
- Redis（可选）
- 必要的系统工具（如nmap）
- SMTP服务器（用于发送告警邮件）

### Docker部署

系统支持使用Docker和Docker Compose进行快速部署，详细说明请参考[Docker部署指南](README.docker.md)。

#### 一键部署

使用提供的部署脚本可以快速完成部署：

```bash
# 赋予脚本执行权限
chmod +x deploy-docker.sh

# 执行部署脚本
./deploy-docker.sh
```

#### 手动部署

```bash
# 复制配置文件
cp config.example.yml config.yml
cp .env.example .env

# 编辑配置文件
vim config.yml
vim .env

# 使用Docker Compose启动所有服务
docker-compose up -d
```

### 安装步骤

1. 克隆代码库

```bash
git clone <repository-url>
cd zhi-neng-hua-manager
```

2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖

```bash
pip install -e .
# 或者
pip install -r requirements.txt
```

4. 配置数据库和应用

编辑`config.yml`文件，设置数据库连接信息、SMTP服务器信息和其他配置项：

```yaml
# 数据库配置
database:
  url: mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
  track_modifications: false

# 应用配置
app:
  secret_key: 你的密钥
  debug: true

# 日志配置
logging:
  level: INFO
  file: logs/app.log
  max_size: 10240
  backup_count: 10

# 定时任务配置
scheduler:
  metrics_interval: 300  # 5分钟
```

5. 初始化数据库

```bash
bash init_db.sh
```

6. 启动应用

```bash
bash run.sh
```

应用将在 http://localhost:5000 上运行。

## 使用指南

### Web界面

启动应用后，访问`http://localhost:5000`进入Web界面。默认管理员账号：

- 用户名：admin
- 密码：admin

### 主要功能

- **仪表板**：查看系统性能概览，包括CPU、内存、磁盘使用率的实时和历史数据
- **监控**：查看详细的系统指标和进程信息，支持按时间范围筛选
- **资产**：管理和监控网络设备，支持添加、编辑、删除资产，以及导入/导出资产列表
- **备份**：管理系统备份任务，查看备份历史和状态
- **日志**：查看系统日志，支持按级别、类型、日期和搜索内容进行过滤
- **任务**：管理定时任务，支持启用/禁用任务

### API接口

系统提供了RESTful API接口，可用于与其他系统集成：

- **GET /api/metrics/summary**：获取CPU、内存、磁盘的实时摘要指标
- **GET /api/metrics/realtime**：获取详细的实时系统指标
- **POST /api/assets**：创建新资产
- **PUT /api/assets/<asset_id>**：更新指定资产
- **DELETE /api/assets/<asset_id>**：删除指定资产
- **GET /api/assets/export**：导出所有资产到CSV文件
- **POST /api/assets/import**：从CSV文件导入资产

### 告警配置

系统支持基于阈值的告警机制。当系统指标超过预设阈值时，系统会自动发送告警邮件。默认阈值设置：

- CPU使用率：80%
- 内存使用率：85%
- 磁盘使用率：90%
- 网络流量：1GB

可以在`config.yml`文件中自定义这些阈值。

## 开发指南

### 项目结构

```
├── config.yml          # 配置文件
├── data/               # 数据目录
├── init_db.sh          # 数据库初始化脚本
├── logs/               # 日志目录
├── monitor.db          # SQLite数据库文件
├── requirements.txt    # 依赖列表
├── run.sh              # 启动脚本
├── setup.py            # 安装配置
├── src/                # 源代码
│   ├── __init__.py     # 包初始化文件
│   ├── alert/          # 告警模块
│   │   └── alert_manager.py  # 告警管理器
│   ├── analysis/       # 分析模块
│   │   └── metrics_analyzer.py  # 指标分析器
│   ├── assets/         # 资产管理
│   │   └── __init__.py
│   ├── auth/           # 认证模块
│   │   └── __init__.py
│   ├── backup/         # 备份模块
│   │   └── __init__.py
│   ├── cli.py          # 命令行接口
│   ├── database/       # 数据库模块
│   │   └── db_manager.py  # 数据库管理器
│   ├── export/         # 数据导出
│   │   └── data_exporter.py  # 数据导出器
│   ├── main.py         # 主程序
│   ├── models.py       # 数据模型
│   ├── models/         # 模型目录
│   │   └── __init__.py
│   ├── monitor/        # 监控模块
│   │   └── system_monitor.py  # 系统监控器
│   ├── scheduler/      # 调度器
│   │   └── __init__.py
│   ├── utils/          # 工具函数
│   │   └── network_checker.py  # 网络检查器
│   ├── visualization/  # 可视化模块
│   │   └── data_visualizer.py  # 数据可视化器
│   └── web/            # Web界面
│       ├── __init__.py
│       ├── app.py      # Flask应用
│       ├── auth.py     # 认证路由
│       ├── forms.py    # 表单定义
│       ├── routes.py   # 主要路由
│       ├── run.py      # Web启动脚本
│       └── templates/  # HTML模板
└── tests/              # 测试代码
    ├── test_basic.py   # 基本测试
    └── test_monitor.py # 监控测试
```

### 核心模块说明

- **SystemMonitor**：负责收集系统指标，包括CPU、内存、磁盘、网络和进程信息
- **MetricsAnalyzer**：负责分析指标趋势和预测未来状态，使用线性回归模型
- **DataVisualizer**：负责从数据库获取历史数据并生成可视化图表
- **DataExporter**：负责将监控数据导出为CSV或JSON格式
- **DatabaseManager**：负责管理数据库连接和操作，支持SQLite、MySQL和MongoDB
- **AlertManager**：负责发送告警邮件
- **NetworkChecker**：负责检查网络连接和服务状态

### 添加新功能

1. 在相应模块中添加功能代码
2. 更新数据模型（如需要）
3. 添加Web界面路由和模板
4. 更新配置文件（如需要）
5. 编写测试用例

### 扩展指南

#### 添加新的监控指标

1. 在`SystemMonitor`类中添加新的指标收集方法
2. 在`models.py`中更新`MonitorData`模型（如需要）
3. 在`DataVisualizer`中添加新的可视化方法
4. 在Web界面中添加新的展示组件

#### 添加新的数据库支持

1. 在`DatabaseManager`类中添加新的数据库连接方法
2. 更新配置文件以支持新的数据库参数
3. 测试新数据库的连接和操作

## 测试

### 运行所有测试

```bash
python -m unittest discover tests
```

### 运行特定测试

```bash
python -m unittest tests.test_basic
python -m unittest tests.test_monitor
```

### 测试覆盖范围

- **test_basic.py**：测试`SystemMonitor`的基本功能，包括收集CPU、内存和磁盘使用率等系统指标
- **test_monitor.py**：测试`SystemMonitor`的核心功能，包括收集系统指标、检查阈值、数据可视化、指标趋势分析和数据导出

### 添加新测试

1. 在`tests`目录下创建新的测试文件
2. 导入需要测试的模块和`unittest`
3. 创建继承自`unittest.TestCase`的测试类
4. 实现测试方法（方法名必须以`test_`开头）
5. 在测试方法中使用断言方法验证结果

## 许可证

[MIT License](LICENSE)

## 贡献指南

欢迎提交问题报告和功能请求。如果您想贡献代码，请遵循以下步骤：

1. Fork项目
2. 创建功能分支（`git checkout -b feature/your-feature-name`）
3. 提交更改（`git commit -am 'Add some feature'`）
4. 推送到分支（`git push origin feature/your-feature-name`）
5. 创建Pull Request

### 代码规范

- 遵循PEP 8编码规范
- 为所有新功能编写测试
- 保持代码简洁清晰
- 添加适当的注释和文档

### 问题报告

提交问题报告时，请包含以下信息：

- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 系统环境（操作系统、Python版本等）

## 联系方式

如有任何问题或建议，请通过以下方式联系我们：

- 电子邮件：example@example.com
- 项目Issues：[GitHub Issues](https://github.com/yourusername/zhi-neng-hua-manager/issues)

## 致谢

感谢所有为本项目做出贡献的开发者和用户。