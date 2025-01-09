import socket
import subprocess
import platform
import time
from typing import Dict, List, Optional
import nmap
import paramiko
import requests
import mysql.connector
import redis
import pymongo
from ftplib import FTP
import ssl

class NetworkChecker:
    def __init__(self):
        """初始化网络检查器"""
        try:
            self.nm = nmap.PortScanner()
        except nmap.PortScannerError:
            raise RuntimeError("nmap 未安装或无法访问。请确保已安装 nmap 并有适当的权限。")

    @staticmethod
    def check_ping(host: str) -> Dict:
        """检查主机是否可以 ping 通"""
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', host]
        
        try:
            start_time = time.time()
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            return {
                'status': 'online' if result.returncode == 0 else 'offline',
                'response_time': round(response_time, 2)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def scan_ports(host: str, ports: List[int] = None) -> Dict:
        """扫描主机开放的端口"""
        nm = nmap.PortScanner()
        ports_str = ','.join(map(str, ports)) if ports else '22-25,80,443,3306,5432,6379,8080'
        
        try:
            nm.scan(host, ports_str)
            if host in nm.all_hosts():
                open_ports = []
                for port in nm[host]['tcp']:
                    if nm[host]['tcp'][port]['state'] == 'open':
                        service = nm[host]['tcp'][port]
                        open_ports.append({
                            'port': port,
                            'service': service['name'],
                            'version': service.get('version', ''),
                            'product': service.get('product', '')
                        })
                return {
                    'status': 'success',
                    'open_ports': open_ports
                }
            return {
                'status': 'error',
                'message': 'Host not found'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def check_ssh(host: str, port: int = 22, timeout: int = 5) -> Dict:
        """检查 SSH 服务"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            start_time = time.time()
            client.connect(host, port=port, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            transport = client.get_transport()
            server_version = transport.remote_version
            
            client.close()
            return {
                'status': 'online',
                'service': 'ssh',
                'version': server_version,
                'response_time': round(response_time, 2)
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_http(url: str, timeout: int = 5) -> Dict:
        """检查 HTTP/HTTPS 服务"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout, verify=False)
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'online',
                'code': response.status_code,
                'server': response.headers.get('Server', 'Unknown'),
                'response_time': round(response_time, 2)
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_tcp_port(host: str, port: int, timeout: int = 5) -> Dict:
        """检查 TCP 端口是否开放"""
        try:
            start_time = time.time()
            with socket.create_connection((host, port), timeout=timeout) as sock:
                response_time = (time.time() - start_time) * 1000
                return {
                    'status': 'online',
                    'port': port,
                    'response_time': round(response_time, 2)
                }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_mysql(host: str, port: int = 3306, timeout: int = 5) -> Dict:
        """检查 MySQL 服务"""
        try:
            start_time = time.time()
            conn = mysql.connector.connect(
                host=host,
                port=port,
                connect_timeout=timeout
            )
            response_time = (time.time() - start_time) * 1000
            
            version = conn.get_server_info()
            conn.close()
            
            return {
                'status': 'online',
                'service': 'mysql',
                'version': version,
                'response_time': round(response_time, 2)
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_redis(host: str, port: int = 6379, timeout: int = 5) -> Dict:
        """检查 Redis 服务"""
        try:
            start_time = time.time()
            r = redis.Redis(host=host, port=port, socket_timeout=timeout)
            info = r.info()
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'online',
                'service': 'redis',
                'version': info['redis_version'],
                'response_time': round(response_time, 2)
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_mongodb(host: str, port: int = 27017, timeout: int = 5) -> Dict:
        """检查 MongoDB 服务"""
        try:
            start_time = time.time()
            client = pymongo.MongoClient(f"mongodb://{host}:{port}/", 
                                       serverSelectionTimeoutMS=timeout*1000)
            server_info = client.server_info()
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'online',
                'service': 'mongodb',
                'version': server_info['version'],
                'response_time': round(response_time, 2)
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_ftp(host: str, port: int = 21, timeout: int = 5) -> Dict:
        """检查 FTP 服务"""
        try:
            start_time = time.time()
            ftp = FTP()
            ftp.connect(host=host, port=port, timeout=timeout)
            welcome = ftp.getwelcome()
            response_time = (time.time() - start_time) * 1000
            ftp.quit()
            
            return {
                'status': 'online',
                'service': 'ftp',
                'banner': welcome,
                'response_time': round(response_time, 2)
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    @staticmethod
    def check_https_cert(host: str, port: int = 443, timeout: int = 5) -> Dict:
        """检查 HTTPS 证书信息"""
        try:
            start_time = time.time()
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    response_time = (time.time() - start_time) * 1000
                    
                    return {
                        'status': 'online',
                        'service': 'https',
                        'cert_expires': cert['notAfter'],
                        'cert_subject': dict(x[0] for x in cert['subject']),
                        'cert_issuer': dict(x[0] for x in cert['issuer']),
                        'response_time': round(response_time, 2)
                    }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

    def scan_all_services(self, host: str, timeout: int = 5) -> Dict:
        """扫描所有支持的服务"""
        results = {
            'ping': self.check_ping(host),
            'ports': self.scan_ports(host)
        }
        
        # 如果主机在线，检查各种服务
        if results['ping']['status'] == 'online':
            service_checks = {
                'ssh': (self.check_ssh, 22),
                'http': (self.check_http, 80),
                'https': (self.check_https_cert, 443),
                'mysql': (self.check_mysql, 3306),
                'redis': (self.check_redis, 6379),
                'mongodb': (self.check_mongodb, 27017),
                'ftp': (self.check_ftp, 21)
            }
            
            results['services'] = {}
            for service_name, (check_func, default_port) in service_checks.items():
                try:
                    if service_name in ['http', 'https']:
                        url = f"{service_name}://{host}:{default_port}"
                        results['services'][service_name] = check_func(url, timeout=timeout)
                    else:
                        results['services'][service_name] = check_func(host, default_port, timeout)
                except Exception as e:
                    results['services'][service_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
        
        return results 