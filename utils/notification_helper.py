import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.template_manager import TemplateManager
from utils.logger import log_info, log_error

load_dotenv()


class NotificationManager:
    """Manage stakeholder notifications via email with rate limiting and batching."""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_address = os.getenv('GMAIL_USER')
        self.password = os.getenv('GMAIL_APP_PASSWORD')
        
        self.template_manager = TemplateManager()

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        self.notification_logs_file = os.path.join(project_root, 'data', 'notification_logs.json')  
        self.stakeholder_contacts_file = os.path.join(project_root, 'data', 'stakeholder_contacts.json')
        
        # Event to stakeholder mapping
        self.event_stakeholder_map = {
            'rfq_sent': ['717822i216@kce.ac.in'],
            'quote_received': ['717822i216@kce.ac.in'],
            'quote_parsed': ['717822i216@kce.ac.in'],
            'po_created': ['717822i216@kce.ac.in'],
            'po_approved': ['717822i216@kce.ac.in'],
            'po_rejected': ['717822i216@kce.ac.in'],
            'delivery_expected': ['717822i216@kce.ac.in'],
            'delivery_delayed': ['717822i216@kce.ac.in'],
            'budget_exceeded': ['717822i216@kce.ac.in'],
            'supplier_update_received': ['717822i216@kce.ac.in'],
            'verification_complete': ['717822i216@kce.ac.in'],
            'mismatch_email_to_supplier': ['supplier_email'],
            'final_report': ['717822i216@kce.ac.in']
        }
        
        # Rate limiting: 5 minutes between notifications
        self.last_notification_time = {}
        self.rate_limit_seconds = 300
        
        # Batching: 10 minute window for grouping similar events
        self.batch_cache = {}
        self.batch_window_seconds = 600
        
        if not self.email_address or not self.password:
            raise ValueError("Gmail credentials not found in .env file")
        
        log_info("Notification Manager initialized", "NotificationManager")
    
    
    def _load_notification_logs(self):
        """Load notification history."""
        try:
            if os.path.exists(self.notification_logs_file):
                with open(self.notification_logs_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            return {}
        except json.JSONDecodeError:
            log_error("Notification logs file is corrupted, creating new", "NotificationManager")
            return {}
        except Exception as e:
            log_error(f"Failed to load notification logs: {e}", "NotificationManager")
            return {}
    
    
    def _save_notification_log(self, notification_id, log_data):
        """Save notification log."""
        try:
            logs = self._load_notification_logs()
            logs[notification_id] = log_data
            
            os.makedirs(os.path.dirname(self.notification_logs_file), exist_ok=True)
            with open(self.notification_logs_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            log_info(f"Saved notification log: {notification_id}", "NotificationManager")
        except Exception as e:
            log_error(f"Failed to save notification log: {e}", "NotificationManager")
    
    
    def _check_rate_limit(self, event_type):
        """Check if event is rate limited."""
        now = datetime.now()
        
        if event_type in self.last_notification_time:
            time_diff = (now - self.last_notification_time[event_type]).total_seconds()
            
            # High priority events bypass rate limit
            high_priority = ['budget_exceeded', 'delivery_delayed', 'po_approved', 
                           'verification_complete', 'final_report']
            
            if event_type not in high_priority and time_diff < self.rate_limit_seconds:
                return False
        
        return True
    
    
    def _update_rate_limit(self, event_type):
        """Update rate limit timestamp."""
        self.last_notification_time[event_type] = datetime.now()
    
    
    def _check_batch_window(self, event_type):
        """Check if similar events should be batched."""
        now = datetime.now()
        
        # Only batch quote_received events
        if event_type != 'quote_received':
            return None
        
        if event_type in self.batch_cache:
            cache_entry = self.batch_cache[event_type]
            time_diff = (now - cache_entry['first_time']).total_seconds()
            
            if time_diff < self.batch_window_seconds:
                return cache_entry
        
        return None
    
    
    def _add_to_batch(self, event_type, event_data):
        """Add event to batch cache."""
        now = datetime.now()
        
        if event_type not in self.batch_cache:
            self.batch_cache[event_type] = {
                'first_time': now,
                'events': []
            }
        
        self.batch_cache[event_type]['events'].append(event_data)
    
    
    def _send_batched_notification(self, event_type):
        """Send batched notification."""
        if event_type not in self.batch_cache:
            return
        
        batch = self.batch_cache[event_type]
        events = batch['events']
        
        if len(events) == 0:
            return
        
        # Create batched notification
        item_name = events[0].get('item_name', 'Multiple Items')
        
        event_data = {
            'item_name': item_name,
            'quote_count': len(events),
            'quotes': events
        }
        
        # Send notification
        recipients = self.event_stakeholder_map.get(event_type, [])
        subject = f"{len(events)} New Quotes Received - {item_name}"
        body = self.template_manager.render('quote_received_batch', event_data)
        
        self._send_email(recipients, subject, body, event_type)
        
        # Clear batch
        del self.batch_cache[event_type]
    
    
    def _send_email(self, recipients, subject, body, event_type, attachment_path=None):
        """Send email notification with optional attachment."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=os.path.basename(attachment_path))
                    msg.attach(pdf_attachment)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.password)
            
            server.send_message(msg)
            server.quit()
            
            log_info(f"Email sent to {len(recipients)} recipients", "NotificationManager")
            
            # Log notification
            notification_id = f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            log_data = {
                'notification_id': notification_id,
                'event_type': event_type,
                'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'recipients': recipients,
                'subject': subject,
                'status': 'sent',
                'error_message': None
            }
            self._save_notification_log(notification_id, log_data)
            
            return True
            
        except Exception as e:
            log_error(f"Email send failed: {e}", "NotificationManager")
            
            # Log failure
            notification_id = f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            log_data = {
                'notification_id': notification_id,
                'event_type': event_type,
                'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'recipients': recipients,
                'subject': subject,
                'status': 'failed',
                'error_message': str(e)
            }
            self._save_notification_log(notification_id, log_data)
            
            return False
    
    
    def send_event_notification(self, event_type, event_data):
        """Send notification for an event with rate limiting and batching support."""
        # Check rate limit
        if not self._check_rate_limit(event_type):
            log_info(f"Event {event_type} rate limited", "NotificationManager")
            return {
                'status': 'rate_limited',
                'message': 'Notification rate limited'
            }
        
        # Check batching for quote_received
        if event_type == 'quote_received':
            batch = self._check_batch_window(event_type)
            if batch:
                self._add_to_batch(event_type, event_data)
                log_info(f"Added to batch, count: {len(batch['events']) + 1}", "NotificationManager")
                return {
                    'status': 'batched',
                    'message': 'Added to batch window'
                }
            else:
                self._add_to_batch(event_type, event_data)
        
        # Get recipients (handle dynamic supplier email for Agent 9)
        recipients = self.event_stakeholder_map.get(event_type, [])
        
        if event_type == 'mismatch_email_to_supplier':
            # Use supplier email from event_data
            recipients = [event_data.get('supplier_email', '717822i216@kce.ac.in')]
        
        if not recipients:
            log_error(f"No recipients for event: {event_type}", "NotificationManager")
            return {
                'status': 'failed',
                'error': 'No recipients configured'
            }
        
        # Generate email content
        subject = self.template_manager.get_subject(event_type, event_data)
        body = self.template_manager.render(event_type, event_data)
        
        # Check for PDF attachment (for final_report)
        attachment_path = event_data.get('report_path') if event_type == 'final_report' else None
        
        # Send email
        success = self._send_email(recipients, subject, body, event_type, attachment_path)
        
        if success:
            self._update_rate_limit(event_type)
            return {
                'status': 'success',
                'recipients': recipients,
                'event_type': event_type
            }
        else:
            return {
                'status': 'failed',
                'error': 'Email send failed'
            }


if __name__ == "__main__":
    print("="*60)
    print("Testing Notification Manager (Updated)")
    print("="*60)
    
    manager = NotificationManager()
    
    print("\nTest 1: Send verification complete notification")
    print("-"*60)
    result = manager.send_event_notification('verification_complete', {
        'po_number': 'PO-ITM001-20240115',
        'item_name': 'M8 Screws',
        'match_result': 'PASS',
        'mismatch_count': 0,
        'mismatches': [],
        'verified_at': '2024-01-15 14:30:00'
    })
    print(f"Status: {result['status']}")
    
    print("\nTest 2: Send RFQ notification")
    print("-"*60)
    result = manager.send_event_notification('rfq_sent', {
        'item_name': 'M8 Screws',
        'quantity': 2536,
        'suppliers_contacted': 5,
        'emails_sent': 5
    })
    print(f"Status: {result['status']}")
    
    print("\nTest 3: Send quote received notification")
    print("-"*60)
    result = manager.send_event_notification('quote_received', {
        'item_name': 'M8 Screws',
        'supplier_name': 'NextGen Components',
        'unit_price': 12.50,
        'delivery_days': 10,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    print(f"Status: {result['status']}")
    