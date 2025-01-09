import os
import sys
import yaml

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.web import create_app

# 确保数据目录存在
os.makedirs('data', exist_ok=True)

# 加载配置
config_path = os.getenv('CONFIG_PATH', os.path.join(project_root, 'config.yml'))
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = {}

app = create_app(config)

if __name__ == '__main__':
    app.run(debug=True) 