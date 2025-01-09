import platform
import psutil
import logging
from src.models import Asset, db

class AssetManager:
    def __init__(self):
        self.has_nmap = False
        try:
            import nmap
            self.nm = nmap.PortScanner()
            self.has_nmap = True
        except (ImportError, nmap.PortScannerError):
            logging.warning("nmap not available. Network discovery features will be limited.")
    
    def discover_network_assets(self, network):
        """发现网络中的资产"""
        if not self.has_nmap:
            logging.warning("Network discovery requires nmap to be installed")
            return []
            
        try:
            self.nm.scan(hosts=network, arguments='-sn')
            discovered = []
            
            for host in self.nm.all_hosts():
                if self.nm[host].state() == 'up':
                    asset = Asset(
                        name=host,
                        type='server',
                        ip_address=host,
                        status='active',
                        specs={
                            'hostname': self.nm[host].hostname(),
                            'mac': self.nm[host].get('addresses', {}).get('mac', '')
                        }
                    )
                    discovered.append(asset)
            
            return discovered
            
        except Exception as e:
            logging.error(f"Asset discovery failed: {str(e)}")
            return []
    
    def collect_system_info(self):
        """收集本地系统信息"""
        try:
            info = {
                'platform': platform.platform(),
                'processor': platform.processor(),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'free': psutil.disk_usage('/').free
                },
                'network': {
                    'interfaces': psutil.net_if_addrs()
                }
            }
            return info
        except Exception as e:
            logging.error(f"System info collection failed: {str(e)}")
            return {} 