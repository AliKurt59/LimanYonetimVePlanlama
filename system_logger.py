# system_logger.py - Gelişmiş Loglama Sistemi

import logging
import json
import traceback
from datetime import datetime
from functools import wraps
import inspect
import os
from enum import Enum
from typing import Dict, Any, Optional

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SystemLogger:
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.setup_file_logging()
        
    def setup_file_logging(self):
        """Dosya tabanlı loglama kurulumu"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Ana log dosyası
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/system.log', encoding='utf-8'),
                logging.StreamHandler()  # Console'a da yazdır
            ]
        )
        
        # Farklı seviyeler için farklı dosyalar
        self.error_logger = logging.getLogger('ERROR')
        error_handler = logging.FileHandler(f'{log_dir}/errors.log', encoding='utf-8')
        error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.error_logger.addHandler(error_handler)
        
        self.audit_logger = logging.getLogger('AUDIT')
        audit_handler = logging.FileHandler(f'{log_dir}/audit.log', encoding='utf-8')
        audit_handler.setFormatter(logging.Formatter('%(asctime)s - AUDIT - %(message)s'))
        self.audit_logger.addHandler(audit_handler)
        
        self.performance_logger = logging.getLogger('PERFORMANCE')
        perf_handler = logging.FileHandler(f'{log_dir}/performance.log', encoding='utf-8')
        perf_handler.setFormatter(logging.Formatter('%(asctime)s - PERF - %(message)s'))
        self.performance_logger.addHandler(perf_handler)
    
    def log_audit(self, user_id, action, table_name=None, record_id=None, old_data=None, new_data=None, ip_address=None):
        """Audit log kaydı"""
        audit_data = {
            'user_id': user_id,
            'action': action,
            'table_name': table_name,
            'record_id': record_id,
            'old_data': old_data,
            'new_data': new_data,
            'ip_address': ip_address,
            'timestamp': datetime.now().isoformat()
        }
        
        # Dosyaya yaz
        self.audit_logger.info(json.dumps(audit_data, ensure_ascii=False))
        
        # Veritabanına yaz (eğer bağlantı varsa)
        if self.db and self.db.conn:
            try:
                query = """
                    INSERT INTO audit_logs (kullanici_id, aksiyon, tablo_adi, kayit_id, 
                                          eski_deger, yeni_deger, ip_adresi)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                self.db.execute_query(query, (
                    user_id, action, table_name, record_id,
                    json.dumps(old_data) if old_data else None,
                    json.dumps(new_data) if new_data else None,
                    ip_address
                ))
            except Exception as e:
                logging.error(f"Audit log veritabanına yazılamadı: {e}")
    
    def log_performance(self, operation, duration, details=None):
        """Performans log kaydı"""
        perf_data = {
            'operation': operation,
            'duration_ms': duration,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.performance_logger.info(json.dumps(perf_data))
        
        # Veritabanına performans metriği kaydet
        if self.db and self.db.conn:
            try:
                query = """
                    INSERT INTO performans_metrikleri (metrik_adi, deger, birim, kategori, ek_bilgi)
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.db.execute_query(query, (
                    operation, duration, 'ms', 'PERFORMANCE',
                    json.dumps(details) if details else None
                ))
            except Exception as e:
                logging.error(f"Performans metriği kaydedilemedi: {e}")
    
    def log_query_performance(self, query, execution_time, params=None, result_count=None):
        """SQL sorgu performansı logla"""
        # Önceki log_performance metodunu kullan
        self.log_performance(
            operation="SQL_QUERY",
            duration=execution_time,
            details={
                'query': query[:100] + '...' if len(query) > 100 else query,
                'params_count': len(params) if params else 0,
                'result_count': result_count
            }
        )
        
        # Yavaş sorgular için uyarı
        if execution_time > 1000:  # 1 saniyeden uzun
            self.warning(f"Yavaş sorgu tespit edildi: {execution_time:.2f}ms", "DATABASE")
    
    def info(self, message, module_name="", **kwargs):
        """Info level log"""
        logging.info(f"[{module_name}] {message}")
    
    def warning(self, message, module_name="", **kwargs):
        """Warning level log"""
        logging.warning(f"[{module_name}] {message}")
    
    def error(self, message, module_name="", **kwargs):
        """Error level log"""
        logging.error(f"[{module_name}] {message}")
    
    def debug(self, message, module_name="", **kwargs):
        """Debug level log"""
        logging.debug(f"[{module_name}] {message}")
    
    def log_error(self, error, context=None, user_id=None):
        """Hata log kaydı"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        self.error_logger.error(json.dumps(error_data, ensure_ascii=False))
        
        # Critical hatalar için bildirim oluştur
        if self.db and self.db.conn and isinstance(error, (ConnectionError, Exception)):
            self.create_notification(
                "Sistem Hatası",
                f"Kritik hata oluştu: {str(error)}",
                "ERROR",
                4  # Kritik öncelik
            )
    
    def create_notification(self, title, message, notification_type="INFO", priority=1, user_id=None, source=None, related_id=None):
        """Bildirim oluştur"""
        if self.db and self.db.conn:
            try:
                query = """
                    INSERT INTO bildirimler (baslik, mesaj, tip, oncelik, kullanici_id, kaynak, ilgili_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                self.db.execute_query(query, (
                    title, message, notification_type, priority, user_id, source, related_id
                ))
            except Exception as e:
                logging.error(f"Bildirim oluşturulamadı: {e}")

# Global logger instance
_system_logger = None

def get_logger(db_connection=None):
    """Global logger instance'ı al"""
    global _system_logger
    if _system_logger is None:
        _system_logger = SystemLogger(db_connection)
    elif db_connection and not _system_logger.db:
        _system_logger.db = db_connection
    return _system_logger

def log_execution_time(operation_name=None):
    """Fonksiyon yürütme süresini logla (decorator)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # milliseconds
                
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                logger = get_logger()
                logger.log_performance(op_name, duration, {
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'success': True
                })
                
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                logger = get_logger()
                logger.log_performance(op_name, duration, {
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'success': False,
                    'error': str(e)
                })
                logger.log_error(e, {'function': op_name})
                raise
                
        return wrapper
    return decorator

def log_audit_action(action, table_name=None, get_record_id=None):
    """Audit log için decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Fonksiyon çağrısından önce mevcut durumu al
            old_data = None
            record_id = None
            
            if get_record_id and callable(get_record_id):
                try:
                    record_id = get_record_id(*args, **kwargs)
                except:
                    pass
            
            try:
                result = func(*args, **kwargs)
                
                # Audit log kaydet
                logger = get_logger()
                logger.log_audit(
                    user_id="system",  # Bu, kullanıcı sistemi implementasyonunda güncellenecek
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    old_data=old_data,
                    new_data={"result": "success"}
                )
                
                return result
                
            except Exception as e:
                logger = get_logger()
                logger.log_audit(
                    user_id="system",
                    action=f"{action}_FAILED",
                    table_name=table_name,
                    record_id=record_id,
                    old_data=old_data,
                    new_data={"error": str(e)}
                )
                raise
                
        return wrapper
    return decorator

class DatabaseLogHandler:
    """Veritabanı işlemleri için özel log handler"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = get_logger(db_connection)
    
    def log_query(self, query, params=None, execution_time=None, result_count=None):
        """SQL sorgu logları"""
        query_data = {
            'query': query[:500] + '...' if len(query) > 500 else query,  # Uzun sorguları kısalt
            'params_count': len(params) if params else 0,
            'execution_time_ms': execution_time,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat()
        }
        
        logging.info(f"DB_QUERY: {json.dumps(query_data)}")
        
        # Yavaş sorgular için uyarı
        if execution_time and execution_time > 1000:  # 1 saniyeden uzun
            self.logger.create_notification(
                "Yavaş Sorgu Uyarısı",
                f"Sorgu {execution_time:.2f}ms sürdü",
                "WARNING",
                2
            )
    
    def log_connection_issue(self, error):
        """Veritabanı bağlantı sorunları"""
        self.logger.log_error(error, {"category": "database_connection"})
        self.logger.create_notification(
            "Veritabanı Bağlantı Sorunu",
            f"Veritabanı bağlantısında sorun: {str(error)}",
            "ERROR",
            4
        )

# Uygulama başlangıcında kullanılacak
def setup_logging(db_connection=None):
    """Sistem başlangıcında loglama kurulumu"""
    logger = get_logger(db_connection)
    
    # Uygulama başlangıç logu
    logger.log_audit(
        user_id="system",
        action="APPLICATION_START",
        new_data={"version": "2.1", "timestamp": datetime.now().isoformat()}
    )
    
    return logger

# Singleton Logger Factory
class LoggerFactory:
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerFactory, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_logger(cls, name=None, db_connection=None):
        if cls._logger is None:
            cls._logger = SystemLogger(db_connection)
        return cls._logger
    
    @classmethod
    def get_audit_trail(cls, db_connection, logger):
        # Basit audit trail implementasyonu
        return logger
    
    @classmethod
    def get_performance_logger(cls, db_connection, logger):
        # Basit performance logger implementasyonu
        return logger
    
    @classmethod
    def get_notification_manager(cls, db_connection, logger):
        # Basit notification manager implementasyonu
        return logger

# Global instance
logger_factory = LoggerFactory()

# Backward compatibility
def get_logger(db_connection=None):
    return logger_factory.get_logger(db_connection=db_connection)
