#!/usr/bin/env python3
# offline_mode.py - Offline çalışma için mock database sistemi

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class MockDatabase:
    """Gerçek veritabanı olmadan tüm özelliklerin çalışması için mock database"""
    
    def __init__(self):
        self.connection = self  # Kendini connection olarak göster
        self.containers = self._generate_mock_containers()
        self.ships = self._generate_mock_ships()
        self.lifecycle_states = self._generate_mock_lifecycle_states()
        self.lifecycle_history = self._generate_mock_lifecycle_history()
        self.notifications = self._generate_mock_notifications()
        
    def _generate_mock_containers(self):
        """Mock container verileri oluştur"""
        statuses = ['SAHA', 'GEMI', 'ATANMAMIS', 'DELIVERED', 'CUSTOMS']
        types = ['20ft', '40ft', '45ft']
        containers = []
        
        for i in range(50):
            container_id = f'CONT{100000 + i}'
            containers.append({
                'id': container_id,
                'tip': random.choice(types),
                'durum': random.choice(statuses),
                'lifecycle_state_name': random.choice(['IN_YARD', 'LOADED', 'DELIVERED', 'PENDING']),
                'lifecycle_color': random.choice(['#3498db', '#2ecc71', '#e74c3c', '#f39c12']),
                'arrival_date': datetime.now() - timedelta(days=random.randint(1, 30)),
                'departure_date': None if random.choice([True, False]) else datetime.now() - timedelta(days=random.randint(1, 10)),
                'created_at': datetime.now() - timedelta(days=random.randint(1, 60))
            })
        
        return containers
    
    def _generate_mock_ships(self):
        """Mock ship verileri oluştur"""
        ship_names = ['MV ATLAS', 'MV PACIFIC', 'MV EUROPA', 'MV ASIA STAR', 'MV OCEAN PRIDE']
        statuses = ['ARRIVED', 'DEPARTED', 'ANCHORED', 'LOADING', 'UNLOADING']
        ships = []
        
        for i, name in enumerate(ship_names):
            ships.append({
                'id': i + 1,
                'name': name,
                'status': random.choice(statuses),
                'arrival_date': datetime.now() - timedelta(days=random.randint(1, 15)),
                'departure_date': None if random.choice([True, False]) else datetime.now() - timedelta(days=random.randint(1, 5)),
                'created_at': datetime.now() - timedelta(days=random.randint(1, 30))
            })
        
        return ships
    
    def _generate_mock_lifecycle_states(self):
        """Mock lifecycle states oluştur"""
        return [
            {'id': 1, 'state_description': 'PENDING', 'color_code': '#f39c12', 'is_active': True},
            {'id': 2, 'state_description': 'IN_YARD', 'color_code': '#3498db', 'is_active': True},
            {'id': 3, 'state_description': 'LOADED', 'color_code': '#2ecc71', 'is_active': True},
            {'id': 4, 'state_description': 'DELIVERED', 'color_code': '#e74c3c', 'is_active': True},
            {'id': 5, 'state_description': 'CUSTOMS_PENDING', 'color_code': '#9b59b6', 'is_active': True},
            {'id': 6, 'state_description': 'DISPATCHED', 'color_code': '#34495e', 'is_active': True}
        ]
    
    def _generate_mock_lifecycle_history(self):
        """Mock lifecycle history oluştur"""
        history = []
        for container in self.containers[:10]:  # İlk 10 container için
            # Her container için 2-4 geçmiş kaydı
            num_changes = random.randint(2, 4)
            base_time = datetime.now() - timedelta(days=10)
            
            for i in range(num_changes):
                state = random.choice(self.lifecycle_states)
                prev_state = random.choice(self.lifecycle_states) if i > 0 else None
                
                history.append({
                    'container_id': container['id'],
                    'change_timestamp': base_time + timedelta(days=i*2),
                    'from_state_name': prev_state['state_description'] if prev_state else None,
                    'to_state_name': state['state_description'],
                    'color_code': state['color_code'],
                    'change_reason': random.choice([
                        'Container moved to yard',
                        'Loaded onto ship',
                        'Customs clearance completed',
                        'Delivery confirmed',
                        'System update',
                        'Manual state change'
                    ]),
                    'changed_by': random.choice(['operator', 'system', 'admin', 'yard_crew'])
                })
        
        return history
    
    def _generate_mock_notifications(self):
        """Mock notifications oluştur"""
        notifications = []
        alert_types = ['info', 'warning', 'error', 'critical']
        
        for i in range(20):
            notifications.append({
                'title': f'System Alert {i+1}',
                'message': f'This is a sample notification message for testing purposes #{i+1}',
                'alert_type': random.choice(alert_types),
                'created_at': datetime.now() - timedelta(hours=random.randint(1, 72))
            })
        
        return notifications
    
    # Database interface methods
    def cursor(self):
        """Mock cursor döndür"""
        return MockCursor(self)
    
    # Container methods
    def get_all_containers_detailed(self):
        """Tüm container'ları detaylı olarak getir"""
        return self.containers
    
    def get_lifecycle_states(self):
        """Lifecycle state'lerini getir"""
        return self.lifecycle_states
    
    def get_container_lifecycle_history(self, container_id):
        """Container lifecycle geçmişini getir"""
        return [h for h in self.lifecycle_history if h['container_id'] == container_id]
    
    def change_container_lifecycle_state(self, container_id, new_state_id, reason=None, changed_by="USER"):
        """Container state değiştir"""
        # Container'ı bul ve state'ini güncelle
        for container in self.containers:
            if container['id'] == container_id:
                new_state = next((s for s in self.lifecycle_states if s['id'] == new_state_id), None)
                if new_state:
                    # Eski state'i kaydet
                    old_state = container['lifecycle_state_name']
                    
                    # Yeni state'i ata
                    container['lifecycle_state_name'] = new_state['state_description']
                    container['lifecycle_color'] = new_state['color_code']
                    
                    # History'ye ekle
                    self.lifecycle_history.append({
                        'container_id': container_id,
                        'change_timestamp': datetime.now(),
                        'from_state_name': old_state,
                        'to_state_name': new_state['state_description'],
                        'color_code': new_state['color_code'],
                        'change_reason': reason or 'State changed via UI',
                        'changed_by': changed_by
                    })
                    
                    return True
        return False
    
    def get_containers_count(self):
        """Toplam konteyner sayısını al - offline mode"""
        return len(self.containers)
    
class MockCursor:
    """Mock database cursor"""
    
    def __init__(self, db):
        self.db = db
        self.results = []
    
    def execute(self, query, params=None):
        """Mock SQL query execution"""
        query_lower = query.lower().strip()
        
        # Container queries
        if 'select count(*) from containers' in query_lower:
            if 'status in' in query_lower:
                # Port utilization query
                self.results = [(random.randint(20, 80),)]
            else:
                # Total containers
                self.results = [(len(self.db.containers),)]
                
        elif 'select status, count(*) from containers' in query_lower:
            # Container status breakdown
            statuses = {}
            for container in self.db.containers:
                status = container['durum']
                statuses[status] = statuses.get(status, 0) + 1
            self.results = list(statuses.items())
            
        elif 'container_lifecycle' in query_lower and 'count(*)' in query_lower:
            # Lifecycle movements
            self.results = [(len(self.db.lifecycle_history),)]
            
        elif 'new_state, count(*)' in query_lower:
            # State distribution
            states = {}
            for history in self.db.lifecycle_history:
                state = history['to_state_name']
                states[state] = states.get(state, 0) + 1
            self.results = list(states.items())
            
        # Ship queries
        elif 'select count(*) from ships' in query_lower:
            self.results = [(len(self.db.ships),)]
            
        elif 'select status, count(*) from ships' in query_lower:
            # Ship status breakdown
            statuses = {}
            for ship in self.db.ships:
                status = ship['status']
                statuses[status] = statuses.get(status, 0) + 1
            self.results = list(statuses.items())
            
        # Date-based ship queries
        elif 'arrival_date >=' in query_lower and 'ships' in query_lower:
            if 'count(*)' in query_lower:
                # Ship arrivals/departures count
                self.results = [(random.randint(2, 8),)]
            else:
                # Ship trends
                dates = []
                for i in range(7):
                    date = datetime.now().date() - timedelta(days=i)
                    count = random.randint(1, 5)
                    dates.append((date, count))
                self.results = dates
                
        # Container trends
        elif 'arrival_date >=' in query_lower and 'containers' in query_lower:
            dates = []
            for i in range(7):
                date = datetime.now().date() - timedelta(days=i)
                count = random.randint(3, 12)
                dates.append((date, count))
            self.results = dates
            
        # Audit log / performance
        elif 'audit_log' in query_lower:
            self.results = [(random.randint(50, 200), random.uniform(10, 50))]
            
        # Notifications
        elif 'notifications' in query_lower:
            if 'alert_type in' in query_lower:
                # Get alerts
                alerts = []
                for notif in self.db.notifications:
                    if notif['alert_type'] in ['warning', 'error', 'critical']:
                        alerts.append((
                            notif['title'],
                            notif['message'],
                            notif['alert_type'],
                            notif['created_at']
                        ))
                self.results = alerts
            
        # Default fallback
        else:
            self.results = [(0,)]
    
    def fetchone(self):
        """Tek sonuç getir"""
        return self.results[0] if self.results else None
    
    def fetchall(self):
        """Tüm sonuçları getir"""
        return self.results
    
    def close(self):
        """Cursor'u kapat"""
        pass

# Global offline mode flag
OFFLINE_MODE = False  # Varsayılan olarak PostgreSQL kullan

# Environment variable ile kontrol
import os
if os.getenv('FORCE_OFFLINE_MODE') == 'true':
    OFFLINE_MODE = True
elif os.getenv('FORCE_ONLINE_MODE') == 'true':
    OFFLINE_MODE = False

# Config dosyasından da kontrol et
try:
    import json
    with open('config.json', 'r') as f:
        config = json.load(f)
        if config.get('database', {}).get('offline_mode', False):
            OFFLINE_MODE = True
except:
    pass

def get_database_connection():
    """Database bağlantısı getir (offline modda mock döner)"""
    if OFFLINE_MODE:
        return MockDatabase()
    else:
        # Gerçek database bağlantısı
        from database import Database
        return Database()

def create_offline_config():
    """Offline mod için config oluştur"""
    config = {
        "database": {
            "offline_mode": True,
            "mock_data": True
        },
        "colors": {
            "filled": "#e74c3c",
            "pending": "#f1c40f",
            "placeable": "#2ecc71",
            "incompatible": "#e67e22",
            "empty": "#bdc3c7",
            "reefer": "#3498db"
        },
        "theme": "dark",
        "offline_features": {
            "container_lifecycle": True,
            "advanced_reporting": True,
            "notifications": True,
            "performance_metrics": True
        }
    }
    
    with open('config_offline.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    return config

if __name__ == "__main__":
    # Test offline database
    print("🧪 Testing Offline Database...")
    
    mock_db = MockDatabase()
    print(f"✅ Generated {len(mock_db.containers)} containers")
    print(f"✅ Generated {len(mock_db.ships)} ships")
    print(f"✅ Generated {len(mock_db.lifecycle_states)} lifecycle states")
    print(f"✅ Generated {len(mock_db.lifecycle_history)} history records")
    
    # Test container lifecycle
    test_container = mock_db.containers[0]
    print(f"\n📦 Testing container: {test_container['id']}")
    
    history = mock_db.get_container_lifecycle_history(test_container['id'])
    print(f"✅ History records: {len(history)}")
    
    # Test state change
    success = mock_db.change_container_lifecycle_state(
        test_container['id'], 
        3,  # LOADED state
        "Test state change",
        "test_user"
    )
    print(f"✅ State change: {'Success' if success else 'Failed'}")
    
    print("\n🎉 Offline database ready!")
