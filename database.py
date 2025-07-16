# database.py (Eksik Rapor Fonksiyonları Eklenmiş Tam Hali)

import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
import config_manager
import time
from datetime import datetime

# Offline mode kontrolü
try:
    from offline_mode import get_database_connection, OFFLINE_MODE
    if OFFLINE_MODE:
        print("🎭 Offline mode aktif - Mock database kullanılacak")
except ImportError:
    OFFLINE_MODE = False

# Yeni modülleri import et
try:
    import sys
    import os
    # Mevcut dizindeki dosyaları import etmeye zorla
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from system_logger import logger_factory, LogLevel
    from performance_optimizer import PerformanceOptimizer
    ADVANCED_FEATURES_ENABLED = True
    print("✅ Advanced features enabled successfully!")
except ImportError as e:
    ADVANCED_FEATURES_ENABLED = False
    print(f"⚠️  Gelişmiş özellikler henüz kurulmadı: {e}. Temel özellikler kullanılacak.")
except Exception as e:
    ADVANCED_FEATURES_ENABLED = False
    print(f"⚠️  Beklenmeyen hata: {e}. Temel özellikler kullanılacak.")

class DatabaseConnection:
    def __init__(self):
        # Offline mode kontrolü
        if OFFLINE_MODE:
            print("🎭 Offline mode - PostgreSQL gerektirmez")
            from offline_mode import MockDatabase
            mock_db = MockDatabase()
            # Mock database'den tüm özellikleri kopyala
            for attr in dir(mock_db):
                if not attr.startswith('_'):
                    setattr(self, attr, getattr(mock_db, attr))
            self.connection = mock_db  # Mock bağlantı
            self.conn = mock_db
            return
        
        # Normal PostgreSQL mode
        self.db_config = config_manager.get_config().get("database")
        self.conn = None
        
        self.connect()
        
        # Gelişmiş özellikler
        if ADVANCED_FEATURES_ENABLED:
            self._init_advanced_features()
    
    @property
    def connection(self):
        """Provide connection property for backward compatibility"""
        return self.conn
        
    def _init_advanced_features(self):
        """Gelişmiş özellikleri başlat"""
        try:
            # Logger'ı başlat
            self.logger = logger_factory.get_logger(self)
            self.audit_trail = logger_factory.get_audit_trail(self, self.logger)
            self.performance_logger = logger_factory.get_performance_logger(self, self.logger)
            self.notification_manager = logger_factory.get_notification_manager(self, self.logger)
            
            # Basit cache sistemi (şimdilik performance_optimizer olmadan)
            self.cache = {}
            self.cache_timestamps = {}
            
            print("✅ Advanced features initialized successfully")
            
        except Exception as e:
            print(f"⚠️  Gelişmiş özellik başlatma hatası: {e}")
            # Global değişkeni değiştiremeyiz, sadece yerel attributeları None yapalım
            self.logger = None
            self.cache = None

    def connect(self):
        """Database connection with improved error handling"""
        try:
            # Close existing connection if any
            if self.conn and not self.conn.closed:
                try:
                    self.conn.close()
                except:
                    pass
            
            # Create new connection
            self.conn = psycopg2.connect(**self.db_config)
            
            # Test the connection immediately
            with self.conn.cursor() as test_cursor:
                test_cursor.execute("SELECT 1")
                test_cursor.fetchone()
            
            if ADVANCED_FEATURES_ENABLED and hasattr(self, 'logger'):
                try:
                    self.logger.info("Database connection established", module_name="DatabaseConnection")
                except:
                    pass
                
        except psycopg2.OperationalError as e:
            self.conn = None
            
            if ADVANCED_FEATURES_ENABLED and hasattr(self, 'logger'):
                try:
                    self.logger.error(f"Database connection failed: {e}", module_name="DatabaseConnection")
                except:
                    pass
        except Exception as e:
            self.conn = None

    def close_connection(self):
        if self.conn:
            self.conn.close()
            
        if ADVANCED_FEATURES_ENABLED and hasattr(self, 'performance_optimizer'):
            self.performance_optimizer.stop_metrics_collection()

    def execute_query(self, query, params=(), fetchone=False, fetchall=False, _retry_count=0):
        """Execute database query with proper error handling and connection management"""
        # Prevent infinite retry loops
        max_retries = 2
        if _retry_count >= max_retries:
            print(f"❌ Maximum retry attempts ({max_retries}) reached")
            return False
            
        # Check and establish connection
        if not self.conn or (hasattr(self.conn, 'closed') and self.conn.closed):
            print(f"⚠️  Database connection not available (retry {_retry_count + 1}/{max_retries + 1})")
            self.connect()
            if not self.conn:
                print("❌ Could not establish database connection")
                return False
            
        start_time = time.time()
        
        try:
            # Double-check connection state
            if hasattr(self.conn, 'closed') and self.conn.closed:
                print("⚠️  Connection was closed during execution, reconnecting...")
                self.connect()
                if not self.conn:
                    return False
            
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            
            if fetchone:
                result = cursor.fetchone()
                cursor.close()
            elif fetchall:
                result = cursor.fetchall()
                cursor.close()
            else:
                # For INSERT/UPDATE/DELETE operations
                affected_rows = cursor.rowcount
                cursor.close()
                self.conn.commit()
                result = True
                
            # Performance logging (only on success)
            if ADVANCED_FEATURES_ENABLED and hasattr(self, 'performance_logger'):
                execution_time = (time.time() - start_time) * 1000
                rows_affected = affected_rows if 'affected_rows' in locals() else 0
                try:
                    self.performance_logger.log_query_performance(
                        query, execution_time, params, rows_affected
                    )
                except:
                    pass  # Don't let logging errors break the main operation
            
            return result
                
        except psycopg2.OperationalError as e:
            print(f"❌ Connection error (attempt {_retry_count + 1}): {e}")
            
            # Try to reconnect and retry (with limit)
            if _retry_count < max_retries:
                print(f"⚠️  Attempting to reconnect and retry ({_retry_count + 1}/{max_retries})...")
                try:
                    self.conn = None  # Reset connection
                    self.connect()
                    if self.conn:
                        return self.execute_query(query, params, fetchone, fetchall, _retry_count + 1)
                except Exception as reconnect_error:
                    print(f"❌ Reconnection failed: {reconnect_error}")
            
            return False
            
        except psycopg2.Error as e:
            print(f"❌ Database error: {e}")
            print(f"   Query: {query[:100]}...")
            print(f"   Params: {params}")
            
            # Rollback transaction
            try:
                if self.conn and not self.conn.closed:
                    self.conn.rollback()
            except Exception as rollback_error:
                print(f"⚠️  Rollback failed: {rollback_error}")
            
            # Log error if available
            if ADVANCED_FEATURES_ENABLED and hasattr(self, 'logger'):
                try:
                    self.logger.error(f"Query error: {e}", module_name="DatabaseConnection", 
                                    additional_data={"query": query[:100], "params": str(params)})
                except:
                    pass
            
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            try:
                if self.conn and not self.conn.closed:
                    self.conn.rollback()
            except:
                pass
            return False

    # Container Lifecycle Methods
    def get_lifecycle_states(self):
        """Konteyner lifecycle state'lerini getir"""
        try:
            return self.execute_query(
                "SELECT * FROM container_lifecycle_states WHERE is_active = true ORDER BY id", 
                fetchall=True
            )
        except:
            # Eğer tablo yoksa boş liste döndür
            return []
    
    def change_container_lifecycle_state(self, container_id, new_state_id, reason=None, changed_by="USER"):
        """Konteyner lifecycle state'ini değiştir"""
        try:
            # Önce geçerli state'i ve cycle count'ı al
            current_state_query = "SELECT current_lifecycle_state, lifecycle_cycle_count FROM public.konteynerler WHERE id = %s"
            current_state_result = self.execute_query(current_state_query, (container_id,), fetchone=True)
            
            if not current_state_result:
                print(f"Container {container_id} bulunamadı")
                return False
            
            current_state = current_state_result.get('current_lifecycle_state')
            current_cycle_count = current_state_result.get('lifecycle_cycle_count', 0)
            
            # Lifecycle history'ye ekle
            history_query = """
                INSERT INTO public.container_lifecycle_history 
                (container_id, from_state_id, to_state_id, change_timestamp, change_reason, changed_by)
                VALUES (%s, %s, %s, NOW(), %s, %s)
            """
            
            history_result = self.execute_query(history_query, (container_id, current_state, new_state_id, reason, changed_by))
            
            if history_result:
                # Eğer DELIVERED (9 veya 11) state'ine geçiş yapılıyorsa cycle count'ı artır
                new_cycle_count = current_cycle_count
                final_state_id = new_state_id
                
                if new_state_id == 9 or new_state_id == 11:  # DELIVERED state (hem 9 hem 11)
                    new_cycle_count = current_cycle_count + 1
                    final_state_id = 1  # Cycle tamamlandı, yeni cycle için ORDERED state'e geç
                    
                    print(f"🔄 Container {container_id}: Cycle {new_cycle_count} tamamlandı (State {new_state_id}→1), yeni cycle başlıyor")
                    
                    # Cycle tamamlandığında additional history kaydı
                    additional_history_query = """
                        INSERT INTO public.container_lifecycle_history 
                        (container_id, from_state_id, to_state_id, change_timestamp, change_reason, changed_by)
                        VALUES (%s, %s, %s, NOW(), %s, %s)
                    """
                    
                    self.execute_query(additional_history_query, (container_id, new_state_id, 1, f"Cycle {new_cycle_count} tamamlandı - Yeni cycle başlıyor", "SYSTEM"))
                
                # Konteyner'in current state'ini ve cycle count'ını güncelle
                update_query = """
                    UPDATE public.konteynerler 
                    SET current_lifecycle_state = %s, lifecycle_cycle_count = %s 
                    WHERE id = %s
                """
                update_result = self.execute_query(update_query, (final_state_id, new_cycle_count, container_id))
                
                if update_result:
                    print(f"✅ Container {container_id} state changed to {final_state_id}, cycle count: {new_cycle_count}")
                    
                    # Cache'i temizle - UI'da güncel veri görünsün
                    if ADVANCED_FEATURES_ENABLED and hasattr(self, 'cache') and self.cache is not None:
                        # Tüm container cache'lerini temizle
                        cache_keys_to_remove = []
                        for key in self.cache.keys():
                            if key.startswith('all_containers_detailed_'):
                                cache_keys_to_remove.append(key)
                        
                        for key in cache_keys_to_remove:
                            del self.cache[key]
                        
                        print(f"🧹 Cache temizlendi: {len(cache_keys_to_remove)} cache key'i silindi")
                    
                    return True
                else:
                    print(f"❌ Failed to update container {container_id} state")
                    return False
            else:
                print(f"❌ Failed to create history record for container {container_id}")
                return False
                
        except Exception as e:
            print(f"❌ Lifecycle state change error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_state_name(self, state_id):
        """State ID'den state adını al"""
        try:
            result = self.execute_query(
                "SELECT state_name FROM container_lifecycle_states WHERE id = %s", 
                (state_id,), fetchone=True
            )
            return result['state_name'] if result else 'UNKNOWN'
        except:
            return 'UNKNOWN'
    
    def get_container_lifecycle_history(self, container_id):
        """Konteyner lifecycle geçmişini getir"""
        try:
            query = """
                SELECT clh.*, 
                       from_state.state_name as from_state_name,
                       to_state.state_name as to_state_name
                FROM container_lifecycle_history clh
                LEFT JOIN container_lifecycle_states from_state ON clh.from_state_id = from_state.id
                JOIN container_lifecycle_states to_state ON clh.to_state_id = to_state.id
                WHERE clh.container_id = %s
                ORDER BY clh.change_timestamp DESC
            """
            return self.execute_query(query, (container_id,), fetchall=True)
        except:
            # Eğer tablolar yoksa boş liste döndür
            return []

    # Cached methods
    def get_all_containers_detailed(self, limit=None, offset=None):
        """Cache'li konteyner listesi - sayfalama desteği ile"""
        cache_key = f"all_containers_detailed_{limit}_{offset}"
        
        if ADVANCED_FEATURES_ENABLED and hasattr(self, 'cache') and self.cache is not None:
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        # Base query
        query = """
            SELECT k.*, cls.state_name as lifecycle_state_name, cls.color_code as lifecycle_color
            FROM public.konteynerler k
            LEFT JOIN container_lifecycle_states cls ON k.current_lifecycle_state = cls.id
            ORDER BY k.id ASC
        """
        
        # Sayfalama ekle
        params = []
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
            if offset is not None:
                query += " OFFSET %s"
                params.append(offset)
        
        result = self.execute_query(query, params if params else None, fetchall=True)
        
        # Cache'e kaydet (sadece küçük result setleri için)
        if ADVANCED_FEATURES_ENABLED and hasattr(self, 'cache') and self.cache is not None and result:
            if not limit or limit <= 1000:  # Sadece küçük sonuçları cache'le
                self.cache[cache_key] = result
        
        return result
    
    def get_containers_count(self):
        """Toplam konteyner sayısını al"""
        query = "SELECT COUNT(*) as total FROM public.konteynerler"
        result = self.execute_query(query, fetchall=True)
        return result[0]['total'] if result else 0

    def add_new_container(self, c_id, c_tip, c_cikis, c_varis, c_durum='ATANMAMIS'):
        """Yeni konteyner ekle - Enhanced with detailed logging"""
        
        try:
            # Connection check 
            if not self.conn or (hasattr(self.conn, 'closed') and self.conn.closed):
                self.connect()
                
            if not self.conn:
                error_msg = "Veritabanı bağlantısı kurulamadı"
                print(f"❌ {error_msg}")
                return error_msg
            
            print(f"🔧 DEBUG: Connection status: {self.conn}")
            
            # Check if container already exists
            print(f"🔧 DEBUG: Checking if container {c_id} already exists...")
            existing = self.get_container_details_by_id(c_id)
            if existing:
                error_msg = f"Konteyner ID {c_id} zaten mevcut"
                print(f"⚠️  {error_msg}")
                return error_msg
            
            print(f"🔧 DEBUG: Container {c_id} is unique, proceeding with insert...")
            
            # Insert new container
            result = self.execute_query(
                "INSERT INTO public.konteynerler (id, tip, cikis_limani, varis_limani, durum, current_lifecycle_state) VALUES (%s, %s, %s, %s, %s, %s)", 
                (c_id, c_tip, c_cikis, c_varis, c_durum, 3)
            )
            
            print(f"🔧 DEBUG: Execute query result: {result}")
            
            if result:
                print(f"✅ Konteyner {c_id} başarıyla eklendi: {c_id}")
                
                # CRITICAL: Clear all caches immediately after successful insert
                try:
                    # Clear database cache
                    if hasattr(self, 'cache') and self.cache is not None:
                        print("🧹 Clearing database cache...")
                        if hasattr(self.cache, 'clear'):
                            self.cache.clear()
                        elif isinstance(self.cache, dict):
                            self.cache.clear()
                        print("✅ Database cache cleared")
                except Exception as e:
                    print(f"⚠️  Database cache clear error: {e}")
                
                # Advanced features (non-blocking)
                if ADVANCED_FEATURES_ENABLED:
                    try:
                        # Cache temizle (performance optimizer)
                        if hasattr(self, 'performance_optimizer') and hasattr(self.performance_optimizer, 'cache'):
                            print("🧹 Clearing performance optimizer cache...")
                            self.performance_optimizer.cache.invalidate(cache_type="containers")
                            print("✅ Performance optimizer cache cleared")
                    except Exception as e:
                        print(f"⚠️  Performance optimizer cache invalidate error (non-critical): {e}")
                    
                    try:
                        # Audit log
                        if hasattr(self, 'audit_trail') and hasattr(self.audit_trail, 'log_change'):
                            self.audit_trail.log_change(
                                table_name="konteynerler",
                                record_id=c_id,
                                action_type="INSERT",
                                new_values={"id": c_id, "tip": c_tip, "cikis_limani": c_cikis, "varis_limani": c_varis, "durum": c_durum}
                            )
                    except Exception as e:
                        print(f"⚠️  Audit log error (non-critical): {e}")
                    
                    try:
                        # Bildirim oluştur
                        if hasattr(self, 'system_logger') and hasattr(self.system_logger, 'create_notification'):
                            self.system_logger.create_notification(
                                title='Yeni Konteyner Eklendi',
                                message=f'Konteyner {c_id} sisteme eklendi.',
                                notification_type='INFO',
                                priority=2,
                                source='CONTAINER_MANAGEMENT',
                                related_id=c_id
                            )
                    except Exception as e:
                        print(f"⚠️  Notification error (non-critical): {e}")
                
                return True
            else:
                error_msg = "Veritabanına kayıt eklenemedi"
                print(f"❌ {error_msg}")
                return error_msg
                
        except psycopg2.IntegrityError as e:
            error_msg = f"Konteyner ID {c_id} zaten mevcut (Integrity Error)"
            print(f"❌ {error_msg}: {e}")
            return error_msg
        except psycopg2.Error as e:
            error_msg = f"PostgreSQL hatası: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Beklenmeyen hata: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def update_container_full_details(self, c_id, c_tip, c_durum, c_konum, c_cikis, c_varis):
        """Konteyner detaylarını güncelle"""
        # Eski değerleri al (audit için)
        old_values = None
        if ADVANCED_FEATURES_ENABLED and hasattr(self, 'audit_trail'):
            old_container = self.get_container_details_by_id(c_id)
            old_values = dict(old_container) if old_container else None
        
        saha_konum = c_konum if c_konum and c_durum == 'SAHA' else None
        gemi_id, gemi_konum = None, None
        if c_durum == 'ATANMAMIS': 
            saha_konum = None
            
        query = "UPDATE public.konteynerler SET tip=%s, durum=%s, saha_konum=%s, cikis_limani=%s, varis_limani=%s, gemi_id=%s, gemi_konum=%s WHERE id=%s"
        params = (c_tip, c_durum, saha_konum, c_cikis, c_varis, gemi_id, gemi_konum, c_id)
        result = self.execute_query(query, params)
        
        if result and ADVANCED_FEATURES_ENABLED:
            # Audit log
            if hasattr(self, 'audit_trail') and old_values:
                new_values = {
                    "tip": c_tip, "durum": c_durum, "saha_konum": saha_konum,
                    "cikis_limani": c_cikis, "varis_limani": c_varis
                }
                self.audit_trail.log_change(
                    table_name="konteynerler",
                    record_id=c_id,
                    action_type="UPDATE",
                    old_values=old_values,
                    new_values=new_values
                )
            
            # Cache temizle
            if hasattr(self, 'performance_optimizer'):
                self.performance_optimizer.cache.invalidate(cache_type="containers")
        
        return result

    def delete_container_by_id(self, c_id):
        return self.execute_query("DELETE FROM public.konteynerler WHERE id=%s", (c_id,))

    def get_container_details_by_id(self, c_id):
        """Konteyner detaylarını ID ile getir"""
        try:
            print(f"🔧 DEBUG: Getting container details for ID: {c_id}")
            
            if not self.conn:
                print("⚠️  Database connection is None, attempting to connect...")
                self.connect()
                
            if not self.conn:
                print("❌ Could not establish database connection")
                return None
                
            result = self.execute_query("SELECT * FROM public.konteynerler WHERE id = %s", (c_id,), fetchone=True)
            print(f"🔧 DEBUG: Query result for {c_id}: {result}")
            return result
            
        except Exception as e:
            print(f"❌ Error in get_container_details_by_id: {e}")
            return None
        
    def get_all_loadable_containers(self):
        return self.execute_query("SELECT * FROM public.konteynerler WHERE durum = 'SAHA' OR durum = 'ATANMAMIS'", fetchall=True)

    def get_unassigned_containers(self):
        return self.execute_query("SELECT * FROM public.konteynerler WHERE durum = 'ATANMAMIS'", fetchall=True)

    def get_all_yard_containers(self):
        return self.execute_query("SELECT * FROM public.konteynerler WHERE durum = 'SAHA' AND saha_konum IS NOT NULL", fetchall=True)

    def update_container_yard_location(self, container_id, location):
        params = (location, container_id) if location else (container_id,)
        query = "UPDATE public.konteynerler SET saha_konum = %s, durum = 'SAHA', gemi_id = NULL, gemi_konum = NULL WHERE id = %s" if location else "UPDATE public.konteynerler SET saha_konum = NULL, durum = 'ATANMAMIS' WHERE id = %s"
        return self.execute_query(query, params)
        
    def get_all_ships(self):
        return self.execute_query("SELECT * FROM public.gemiler ORDER BY gemi_id ASC", fetchall=True)

    def add_container_to_ship(self, container_id, ship_id, row, tier, bay_id):
        gemi_konum_str = f"{bay_id}-R{row}-T{tier}"
        try:
            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute("UPDATE public.konteynerler SET durum = 'GEMI', saha_konum = NULL, gemi_id = %s, gemi_konum = %s WHERE id = %s", (ship_id, gemi_konum_str, container_id))
                    cursor.execute("DELETE FROM public.gemi_yuklemeler WHERE konteyner_id = %s", (container_id,))
                    cursor.execute("INSERT INTO public.gemi_yuklemeler (konteyner_id, gemi_id, gemi_satir, gemi_sutun, gemi_bay, yukleme_tarihi) VALUES (%s, %s, %s, %s, %s, NOW())", (container_id, ship_id, row, tier, bay_id))
            return True
        except psycopg2.Error as e: print(f"Gemiye konteyner ekleme hatası: {e}"); self.conn.rollback(); return False

    def update_container_ship_location(self, container_id, bay_id, new_row, new_tier):
        gemi_konum_str = f"{bay_id}-R{new_row}-T{new_tier}"
        try:
            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute("UPDATE public.konteynerler SET gemi_konum = %s WHERE id = %s", (gemi_konum_str, container_id))
                    cursor.execute("UPDATE public.gemi_yuklemeler SET gemi_bay=%s, gemi_satir=%s, gemi_sutun=%s WHERE konteyner_id=%s", (bay_id, new_row, new_tier, container_id))
            return True
        except psycopg2.Error as e: print(f"Gemi konumu güncelleme hatası: {e}"); self.conn.rollback(); return False
        
    def get_all_ship_slots(self, ship_id):
        query = "SELECT k.*, gy.gemi_satir, gy.gemi_sutun as gemi_tier, gy.gemi_bay FROM public.gemi_yuklemeler gy JOIN public.konteynerler k ON gy.konteyner_id = k.id WHERE gy.gemi_id = %s"
        records = self.execute_query(query, (ship_id,), fetchall=True)
        slots = defaultdict(dict)
        if records:
            for r in records: slots[r['gemi_bay']][(r['gemi_satir'], r['gemi_tier'])] = r
        return slots

    def add_ship(self, gemi_id, gemi_adi, toplam_bay, toplam_sira, toplam_kat):
        query = "INSERT INTO public.gemiler (gemi_id, gemi_adi, toplam_bay_sayisi, toplam_sira_sayisi, toplam_kat_sayisi) VALUES (%s, %s, %s, %s, %s)"
        return self.execute_query(query, (gemi_id, gemi_adi, toplam_bay, toplam_sira, toplam_kat))

    def update_ship(self, gemi_id, gemi_adi, toplam_bay, toplam_sira, toplam_kat):
        query = "UPDATE public.gemiler SET gemi_adi=%s, toplam_bay_sayisi=%s, toplam_sira_sayisi=%s, toplam_kat_sayisi=%s WHERE gemi_id=%s"
        return self.execute_query(query, (gemi_adi, toplam_bay, toplam_sira, toplam_kat, gemi_id))

    def delete_ship(self, gemi_id):
        self.execute_query("UPDATE public.konteynerler SET durum='ATANMAMIS', gemi_id=NULL, gemi_konum=NULL WHERE gemi_id=%s", (gemi_id,))
        return self.execute_query("DELETE FROM public.gemiler WHERE gemi_id=%s", (gemi_id,))
        
    def generate_next_ship_id(self):
        """Yeni gemi ID'si oluştur - çakışma kontrolü ile"""
        try:
            # Sadece 'GEMI-XX' formatındaki ID'leri seç
            query = "SELECT gemi_id FROM public.gemiler WHERE gemi_id ~ '^GEMI-\\d+$' ORDER BY CAST(SUBSTRING(gemi_id FROM 6) AS INTEGER) DESC LIMIT 1"
            last_id_row = self.execute_query(query, fetchone=True)
            if not last_id_row or not last_id_row.get('gemi_id'):
                return "GEMI-01"
            try:
                last_id = last_id_row['gemi_id']
                num = int(last_id.split('-')[-1])
                
                # Yeni ID oluştur ve çakışma kontrolü yap
                for i in range(1, 100):  # Maksimum 100 deneme
                    new_id = f"GEMI-{(num + i):02d}"
                    
                    # ID'nin kullanılıp kullanılmadığını kontrol et
                    check_query = "SELECT COUNT(*) as count FROM public.gemiler WHERE gemi_id = %s"
                    check_result = self.execute_query(check_query, (new_id,), fetchone=True)
                    
                    if check_result and check_result.get('count', 0) == 0:
                        return new_id
                
                # Eğer 100 deneme sonucu bulunamazsa, timestamp ile unique ID oluştur
                from datetime import datetime
                timestamp = datetime.now().strftime("%H%M%S")
                return f"GEMI-{timestamp}"
                
            except (ValueError, IndexError):
                return "GEMI-01"
                
        except Exception as e:
            print(f"Generate ship ID error: {e}")
            # Fallback: timestamp ile unique ID
            from datetime import datetime
            timestamp = datetime.now().strftime("%H%M%S")
            return f"GEMI-{timestamp}"

    def get_vehicles(self):
        return self.execute_query("SELECT * FROM public.araclar ORDER BY id ASC", fetchall=True)

    def update_vehicle_status(self, vehicle_id, status):
        return self.execute_query("UPDATE public.araclar SET durum=%s WHERE id=%s", (status, vehicle_id))
        
    def assign_vehicle_to_transport(self, vehicle_id, container_id):
        try:
            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute("UPDATE public.araclar SET durum='MEŞGUL' WHERE id=%s", (vehicle_id,))
                    cursor.execute("INSERT INTO public.tasima_loglari (konteyner_id, arac_id, islem_tipi, islem_tarihi) VALUES (%s, %s, 'ATAMA YAPILDI', NOW())", (container_id, vehicle_id))
            return True
        except psycopg2.Error as e: print(f"Araç atama hatası: {e}"); self.conn.rollback(); return False
            
    def get_report_data(self):
        query = "SELECT COUNT(*) as dolu_slot FROM public.konteynerler WHERE durum = 'SAHA'"; result = self.execute_query(query, fetchone=True)
        return {'occupancy_rate': (result['dolu_slot'] / 700) * 100 if result else 0}

    def get_ship_occupancy_data(self, ship_id=None):
        base_query = "SELECT g.gemi_id, g.gemi_adi, (g.toplam_bay_sayisi * g.toplam_sira_sayisi * g.toplam_kat_sayisi) as kapasite, COUNT(gy.id) as dolu_slot FROM public.gemiler g LEFT JOIN public.gemi_yuklemeler gy ON g.gemi_id = gy.gemi_id"
        params = (ship_id,) if ship_id else ()
        if ship_id: base_query += " WHERE g.gemi_id = %s"
        base_query += " GROUP BY g.gemi_id, g.gemi_adi, kapasite"
        results = self.execute_query(base_query, params, fetchall=True)
        if results:
            for r in results: r['doluluk_orani'] = (r['dolu_slot'] * 100.0 / r['kapasite']) if r['kapasite'] > 0 else 0
        return results

    def get_container_type_distribution_data(self, location_type=None, ship_id=None):
        params, query, where_clauses = (), "SELECT tip, COUNT(*) as count FROM public.konteynerler ", []
        if location_type == 'SAHA': where_clauses.append("durum = 'SAHA'")
        elif location_type == 'GEMI':
            where_clauses.append("durum = 'GEMI'")
            if ship_id: where_clauses.append("gemi_id = %s"); params = (ship_id,)
        elif location_type == 'ATANMAMIS': where_clauses.append("durum = 'ATANMAMIS'")
        if where_clauses: query += "WHERE " + " AND ".join(where_clauses)
        query += " GROUP BY tip"; return self.execute_query(query, params, fetchall=True)
    
    ### DÜZELTME: Eksik olan raporlama fonksiyonu eklendi ###
    def get_port_traffic_data(self, start_date, end_date, traffic_type):
        params = (start_date, end_date)
        if traffic_type == 'Çıkış':
            query = "SELECT cikis_limani as liman, COUNT(*) as count FROM public.konteynerler WHERE giris_tarihi BETWEEN %s AND %s AND cikis_limani IS NOT NULL GROUP BY liman"
        elif traffic_type == 'Varış':
            query = "SELECT varis_limani as liman, COUNT(*) as count FROM public.konteynerler WHERE giris_tarihi BETWEEN %s AND %s AND varis_limani IS NOT NULL GROUP BY liman"
        else:
            query = "SELECT liman, SUM(count) as count FROM (SELECT cikis_limani as liman, COUNT(*) as count FROM public.konteynerler WHERE giris_tarihi BETWEEN %s AND %s AND cikis_limani IS NOT NULL GROUP BY liman UNION ALL SELECT varis_limani as liman, COUNT(*) as count FROM public.konteynerler WHERE giris_tarihi BETWEEN %s AND %s AND varis_limani IS NOT NULL GROUP BY liman) as traffic WHERE liman IS NOT NULL GROUP BY liman"
            params = (start_date, end_date, start_date, end_date)
        return self.execute_query(query, params, fetchall=True)

    def get_destination_port_distribution(self):
        query = "SELECT varis_limani, COUNT(*) as count FROM public.konteynerler WHERE varis_limani IS NOT NULL GROUP BY varis_limani ORDER BY count DESC"
        return self.execute_query(query, fetchall=True)

    def get_vehicle_usage_data(self, start_date, end_date, vehicle_type):
        # Önce taşıma loglarını deneyelim
        query = "SELECT t.arac_id, a.tip as arac_tipi, COUNT(t.id) as islem_sayisi FROM public.tasima_loglari t JOIN public.araclar a ON t.arac_id = a.id WHERE t.islem_tarihi BETWEEN %s AND %s"
        params = [start_date, end_date]
        if vehicle_type and vehicle_type != 'Tümü': 
            query += " AND a.tip = %s"
            params.append(vehicle_type)
        query += " GROUP BY t.arac_id, a.tip ORDER BY islem_sayisi DESC"
        
        result = self.execute_query(query, tuple(params), fetchall=True)
        
        # Eğer taşıma logları yoksa, mevcut araçların durumunu göster
        if not result:
            query = "SELECT id as arac_id, tip as arac_tipi, durum, 0 as islem_sayisi FROM public.araclar"
            params = []
            if vehicle_type and vehicle_type != 'Tümü':
                query += " WHERE tip = %s"
                params.append(vehicle_type)
            query += " ORDER BY tip, id"
            result = self.execute_query(query, tuple(params), fetchall=True)
            
        return result