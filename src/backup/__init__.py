import os
import shutil
import tarfile
from datetime import datetime, timedelta
from src.models import Backup, db
import logging

class BackupManager:
    def __init__(self, config):
        self.storage_path = config['backup']['storage_path']
        self.retention_days = config['backup']['retention_days']
        self.compression = config['backup']['compression']
        
        os.makedirs(self.storage_path, exist_ok=True)
    
    def create_backup(self, backup_id):
        backup = Backup.query.get(backup_id)
        if not backup:
            return False
            
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{backup.name}_{timestamp}"
            backup_path = os.path.join(self.storage_path, backup_name)
            
            if os.path.isdir(backup.source):
                if self.compression:
                    self._create_compressed_backup(backup.source, backup_path)
                else:
                    shutil.copytree(backup.source, backup_path)
            else:
                if self.compression:
                    self._create_compressed_backup(backup.source, backup_path)
                else:
                    shutil.copy2(backup.source, backup_path)
            
            # 更新备份状态
            backup.last_backup = datetime.utcnow()
            backup.status = 'success'
            db.session.commit()
            
            # 清理旧备份
            self.cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logging.error(f"Backup failed: {str(e)}")
            backup.status = 'failed'
            db.session.commit()
            return False
    
    def _create_compressed_backup(self, source, dest):
        with tarfile.open(f"{dest}.tar.gz", "w:gz") as tar:
            tar.add(source, arcname=os.path.basename(source))
    
    def cleanup_old_backups(self):
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        old_backups = Backup.query.filter(Backup.created_at < cutoff_date).all()
        
        for backup in old_backups:
            try:
                backup_path = os.path.join(self.storage_path, backup.name)
                if os.path.exists(backup_path):
                    if os.path.isdir(backup_path):
                        shutil.rmtree(backup_path)
                    else:
                        os.remove(backup_path)
            except Exception as e:
                logging.error(f"Failed to cleanup backup {backup.name}: {str(e)}") 