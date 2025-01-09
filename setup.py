from setuptools import setup, find_packages

setup(
    name='zhi-neng-hua-manager',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'flask-login',
        'flask-migrate',
        'pymysql',
        'python-nmap',
        'psutil',
        'apscheduler',
        'pandas',
        'plotly',
        'scikit-learn',
        'requests',
        'paramiko',
        'redis',
        'pymongo',
    ],
) 