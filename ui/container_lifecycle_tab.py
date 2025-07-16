# ui/container_lifecycle_tab.py
"""
Port Management System - Container Lifecycle Management Tab
Konteyner yaşam döngüsü yönetimi ve izleme arayüzü
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import sys
from datetime import datetime, timedelta


class DataLoadingWorker(QThread):
    """Arka planda veri yükleme worker'ı"""
    data_loaded = pyqtSignal(dict)  # Yüklenen veriyi gönder
    error_occurred = pyqtSignal(str)  # Hata mesajını gönder
    progress_update = pyqtSignal(str)  # İlerleme mesajını gönder
    
    def __init__(self, db_connection, page=1, page_size=100):
        super().__init__()
        self.db_connection = db_connection
        self.page = page
        self.page_size = page_size
        
    def run(self):
        """Arka planda veri yükleme"""
        try:
            data = {}
            
            self.progress_update.emit("🔄 Konteyner sayısı hesaplanıyor...")
            data['total_containers'] = self.db_connection.get_containers_count()
            
            self.progress_update.emit(f"🔄 Konteyner listesi yükleniyor (Sayfa {self.page})...")
            offset = (self.page - 1) * self.page_size
            data['containers'] = self.db_connection.get_all_containers_detailed(
                limit=self.page_size, offset=offset
            )
            
            self.progress_update.emit("🔄 Lifecycle durumları yükleniyor...")
            data['lifecycle_states'] = self.db_connection.get_lifecycle_states()
            
            self.progress_update.emit("🔄 İstatistikler hesaplanıyor...")
            data['statistics'] = self.load_statistics_data()
            
            self.progress_update.emit("🔄 Son aktiviteler yükleniyor...")
            data['recent_activities'] = self.load_recent_activities_data()
            
            self.progress_update.emit("🔄 Durum dağılımı hesaplanıyor...")
            data['state_distribution'] = self.load_state_distribution_data()
            
            self.progress_update.emit("✅ Veri yükleme tamamlandı!")
            self.data_loaded.emit(data)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def load_statistics_data(self):
        """İstatistik verilerini yükle"""
        try:
            stats = {}
            
            # Toplam konteyner sayısı
            containers = self.db_connection.get_all_containers_detailed()
            stats['total_containers'] = len(containers) if containers else 0
            
            # Aktif lifecycle sayısı
            lifecycle_states = self.db_connection.get_lifecycle_states()
            stats['active_lifecycles'] = len(lifecycle_states) if lifecycle_states else 0
            
            # Toplam cycle count
            try:
                total_cycles_result = self.db_connection.execute_query(
                    "SELECT SUM(lifecycle_cycle_count) as total_cycles FROM public.konteynerler", 
                    fetchone=True
                )
                stats['total_cycles'] = total_cycles_result['total_cycles'] if total_cycles_result and total_cycles_result['total_cycles'] else 0
            except:
                stats['total_cycles'] = 0
            
            # En çok kullanılan durum
            try:
                most_used_result = self.db_connection.execute_query("""
                    SELECT cls.state_name, COUNT(*) as count
                    FROM public.konteynerler k
                    LEFT JOIN container_lifecycle_states cls ON k.current_lifecycle_state = cls.id
                    GROUP BY cls.state_name
                    ORDER BY count DESC 
                    LIMIT 1
                """, fetchone=True)
                
                stats['most_used_state'] = most_used_result['state_name'] if most_used_result else 'SAHA'
            except:
                stats['most_used_state'] = 'SAHA'
            
            return stats
        except Exception as e:
            print(f"İstatistik yükleme hatası: {e}")
            return {}
    
    def load_recent_activities_data(self):
        """Son aktiviteleri yükle"""
        try:
            # Gerçek lifecycle history'den son aktiviteleri çek
            recent_activities = self.db_connection.execute_query("""
                SELECT h.*, 
                       from_state.state_name as from_state_name,
                       to_state.state_name as to_state_name
                FROM public.container_lifecycle_history h
                LEFT JOIN container_lifecycle_states from_state ON h.from_state_id = from_state.id
                LEFT JOIN container_lifecycle_states to_state ON h.to_state_id = to_state.id
                ORDER BY h.change_timestamp DESC
                LIMIT 10
            """, fetchall=True)
            
            # Aktiviteleri formatted string olarak döndür
            activities = []
            if recent_activities:
                for activity in recent_activities:
                    container_id = activity.get('container_id', 'N/A')
                    from_state = activity.get('from_state_name', 'N/A')
                    to_state = activity.get('to_state_name', 'N/A')
                    timestamp = activity.get('change_timestamp', 'N/A')
                    
                    # Zaman formatı düzenle
                    if timestamp != 'N/A':
                        try:
                            # Sadece saat:dakika göster
                            time_str = str(timestamp).split(' ')[1][:5]
                            activities.append(f"🔄 {container_id}: {from_state} → {to_state} ({time_str})")
                        except:
                            activities.append(f"🔄 {container_id}: {from_state} → {to_state}")
                    else:
                        activities.append(f"🔄 {container_id}: {from_state} → {to_state}")
            
            return activities
        except Exception as e:
            print(f"Son aktiviteler yükleme hatası: {e}")
            return []
    
    def load_state_distribution_data(self):
        """Durum dağılımını yükle"""
        try:
            # Gerçek durum dağılımını çek - doğru kolon adı: current_lifecycle_state
            distribution = self.db_connection.execute_query("""
                SELECT k.current_lifecycle_state, 
                       cls.state_name,
                       COUNT(*) as count
                FROM public.konteynerler k
                LEFT JOIN container_lifecycle_states cls ON k.current_lifecycle_state = cls.id
                GROUP BY k.current_lifecycle_state, cls.state_name
                ORDER BY count DESC
                LIMIT 5
            """, fetchall=True)
            
            # Dictionary formatında döndür
            state_dist = {}
            if distribution:
                colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']  # Renkler
                for i, dist in enumerate(distribution):
                    state_name = dist.get('state_name', 'N/A')
                    count = dist.get('count', 0)
                    color = colors[i % len(colors)]  # Renk döngüsü
                    state_dist[state_name] = {'count': count, 'color': color}
            
            return state_dist
        except Exception as e:
            print(f"Durum dağılımı yükleme hatası: {e}")
            return {}

class ContainerLifecycleTab(QWidget):
    def __init__(self, db_connection):
        super().__init__()
        self.db_connection = db_connection
        self.data_worker = None
        
        # Pagination vars
        self.current_page = 1
        self.total_pages = 1
        
        self.init_ui()
        
        # UI tamamlandıktan sonra veri yüklemeyi başlat
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.load_data_async)  # 100ms sonra çalıştır
        
    def init_ui(self):
        """UI bileşenlerini oluştur"""
        # YENİ: Minimum boyut ayarla
        self.setMinimumSize(1200, 700)
        
        layout = QVBoxLayout()
        
        # Başlık
        title = QLabel("📦 Konteyner Yaşam Döngüsü Yönetimi")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px 0px;")
        layout.addWidget(title)
        
        # Yükleniyor mesajı
        self.loading_label = QLabel("🔄 Veriler yükleniyor...")
        self.loading_label.setStyleSheet("color: #3498db; font-size: 14px; margin: 10px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Ana içerik (başlangıçta gizli)
        self.main_content_widget = QWidget()
        self.main_content_widget.setVisible(False)
        
        main_content = QHBoxLayout(self.main_content_widget)
        
        # Sol panel - Konteyner listesi ve arama
        left_panel = self.create_left_panel()
        main_content.addLayout(left_panel, 1)
        
        # Orta panel - Lifecycle timeline
        center_panel = self.create_center_panel()
        main_content.addLayout(center_panel, 2)
        
        # Sağ panel - State management
        right_panel = self.create_right_panel()
        main_content.addLayout(right_panel, 1)
        
        layout.addWidget(self.main_content_widget)
        
        # Alt panel - İstatistikler
        self.bottom_panel = self.create_bottom_panel()
        self.bottom_panel.setVisible(False)
        layout.addWidget(self.bottom_panel)
        
        self.setLayout(layout)
    
    def create_left_panel(self):
        """Sol panel - Konteyner arama ve listesi"""
        layout = QVBoxLayout()
        
        # Arama grubu
        search_group = QGroupBox("🔍 Konteyner Arama")
        search_layout = QVBoxLayout()
        
        # Arama kutusu
        search_frame = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Konteyner ID ile ara...")
        self.search_input.textChanged.connect(self.filter_containers)
        
        search_btn = QPushButton("🔍")
        search_btn.setMaximumWidth(35)
        search_btn.clicked.connect(self.search_container)
        
        search_frame.addWidget(self.search_input)
        search_frame.addWidget(search_btn)
        search_layout.addLayout(search_frame)
        
        # Durum filtresi
        status_frame = QHBoxLayout()
        status_frame.addWidget(QLabel("Durum:"))
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tümü", "ATANMAMIS", "SAHA", "GEMI"])
        self.status_filter.currentTextChanged.connect(self.filter_containers)
        status_frame.addWidget(self.status_filter)
        
        search_layout.addLayout(status_frame)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Konteyner listesi
        list_group = QGroupBox("📋 Konteyner Listesi")
        list_layout = QVBoxLayout()
        
        # Sayfalama kontrolleri
        pagination_frame = QHBoxLayout()
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500"])
        self.page_size_combo.setCurrentText("100")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        
        self.prev_page_btn = QPushButton("◀ Önceki")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)
        
        self.page_label = QLabel("Sayfa 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_page_btn = QPushButton("Sonraki ▶")
        self.next_page_btn.clicked.connect(self.next_page)
        
        pagination_frame.addWidget(QLabel("Sayfa boyutu:"))
        pagination_frame.addWidget(self.page_size_combo)
        pagination_frame.addStretch()
        pagination_frame.addWidget(self.prev_page_btn)
        pagination_frame.addWidget(self.page_label)
        pagination_frame.addWidget(self.next_page_btn)
        
        list_layout.addLayout(pagination_frame)
        
        self.container_list = QTableWidget()
        self.container_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.container_list.itemSelectionChanged.connect(self.on_container_selected)
        
        # Tablo başlıkları
        self.container_list.setColumnCount(5)
        self.container_list.setHorizontalHeaderLabels(["ID", "Tip", "Durum", "Lifecycle", "Cycle Count"])
        
        # Kolon genişlikleri
        header = self.container_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        list_layout.addWidget(self.container_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Pagination vars
        self.current_page = 1
        self.total_pages = 1
        
        return layout
    
    def create_center_panel(self):
        """Orta panel - Lifecycle timeline"""
        layout = QVBoxLayout()
        
        # Timeline grubu
        timeline_group = QGroupBox("📈 Konteyner Yaşam Döngüsü Timeline")
        timeline_layout = QVBoxLayout()
        
        # Kullanım kılavuzu
        help_label = QLabel("💡 <b>Nasıl Kullanılır:</b> Soldaki listeden konteyner seçin → Aşağıdan yeni durum seçin → 'Durum Değiştir' butonuna basın")
        help_label.setStyleSheet("background-color: #e8f5e8; padding: 8px; border-radius: 4px; color: #2c3e50;")
        help_label.setWordWrap(True)
        timeline_layout.addWidget(help_label)
        
        # Seçili konteyner bilgisi
        self.selected_container_label = QLabel("Konteyner seçiniz...")
        self.selected_container_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin: 5px;")
        timeline_layout.addWidget(self.selected_container_label)
        
        # Timeline scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)
        
        self.timeline_widget = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_widget)
        
        scroll_area.setWidget(self.timeline_widget)
        timeline_layout.addWidget(scroll_area)
        
        # Yeni state ekleme
        add_state_frame = QHBoxLayout()
        add_state_frame.addWidget(QLabel("Yeni Durum:"))
        
        self.new_state_combo = QComboBox()
        self.load_lifecycle_states()
        add_state_frame.addWidget(self.new_state_combo)
        
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Değişiklik sebebi (opsiyonel)")
        add_state_frame.addWidget(self.reason_input)
        
        self.add_state_btn = QPushButton("✅ Durum Değiştir")
        self.add_state_btn.clicked.connect(self.change_container_state)
        self.add_state_btn.setEnabled(False)
        add_state_frame.addWidget(self.add_state_btn)
        
        timeline_layout.addLayout(add_state_frame)
        timeline_group.setLayout(timeline_layout)
        layout.addWidget(timeline_group)
        
        return layout
    
    def create_right_panel(self):
        """Sağ panel - State management"""
        layout = QVBoxLayout()
        
        # State'ler grubu
        states_group = QGroupBox("🏷️ Lifecycle Durumları")
        states_layout = QVBoxLayout()
        
        # State listesi
        self.states_list = QTableWidget()
        self.states_list.setColumnCount(3)
        self.states_list.setHorizontalHeaderLabels(["Durum", "Renk", "Aktif"])
        
        # Kolon genişlikleri
        header = self.states_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        states_layout.addWidget(self.states_list)
        
        # State yönetim butonları
        state_buttons = QHBoxLayout()
        
        add_state_btn = QPushButton("➕ Yeni")
        add_state_btn.clicked.connect(self.add_new_state)
        state_buttons.addWidget(add_state_btn)
        
        edit_state_btn = QPushButton("✏️ Düzenle")
        edit_state_btn.clicked.connect(self.edit_state)
        state_buttons.addWidget(edit_state_btn)
        
        states_layout.addLayout(state_buttons)
        states_group.setLayout(states_layout)
        layout.addWidget(states_group)
        
        # Hızlı istatistikler
        stats_group = QGroupBox("📊 Hızlı İstatistikler")
        stats_layout = QVBoxLayout()
        
        self.stats_labels = {}
        stat_names = ["Toplam Konteyner", "Aktif Lifecycle", "Son 24 Saat Değişim", "En Çok Kullanılan Durum"]
        
        for stat_name in stat_names:
            stat_frame = QHBoxLayout()
            stat_frame.addWidget(QLabel(f"{stat_name}:"))
            
            stat_label = QLabel("0")
            stat_label.setStyleSheet("font-weight: bold; color: #27ae60;")
            stat_frame.addWidget(stat_label)
            stat_frame.addStretch()
            
            self.stats_labels[stat_name] = stat_label
            stats_layout.addLayout(stat_frame)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        return layout
    
    def create_bottom_panel(self):
        """Alt panel - Genel istatistikler"""
        print(f"🔧 DEBUG: create_bottom_panel çağrıldı")
        
        stats_group = QGroupBox("📈 Lifecycle İstatistikleri")
        layout = QHBoxLayout()
        
        # State dağılımı
        state_dist_layout = QVBoxLayout()
        state_dist_layout.addWidget(QLabel("Durum Dağılımı:"))
        
        # ScrollArea yerine direkt widget kullan
        self.state_distribution_widget = QWidget()
        self.state_distribution_widget.setStyleSheet("QWidget { background-color: #1e1e1e; border: 1px solid #555; }")
        self.state_distribution_widget.setMinimumHeight(120)
        self.state_distribution_widget.setMaximumHeight(150)
        self.state_distribution_layout = QVBoxLayout(self.state_distribution_widget)
        self.state_distribution_layout.setContentsMargins(5, 5, 5, 5)
        self.state_distribution_layout.setSpacing(3)
        
        # Debug: Başlangıçta test verileri ekle
        print(f"🔧 DEBUG: state_distribution_layout oluşturuldu, test verisi ekleniyor")
        test_label = QLabel("📊 TEST WIDGET ÇALIŞIYOR!")
        test_label.setStyleSheet("color: yellow; font-size: 16px; background-color: red; padding: 10px; border: 2px solid white;")
        test_label.setMinimumHeight(30)
        self.state_distribution_layout.addWidget(test_label)
        
        test_label2 = QLabel("🔄 VERİ YÜKLENİYOR...")
        test_label2.setStyleSheet("color: white; font-size: 14px; background-color: blue; padding: 8px; border: 1px solid cyan;")
        test_label2.setMinimumHeight(25)
        self.state_distribution_layout.addWidget(test_label2)
        
        # Test durum ekle
        test_state = QLabel("■ TEST DURUM: 999 adet")
        test_state.setStyleSheet("color: lime; font-size: 13px; background-color: purple; padding: 5px; border: 1px solid green;")
        test_state.setMinimumHeight(20)
        self.state_distribution_layout.addWidget(test_state)
        
        # Widget'ı layout'a direkt ekle
        state_dist_layout.addWidget(self.state_distribution_widget)
        
        layout.addLayout(state_dist_layout, 1)
        
        # Günlük aktivite
        activity_layout = QVBoxLayout()
        activity_layout.addWidget(QLabel("Son Aktiviteler:"))
        
        self.activity_list = QListWidget()
        self.activity_list.setMaximumHeight(150)
        
        # Debug: Başlangıçta test verileri ekle
        print(f"🔧 DEBUG: activity_list oluşturuldu, test verisi ekleniyor")
        self.activity_list.addItem("📋 Test: Activity widget çalışıyor")
        self.activity_list.addItem("🔄 Test: Veri yükleme bekleniyor...")
        
        activity_layout.addWidget(self.activity_list)
        
        layout.addLayout(activity_layout, 1)
        
        # Yenileme butonu
        refresh_layout = QVBoxLayout()
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.clicked.connect(self.load_data_async)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        
        layout.addLayout(refresh_layout)
        
        stats_group.setLayout(layout)
        
        print(f"🔧 DEBUG: Alt panel oluşturuldu")
        print(f"   activity_list oluşturuldu: {self.activity_list is not None}")
        print(f"   state_distribution_layout oluşturuldu: {self.state_distribution_layout is not None}")
        
        return stats_group
    
    def load_data_async(self):
        """Asenkron veri yükleme başlat"""
        if self.data_worker is not None:
            self.data_worker.terminate()
            self.data_worker.wait()
        
        # Sayfalama parametreleri - güvenli erişim
        try:
            page_size = int(self.page_size_combo.currentText())
        except:
            page_size = 100  # Default değer
        
        self.data_worker = DataLoadingWorker(
            self.db_connection, 
            page=self.current_page, 
            page_size=page_size
        )
        self.data_worker.data_loaded.connect(self.on_data_loaded)
        self.data_worker.error_occurred.connect(self.on_loading_error)
        self.data_worker.progress_update.connect(self.on_progress_update)
        
        # Loading UI'yi göster - güvenli erişim
        try:
            self.loading_label.setVisible(True)
            self.progress_bar.setVisible(True)
        except:
            pass
        
        self.data_worker.start()
        
    def on_progress_update(self, message):
        """İlerleme mesajını güncelle"""
        self.loading_label.setText(message)
    
    def on_data_loaded(self, data):
        """Veri yükleme tamamlandığında"""
        try:
            # UI bileşenlerini göster
            self.loading_label.setVisible(False)
            self.progress_bar.setVisible(False)
            self.main_content_widget.setVisible(True)
            self.bottom_panel.setVisible(True)
            
            # Sayfalama kontrollerini güncelle
            total_containers = data.get('total_containers', 0)
            self.update_pagination_controls(total_containers)
            
            # Verileri UI'ye yükle
            self.populate_containers(data.get('containers', []))
            self.populate_lifecycle_states(data.get('lifecycle_states', []))
            self.populate_statistics(data.get('statistics', {}))
            self.populate_recent_activities(data.get('recent_activities', []))
            self.populate_state_distribution(data.get('state_distribution', {}))
            
            # Alt panelin görünürlüğünü kontrol et
            print(f"🔧 DEBUG: Alt panel görünürlük kontrolü")
            print(f"   bottom_panel var mı: {hasattr(self, 'bottom_panel')}")
            if hasattr(self, 'bottom_panel'):
                print(f"   bottom_panel görünür mü: {self.bottom_panel.isVisible()}")
                print(f"   activity_list var mı: {hasattr(self, 'activity_list')}")
                print(f"   state_distribution_layout var mı: {hasattr(self, 'state_distribution_layout')}")
            
            print(f"✅ Container Lifecycle Tab veri yükleme tamamlandı! (Sayfa {self.current_page}, Toplam: {total_containers})")
            
        except Exception as e:
            self.on_loading_error(f"Veri işleme hatası: {e}")
    
    def on_loading_error(self, error_message):
        """Yükleme hatası durumunda"""
        self.loading_label.setText(f"❌ Hata: {error_message}")
        self.progress_bar.setVisible(False)
        
        # Hata durumunda temel UI'yi göster
        self.main_content_widget.setVisible(True)
        self.bottom_panel.setVisible(True)
        
        QMessageBox.warning(self, "Veri Yükleme Hatası", f"Veriler yüklenirken hata oluştu:\n{error_message}")
    
    def load_data(self):
        """Eski senkron veri yükleme (yedek)"""
        self.load_data_async()
    
    def populate_containers(self, containers):
        """Konteyner listesini doldur"""
        try:
            print(f"🔧 DEBUG: populate_containers called with {len(containers) if containers else 0} containers")
            
            if not containers:
                print("❌ Konteyner listesi boş!")
                # Boş durum mesajı göster
                self.container_list.setRowCount(1)
                empty_item = QTableWidgetItem("Henüz konteyner bulunmuyor")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.container_list.setItem(0, 0, empty_item)
                self.container_list.setSpan(0, 0, 1, 5)  # Tüm sütunları kapsasın
                return
            
            self.container_list.setRowCount(len(containers))
            
            for row, container in enumerate(containers):
                # ID
                self.container_list.setItem(row, 0, QTableWidgetItem(str(container['id'])))
                
                # Tip
                self.container_list.setItem(row, 1, QTableWidgetItem(str(container['tip'])))
                
                # Durum
                self.container_list.setItem(row, 2, QTableWidgetItem(str(container['durum'])))
                
                # Lifecycle state
                lifecycle_state = container.get('lifecycle_state_name', 'N/A')
                lifecycle_item = QTableWidgetItem(lifecycle_state)
                
                # Renk kodlaması
                if container.get('lifecycle_color'):
                    try:
                        lifecycle_item.setBackground(QColor(container['lifecycle_color']))
                    except:
                        pass
                
                self.container_list.setItem(row, 3, lifecycle_item)
                
                # Cycle Count
                cycle_count = container.get('lifecycle_cycle_count', 0)
                cycle_item = QTableWidgetItem(str(cycle_count))
                cycle_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.container_list.setItem(row, 4, cycle_item)
            
            print(f"✅ {len(containers)} konteyner listesi dolduruldu")
                
        except Exception as e:
            print(f"❌ Konteyner listesi doldurma hatası: {e}")
            import traceback
            traceback.print_exc()
    
    def populate_lifecycle_states(self, states):
        """Lifecycle state'lerini doldur"""
        try:
            # Combo box'ı doldur
            self.new_state_combo.clear()
            for state in states:
                self.new_state_combo.addItem(state['state_description'], state['id'])
            
            # Tablo'yu doldur
            self.states_list.setRowCount(len(states))
            
            for row, state in enumerate(states):
                # Durum adı
                self.states_list.setItem(row, 0, QTableWidgetItem(state['state_description']))
                
                # Renk
                color_item = QTableWidgetItem("")
                if state.get('color_code'):
                    color_item.setBackground(QColor(state['color_code']))
                self.states_list.setItem(row, 1, color_item)
                
                # Aktif durumu
                active_item = QTableWidgetItem("✅" if state['is_active'] else "❌")
                self.states_list.setItem(row, 2, active_item)
                
        except Exception as e:
            print(f"Lifecycle states doldurma hatası: {e}")
    
    def populate_statistics(self, stats):
        """İstatistikleri doldur"""
        try:
            # İstatistik widget'larını bul ve doldur
            if hasattr(self, 'stats_labels') and self.stats_labels:
                # Mevcut labels varsa doldur
                if 'Toplam Konteyner' in self.stats_labels:
                    self.stats_labels['Toplam Konteyner'].setText(str(stats.get('total_containers', 0)))
                if 'Aktif Lifecycle' in self.stats_labels:
                    self.stats_labels['Aktif Lifecycle'].setText(str(stats.get('active_lifecycles', 0)))
                if 'Son 24 Saat Değişim' in self.stats_labels:
                    self.stats_labels['Son 24 Saat Değişim'].setText(str(stats.get('total_cycles', 0)))
                if 'En Çok Kullanılan Durum' in self.stats_labels:
                    self.stats_labels['En Çok Kullanılan Durum'].setText(str(stats.get('most_used_state', 'SAHA')))
            else:
                # İstatistik widget'ları yoksa sadece log'la
                print(f"📊 İstatistikler: {stats}")
                
        except Exception as e:
            print(f"İstatistikler doldurma hatası: {e}")
            print(f"📊 İstatistikler: {stats}")  # Debug için
    
    def populate_recent_activities(self, activities):
        """Son aktiviteleri doldur"""
        try:
            print(f"🔧 DEBUG: populate_recent_activities çağrıldı, {len(activities) if activities else 0} aktivite")
            
            # Activity list widget'ını bul ve doldur
            if hasattr(self, 'activity_list') and self.activity_list:
                print(f"🔧 DEBUG: activity_list widget'ı bulundu")
                self.activity_list.clear()
                
                if activities:
                    print(f"🔧 DEBUG: {len(activities)} aktivite ekleniyor")
                    for i, activity in enumerate(activities):
                        print(f"🔧 DEBUG: Aktivite {i+1}: {activity}")
                        self.activity_list.addItem(activity)
                    print(f"🔧 DEBUG: Aktiviteler başarıyla eklendi")
                else:
                    print(f"🔧 DEBUG: Aktivite yok, placeholder ekleniyor")
                    self.activity_list.addItem("🔍 Henüz aktivite yok")
            else:
                # Activity list yoksa sadece log'la
                print(f"🔧 DEBUG: activity_list widget'ı bulunamadı!")
                print(f"📋 Son Aktiviteler: {len(activities) if activities else 0} aktivite")
                if activities:
                    for i, activity in enumerate(activities[:5], 1):
                        print(f"   {i}. {activity}")
                        
        except Exception as e:
            print(f"❌ Son aktiviteler doldurma hatası: {e}")
            print(f"📋 Son Aktiviteler: {len(activities) if activities else 0} aktivite")
    
    def populate_state_distribution(self, distribution):
        """Durum dağılımını doldur"""
        try:
            print(f"🔧 DEBUG: populate_state_distribution çağrıldı, {len(distribution) if distribution else 0} durum")
            print(f"🔧 DEBUG: Distribution data: {distribution}")
            
            # State distribution widget'ını bul ve doldur
            if hasattr(self, 'state_distribution_layout') and self.state_distribution_layout:
                print(f"🔧 DEBUG: state_distribution_layout widget'ı bulundu")
                
                # Mevcut widget'ları temizle (test verileri dahil)
                widget_count_before = self.state_distribution_layout.count()
                print(f"🔧 DEBUG: Temizleme öncesi widget sayısı: {widget_count_before}")
                
                while self.state_distribution_layout.count():
                    child = self.state_distribution_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                print(f"🔧 DEBUG: Mevcut widget'lar temizlendi")
                
                # Yeni dağılım ekle
                if distribution:
                    print(f"🔧 DEBUG: {len(distribution)} durum ekleniyor")
                    
                    for i, (state_name, data) in enumerate(distribution.items()):
                        count = data.get('count', 0)
                        color = data.get('color', '#999')
                        
                        print(f"🔧 DEBUG: Durum {i+1} ekleniyor: {state_name} - {count} adet ({color})")
                        
                        # Container widget oluştur
                        container_widget = QWidget()
                        container_widget.setStyleSheet(f"background-color: {color}; margin: 2px; padding: 10px; border: 2px solid white;")
                        container_widget.setFixedHeight(60)
                        
                        dist_frame = QVBoxLayout(container_widget)
                        
                        # Durum adı
                        state_label = QLabel(state_name)
                        state_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
                        state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        dist_frame.addWidget(state_label)
                        
                        # Sayısı
                        count_label = QLabel(str(count))
                        count_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
                        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        dist_frame.addWidget(count_label)
                        
                        # Layout'a ekle
                        self.state_distribution_layout.addWidget(container_widget)
                        print(f"🔧 DEBUG: Widget eklendi: {state_name} - {count} adet")
                    
                    # Widget sayısını kontrol et
                    widget_count_after = self.state_distribution_layout.count()
                    print(f"🔧 DEBUG: Ekleme sonrası widget sayısı: {widget_count_after}")
                    print(f"🔧 DEBUG: Tüm durumlar başarıyla eklendi")
                else:
                    print(f"🔧 DEBUG: Dağılım verisi yok, placeholder ekleniyor")
                    # Veri yoksa placeholder
                    no_data_label = QLabel("📊 Veri yükleniyor...")
                    no_data_label.setStyleSheet("color: #999; font-size: 12px; background-color: #444; padding: 10px;")
                    self.state_distribution_layout.addWidget(no_data_label)
                    
                # Widget'ı force update et
                if hasattr(self, 'state_distribution_widget'):
                    self.state_distribution_widget.update()
                    self.state_distribution_widget.repaint()
                    print(f"🔧 DEBUG: Widget update/repaint çağrıldı")
                    
            else:
                # Widget yoksa sadece log'la
                print(f"🔧 DEBUG: state_distribution_layout widget'ı bulunamadı!")
                print(f"📊 Durum Dağılımı: {len(distribution) if distribution else 0} durum")
                if distribution:
                    for state_name, data in distribution.items():
                        count = data.get('count', 0)
                        print(f"   {state_name}: {count} adet")
                        
        except Exception as e:
            print(f"❌ Durum dağılımı doldurma hatası: {e}")
            print(f"📊 Durum Dağılımı: {len(distribution) if distribution else 0} durum")
            import traceback
            traceback.print_exc()
    
    def load_lifecycle_states(self):
        """Lifecycle state'lerini combo box'a yükle - eksik metod"""
        try:
            states = self.db_connection.get_lifecycle_states()
            self.new_state_combo.clear()
            
            for state in states:
                self.new_state_combo.addItem(state['state_description'], state['id'])
                
        except Exception as e:
            print(f"Lifecycle states yükleme hatası: {e}")
    
    # ...existing code...
    
    def on_container_selected(self):
        """Konteyner seçildiğinde"""
        current_row = self.container_list.currentRow()
        if current_row >= 0:
            container_id = self.container_list.item(current_row, 0).text()
            self.selected_container_label.setText(f"📦 Seçili Konteyner: {container_id}")
            self.add_state_btn.setEnabled(True)
            self.load_container_timeline(container_id)
        else:
            self.selected_container_label.setText("Konteyner seçiniz...")
            self.add_state_btn.setEnabled(False)
            self.clear_timeline()
    
    def load_container_timeline(self, container_id):
        """Konteyner timeline'ını yükle"""
        try:
            # Timeline'ı temizle
            self.clear_timeline()
            
            # History'yi al
            history = self.db_connection.get_container_lifecycle_history(container_id)
            
            if not history:
                no_history_label = QLabel("🔍 Bu konteyner için lifecycle geçmişi bulunamadı.")
                no_history_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 20px;")
                self.timeline_layout.addWidget(no_history_label)
                return
            
            # Timeline item'larını oluştur
            for i, item in enumerate(history):
                timeline_item = self.create_timeline_item(item, i == 0)
                self.timeline_layout.addWidget(timeline_item)
                
            self.timeline_layout.addStretch()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Timeline yüklenirken hata: {e}")
    
    def create_timeline_item(self, history_item, is_current=False):
        """Timeline item widget'ı oluştur"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {'#3498db' if is_current else '#bdc3c7'};
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
                background-color: {'#ecf0f1' if is_current else '#ffffff'};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        
        # Başlık
        title_layout = QHBoxLayout()
        
        # State badge
        state_badge = QLabel(history_item['to_state_name'])
        state_badge.setStyleSheet(f"""
            background-color: {history_item.get('color_code', '#95a5a6')};
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: bold;
        """)
        title_layout.addWidget(state_badge)
        
        if is_current:
            current_badge = QLabel("📍 GÜNCEL")
            current_badge.setStyleSheet("color: #e74c3c; font-weight: bold;")
            title_layout.addWidget(current_badge)
        
        title_layout.addStretch()
        
        # Zaman
        time_label = QLabel(history_item['change_timestamp'].strftime("%d/%m/%Y %H:%M"))
        time_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        title_layout.addWidget(time_label)
        
        layout.addLayout(title_layout)
        
        # Detaylar
        if history_item.get('from_state_name'):
            change_label = QLabel(f"➡️ {history_item['from_state_name']} → {history_item['to_state_name']}")
        else:
            change_label = QLabel(f"🆕 İlk durum: {history_item['to_state_name']}")
        
        change_label.setStyleSheet("margin: 5px 0px;")
        layout.addWidget(change_label)
        
        # Sebep
        if history_item.get('change_reason'):
            reason_label = QLabel(f"💬 Sebep: {history_item['change_reason']}")
            reason_label.setStyleSheet("font-style: italic; color: #34495e;")
            layout.addWidget(reason_label)
        
        # Değiştiren kişi
        if history_item.get('changed_by'):
            user_label = QLabel(f"👤 Değiştiren: {history_item['changed_by']}")
            user_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            layout.addWidget(user_label)
        
        return frame
    
    def clear_timeline(self):
        """Timeline'ı temizle"""
        while self.timeline_layout.count():
            child = self.timeline_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def change_container_state(self):
        """Konteyner durumunu değiştir"""
        current_row = self.container_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir konteyner seçin.")
            return
        
        container_id = self.container_list.item(current_row, 0).text()
        new_state_id = self.new_state_combo.currentData()
        reason = self.reason_input.text().strip()
        
        print(f"🔧 DEBUG: Container ID: {container_id}")  # Debug
        print(f"🔧 DEBUG: New state ID: {new_state_id}")  # Debug
        print(f"🔧 DEBUG: Reason: {reason}")  # Debug
        
        # Combo box debug
        print(f"🔧 DEBUG: Combo box item count: {self.new_state_combo.count()}")
        for i in range(self.new_state_combo.count()):
            print(f"   {i}: {self.new_state_combo.itemText(i)} -> {self.new_state_combo.itemData(i)}")
        
        if not new_state_id:
            # Eğer data None ise, index kullan
            current_index = self.new_state_combo.currentIndex()
            if current_index >= 0:
                # States listesinden ID al
                try:
                    states = self.db_connection.get_lifecycle_states()
                    if states and current_index < len(states):
                        new_state_id = states[current_index]['id']
                        print(f"🔧 DEBUG: Using index-based state ID: {new_state_id}")
                    else:
                        QMessageBox.warning(self, "Uyarı", "Durum listesi yüklenemedi.")
                        return
                except Exception as e:
                    QMessageBox.warning(self, "Uyarı", f"Durum listesi hatası: {e}")
                    return
            else:
                QMessageBox.warning(self, "Uyarı", "Lütfen yeni bir durum seçin.")
                return
        
        # Onay al
        state_name = self.new_state_combo.currentText()
        reply = QMessageBox.question(
            self, 
            "Durum Değişikliği Onayı", 
            f"Konteyner {container_id} durumunu '{state_name}' olarak değiştirmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                print(f"🔧 DEBUG: Calling change_container_lifecycle_state...")  # Debug
                success = self.db_connection.change_container_lifecycle_state(
                    container_id, new_state_id, reason, "USER"
                )
                print(f"🔧 DEBUG: Database result: {success}")  # Debug
                
                if success:
                    QMessageBox.information(self, "Başarılı", "Konteyner durumu başarıyla değiştirildi.")
                    self.reason_input.clear()
                    self.load_data_async()
                    self.load_container_timeline(container_id)
                else:
                    QMessageBox.warning(self, "Hata", "Durum değişikliği başarısız oldu.\n\nVeritabanı işlemi tamamlanamadı.")
                    
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"🔧 DEBUG: Exception occurred: {e}")
                print(f"🔧 DEBUG: Full traceback: {error_details}")
                QMessageBox.critical(self, "Hata", f"Durum değişikliği sırasında hata oluştu:\n\n{str(e)}")
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"🔧 DEBUG: Exception occurred: {e}")
                print(f"🔧 DEBUG: Full traceback: {error_details}")
                QMessageBox.critical(self, "Hata", f"Durum değiştirme hatası:\n\n{str(e)}\n\nDetaylı hata konsola yazdırıldı.")
                
        print(f"🔧 DEBUG: Change container state completed")  # Debug
    
    def filter_containers(self):
        """Konteyner listesini filtrele"""
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.container_list.rowCount()):
            should_show = True
            
            # Metin araması
            if search_text:
                container_id = self.container_list.item(row, 0).text().lower()
                if search_text not in container_id:
                    should_show = False
            
            # Durum filtresi
            if should_show and status_filter != "Tümü":
                container_status = self.container_list.item(row, 2).text()
                if container_status != status_filter:
                    should_show = False
            
            self.container_list.setRowHidden(row, not should_show)
    
    def search_container(self):
        """Konteyner ara ve seç"""
        search_text = self.search_input.text().strip()
        if not search_text:
            return
        
        # Listeyi temizle ve ara
        self.filter_containers()
        
        # İlk görünen satırı seç
        for row in range(self.container_list.rowCount()):
            if not self.container_list.isRowHidden(row):
                self.container_list.selectRow(row)
                break
    
    def load_statistics(self):
        """İstatistikleri yükle"""
        try:
            # Toplam konteyner
            containers = self.db_connection.get_all_containers_detailed()
            total_containers = len(containers) if containers else 0
            self.stats_labels["Toplam Konteyner"].setText(str(total_containers))
            
            # Aktif lifecycle state sayısı
            states = self.db_connection.get_lifecycle_states()
            active_states = len([s for s in states if s['is_active']]) if states else 0
            self.stats_labels["Aktif Lifecycle"].setText(str(active_states))
            
            # Toplam cycle count hesapla
            try:
                total_cycles_result = self.db_connection.execute_query(
                    "SELECT SUM(lifecycle_cycle_count) as total_cycles FROM public.konteynerler", 
                    fetchone=True
                )
                total_cycles = total_cycles_result['total_cycles'] if total_cycles_result and total_cycles_result['total_cycles'] else 0
                self.stats_labels["Son 24 Saat Değişim"].setText(str(total_cycles))
            except:
                self.stats_labels["Son 24 Saat Değişim"].setText("0")
            
            # En çok kullanılan durum
            try:
                most_used_result = self.db_connection.execute_query("""
                    SELECT current_lifecycle_state, COUNT(*) as count 
                    FROM public.konteynerler 
                    GROUP BY current_lifecycle_state 
                    ORDER BY count DESC 
                    LIMIT 1
                """, fetchone=True)
                
                if most_used_result:
                    state_id = most_used_result['current_lifecycle_state']
                    state_name = self.db_connection._get_state_name(state_id)
                    self.stats_labels["En Çok Kullanılan Durum"].setText(state_name)
                else:
                    self.stats_labels["En Çok Kullanılan Durum"].setText("SAHA")
            except:
                self.stats_labels["En Çok Kullanılan Durum"].setText("SAHA")
            
        except Exception as e:
            print(f"İstatistik yükleme hatası: {e}")
    
    def load_recent_activities(self):
        """Son aktiviteleri yükle"""
        try:
            self.activity_list.clear()
            
            # Placeholder aktiviteler (gerçek query eklenebilir)
            activities = [
                "🔄 CONT123456 durumu SAHA olarak değiştirildi",
                "➕ CONT789012 yeni lifecycle başlatıldı", 
                "✅ CONT345678 DELIVERED durumuna geçti",
                "📦 CONT901234 CUSTOMS_CLEARED durumunda",
                "🚢 CONT567890 gemiye yüklendi"
            ]
            
            for activity in activities:
                self.activity_list.addItem(activity)
                
        except Exception as e:
            print(f"Aktivite yükleme hatası: {e}")
    
    def load_state_distribution(self):
        """Durum dağılımını yükle"""
        try:
            # State distribution widget'ı temizle
            while self.state_distribution_layout.count():
                child = self.state_distribution_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Placeholder dağılım (gerçek query eklenebilir)
            distribution = [
                ("SAHA", 45, "#3498db"),
                ("GEMI", 30, "#2ecc71"),
                ("ATANMAMIS", 15, "#f39c12"),
                ("CUSTOMS_PENDING", 10, "#e67e22")
            ]
            
            for state_name, count, color in distribution:
                dist_frame = QHBoxLayout()
                
                # Renk göstergesi
                color_label = QLabel("■")
                color_label.setStyleSheet(f"color: {color}; font-size: 16px;")
                dist_frame.addWidget(color_label)
                
                # State adı ve sayısı
                text_label = QLabel(f"{state_name}: {count}")
                dist_frame.addWidget(text_label)
                
                dist_frame.addStretch()
                
                self.state_distribution_layout.addLayout(dist_frame)
                
        except Exception as e:
            print(f"Dağılım yükleme hatası: {e}")
    
    def add_new_state(self):
        """Yeni lifecycle state ekle"""
        # Basit dialog (geliştirilmesi gerekebilir)
        state_name, ok = QInputDialog.getText(self, "Yeni Durum", "Durum adı:")
        if ok and state_name.strip():
            QMessageBox.information(self, "Bilgi", "Bu özellik henüz geliştirilme aşamasındadır.")
    
    def edit_state(self):
        """Lifecycle state düzenle"""
        current_row = self.states_list.currentRow()
        if current_row >= 0:
            QMessageBox.information(self, "Bilgi", "Bu özellik henüz geliştirilme aşamasındadır.")
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir durum seçin.")

    def on_page_size_changed(self):
        """Sayfa boyutu değiştiğinde"""
        self.current_page = 1
        self.load_data_async()
    
    def prev_page(self):
        """Önceki sayfa"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data_async()
    
    def next_page(self):
        """Sonraki sayfa"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_data_async()
    
    def update_pagination_controls(self, total_containers):
        """Sayfalama kontrollerini güncelle"""
        page_size = int(self.page_size_combo.currentText())
        self.total_pages = max(1, (total_containers + page_size - 1) // page_size)
        
        self.page_label.setText(f"Sayfa {self.current_page} / {self.total_pages}")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)


if __name__ == "__main__":
    # Test için
    app = QApplication(sys.argv)
    
    # Mock database connection
    class MockDB:
        def get_all_containers_detailed(self):
            return []
        def get_lifecycle_states(self):
            return []
        def get_container_lifecycle_history(self, container_id):
            return []
        def change_container_lifecycle_state(self, container_id, new_state_id, reason, changed_by):
            return True
    
    window = ContainerLifecycleTab(MockDB())
    window.show()
    
    sys.exit(app.exec())
