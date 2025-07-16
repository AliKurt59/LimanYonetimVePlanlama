#!/usr/bin/env python3
# performance_optimizer.py - Performans optimizasyonu ve sistem izleme

import time
import threading
import psutil
import gc
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
import json
import os

@dataclass
class PerformanceMetrics:
    """Performans metrikleri"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    query_count: int
    query_avg_time: float
    active_connections: int
    cache_hit_rate: float
    ui_response_time: float
    
class QueryProfiler:
    """SQL sorgu profiler"""
    
    def __init__(self, max_queries=1000):
        self.queries = deque(maxlen=max_queries)
        self.query_stats = defaultdict(lambda: {'count': 0, 'total_time': 0.0, 'avg_time': 0.0})
        self.active_queries = {}
        self.lock = threading.Lock()
    
    def start_query(self, query_id: str, query: str):
        """Sorgu başlangıcını kaydet"""
        with self.lock:
            self.active_queries[query_id] = {
                'query': query,
                'start_time': time.time(),
                'thread_id': threading.current_thread().ident
            }
    
    def end_query(self, query_id: str):
        """Sorgu bitişini kaydet"""
        with self.lock:
            if query_id in self.active_queries:
                query_info = self.active_queries.pop(query_id)
                execution_time = time.time() - query_info['start_time']
                
                # Query record
                query_record = {
                    'query': query_info['query'],
                    'execution_time': execution_time,
                    'timestamp': datetime.now(),
                    'thread_id': query_info['thread_id']
                }
                
                self.queries.append(query_record)
                
                # Update stats
                query_key = query_info['query'][:100]  # İlk 100 karakter
                stats = self.query_stats[query_key]
                stats['count'] += 1
                stats['total_time'] += execution_time
                stats['avg_time'] = stats['total_time'] / stats['count']
    
    def get_slow_queries(self, min_time: float = 0.1) -> List[Dict]:
        """Yavaş sorguları getir"""
        with self.lock:
            slow_queries = []
            for query in self.queries:
                if query['execution_time'] >= min_time:
                    slow_queries.append(query)
            return sorted(slow_queries, key=lambda x: x['execution_time'], reverse=True)
    
    def get_query_stats(self) -> Dict:
        """Sorgu istatistiklerini getir"""
        with self.lock:
            return dict(self.query_stats)

class MemoryManager:
    """Bellek yönetimi"""
    
    def __init__(self):
        self.cache_size_limit = 100 * 1024 * 1024  # 100MB
        self.cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        self.memory_warnings = []
        
    def optimize_memory(self):
        """Bellek optimizasyonu yap"""
        # Garbage collection
        collected = gc.collect()
        
        # Memory usage check
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        optimization_result = {
            'garbage_collected': collected,
            'memory_usage_mb': memory_info.rss / (1024 * 1024),
            'memory_percent': memory_percent,
            'timestamp': datetime.now()
        }
        
        # Eğer bellek kullanımı %80'i geçtiyse uyarı
        if memory_percent > 80:
            warning = {
                'type': 'HIGH_MEMORY_USAGE',
                'message': f'Memory usage: {memory_percent:.1f}%',
                'timestamp': datetime.now()
            }
            self.memory_warnings.append(warning)
        
        return optimization_result
    
    def get_cache_stats(self) -> Dict:
        """Cache istatistiklerini getir"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'evictions': self.cache_stats['evictions']
        }

class DatabaseOptimizer:
    """Veritabanı optimizasyonu"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.connection_pool_size = 10
        self.query_cache = {}
        self.query_cache_size = 1000
        
    def optimize_queries(self):
        """Sorgu optimizasyonu"""
        optimizations = []
        
        # Index önerileri
        index_suggestions = self._analyze_missing_indexes()
        optimizations.extend(index_suggestions)
        
        # Slow query optimizasyonu
        slow_query_fixes = self._analyze_slow_queries()
        optimizations.extend(slow_query_fixes)
        
        return optimizations
    
    def _analyze_missing_indexes(self) -> List[Dict]:
        """Eksik index analizi"""
        # Mock implementation - gerçek projede query plan analizi yapılır
        suggestions = [
            {
                'type': 'MISSING_INDEX',
                'table': 'containers',
                'column': 'status',
                'impact': 'HIGH',
                'suggestion': 'CREATE INDEX idx_containers_status ON containers(status);'
            },
            {
                'type': 'MISSING_INDEX',
                'table': 'ships',
                'column': 'arrival_date',
                'impact': 'MEDIUM',
                'suggestion': 'CREATE INDEX idx_ships_arrival_date ON ships(arrival_date);'
            }
        ]
        return suggestions
    
    def _analyze_slow_queries(self) -> List[Dict]:
        """Yavaş sorgu analizi"""
        # Mock implementation
        fixes = [
            {
                'type': 'SLOW_QUERY',
                'query': 'SELECT * FROM containers WHERE status = ?',
                'fix': 'Add WHERE clause limit or use pagination',
                'impact': 'HIGH'
            }
        ]
        return fixes

class PerformanceMonitor(QObject):
    """Performans izleme sistemi"""
    
    # Signals
    performance_updated = pyqtSignal(dict)
    alert_triggered = pyqtSignal(str, str)  # level, message
    
    def __init__(self):
        super().__init__()
        self.query_profiler = QueryProfiler()
        self.memory_manager = MemoryManager()
        self.metrics_history = deque(maxlen=1000)
        self.monitoring_enabled = True
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.collect_metrics)
        self.monitor_timer.start(5000)  # Her 5 saniyede bir
        
        # Optimization timer
        self.optimization_timer = QTimer()
        self.optimization_timer.timeout.connect(self.run_optimizations)
        self.optimization_timer.start(60000)  # Her dakika
    
    def collect_metrics(self):
        """Performans metriklerini topla"""
        if not self.monitoring_enabled:
            return
        
        try:
            # System metrics
            process = psutil.Process()
            cpu_usage = process.cpu_percent()
            memory_info = process.memory_info()
            memory_usage = memory_info.rss / (1024 * 1024)  # MB
            
            # Query metrics
            query_stats = self.query_profiler.get_query_stats()
            query_count = sum(stats['count'] for stats in query_stats.values())
            query_avg_time = sum(stats['avg_time'] for stats in query_stats.values()) / len(query_stats) if query_stats else 0
            
            # Cache metrics
            cache_stats = self.memory_manager.get_cache_stats()
            cache_hit_rate = cache_stats['hit_rate']
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                query_count=query_count,
                query_avg_time=query_avg_time,
                active_connections=1,  # Mock
                cache_hit_rate=cache_hit_rate,
                ui_response_time=0.0  # Mock
            )
            
            self.metrics_history.append(metrics)
            
            # Emit signal
            metrics_dict = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'query_count': query_count,
                'query_avg_time': query_avg_time,
                'cache_hit_rate': cache_hit_rate,
                'timestamp': metrics.timestamp.isoformat()
            }
            
            self.performance_updated.emit(metrics_dict)
            
            # Check for alerts
            self._check_performance_alerts(metrics)
            
        except Exception as e:
            print(f"❌ Metrics collection error: {e}")
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Performans uyarılarını kontrol et"""
        # CPU usage alert
        if metrics.cpu_usage > 80:
            self.alert_triggered.emit('WARNING', f'High CPU usage: {metrics.cpu_usage:.1f}%')
        
        # Memory usage alert
        if metrics.memory_usage > 500:  # 500MB
            self.alert_triggered.emit('WARNING', f'High memory usage: {metrics.memory_usage:.1f}MB')
        
        # Query performance alert
        if metrics.query_avg_time > 0.5:  # 500ms
            self.alert_triggered.emit('WARNING', f'Slow queries detected: {metrics.query_avg_time:.2f}s avg')
    
    def run_optimizations(self):
        """Optimizasyonları çalıştır"""
        if not self.monitoring_enabled:
            return
        
        try:
            # Memory optimization
            optimization_result = self.memory_manager.optimize_memory()
            
            # Log optimization
            print(f"🔧 Memory optimization: {optimization_result['garbage_collected']} objects collected")
            
        except Exception as e:
            print(f"❌ Optimization error: {e}")
    
    def get_performance_report(self) -> Dict:
        """Performans raporunu getir"""
        if not self.metrics_history:
            return {'error': 'No metrics available'}
        
        recent_metrics = list(self.metrics_history)[-60:]  # Son 60 ölçüm
        
        # Calculate averages
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_query_time = sum(m.query_avg_time for m in recent_metrics) / len(recent_metrics)
        
        # Get slow queries
        slow_queries = self.query_profiler.get_slow_queries()
        
        return {
            'period': '5 minutes',
            'metrics': {
                'avg_cpu_usage': avg_cpu,
                'avg_memory_usage': avg_memory,
                'avg_query_time': avg_query_time,
                'total_queries': sum(m.query_count for m in recent_metrics),
                'cache_hit_rate': recent_metrics[-1].cache_hit_rate if recent_metrics else 0
            },
            'slow_queries': slow_queries[:10],  # Top 10 slow queries
            'memory_warnings': self.memory_manager.memory_warnings[-10:],  # Son 10 uyarı
            'recommendations': self._generate_recommendations(recent_metrics)
        }
    
    def _generate_recommendations(self, metrics: List[PerformanceMetrics]) -> List[str]:
        """Performans önerilerini oluştur"""
        recommendations = []
        
        # CPU usage recommendations
        avg_cpu = sum(m.cpu_usage for m in metrics) / len(metrics) if metrics else 0
        if avg_cpu > 70:
            recommendations.append("Consider reducing query complexity or adding database indexes")
        
        # Memory usage recommendations
        avg_memory = sum(m.memory_usage for m in metrics) / len(metrics) if metrics else 0
        if avg_memory > 300:
            recommendations.append("Consider implementing data pagination or reducing cache size")
        
        # Query performance recommendations
        avg_query_time = sum(m.query_avg_time for m in metrics) / len(metrics) if metrics else 0
        if avg_query_time > 0.2:
            recommendations.append("Optimize slow queries and consider adding database indexes")
        
        return recommendations

class PerformanceOptimizer:
    """Ana performans optimizasyon sınıfı"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.enabled = True
        
    def enable_monitoring(self):
        """Monitoring'i etkinleştir"""
        self.monitor.monitoring_enabled = True
        self.enabled = True
        print("✅ Performance monitoring enabled")
    
    def disable_monitoring(self):
        """Monitoring'i devre dışı bırak"""
        self.monitor.monitoring_enabled = False
        self.enabled = False
        print("❌ Performance monitoring disabled")
    
    def get_monitor(self) -> PerformanceMonitor:
        """Monitor nesnesini getir"""
        return self.monitor
    
    def profile_query(self, query_id: str, query: str):
        """Sorgu profiling başlat"""
        if self.enabled:
            self.monitor.query_profiler.start_query(query_id, query)
    
    def end_query_profiling(self, query_id: str):
        """Sorgu profiling bitir"""
        if self.enabled:
            self.monitor.query_profiler.end_query(query_id)
    
    def optimize_for_production(self):
        """Production için optimizasyon"""
        optimizations = []
        
        # Garbage collection optimization
        gc.set_threshold(700, 10, 10)  # More aggressive GC
        optimizations.append("Garbage collection thresholds optimized")
        
        # Memory optimization
        import sys
        if hasattr(sys, 'intern'):
            optimizations.append("String interning available")
        
        return optimizations

# Global optimizer instance
_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Global performans optimizer'ı getir"""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer

def save_performance_config(config: Dict):
    """Performans konfigürasyonunu kaydet"""
    config_path = 'performance_config.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_performance_config() -> Dict:
    """Performans konfigürasyonunu yükle"""
    config_path = 'performance_config.json'
    default_config = {
        'monitoring_enabled': True,
        'monitoring_interval': 5,
        'optimization_interval': 60,
        'memory_alert_threshold': 80,
        'cpu_alert_threshold': 80,
        'query_time_threshold': 0.5,
        'cache_size_limit': 104857600,  # 100MB
        'max_slow_queries': 100
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults
                default_config.update(config)
        except Exception as e:
            print(f"❌ Error loading performance config: {e}")
    
    return default_config

if __name__ == "__main__":
    # Test performance optimizer
    print("🧪 Testing Performance Optimizer...")
    
    optimizer = get_performance_optimizer()
    print("✅ Performance optimizer created")
    
    # Test query profiling
    optimizer.profile_query("test_query_1", "SELECT * FROM containers")
    time.sleep(0.1)
    optimizer.end_query_profiling("test_query_1")
    print("✅ Query profiling test completed")
    
    # Test performance report
    time.sleep(1)  # Wait for metrics collection
    report = optimizer.get_monitor().get_performance_report()
    print(f"✅ Performance report generated: {len(report.get('recommendations', []))} recommendations")
    
    print("\n🎉 Performance optimizer ready!")
