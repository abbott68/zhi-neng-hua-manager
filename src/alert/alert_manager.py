import smtplib
from email.message import EmailMessage
from typing import Dict, List

class AlertManager:
    def __init__(self, smtp_config: Dict[str, str]):
        self.smtp_config = smtp_config
        
    def send_alert(self, alert_type: str, message: str, recipients: List[str]) -> None:
        """发送告警邮件"""
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = f'系统告警: {alert_type}'
        msg['From'] = self.smtp_config['sender']
        msg['To'] = ', '.join(recipients)
        
        with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            server.send_message(msg) 