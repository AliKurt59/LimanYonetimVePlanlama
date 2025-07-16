# ui/transport_planning_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QComboBox, QProgressBar, QTextEdit,
                           QTabWidget, QWidget, QFormLayout, QMessageBox, 
                           QGroupBox, QListWidget, QListWidgetItem,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QSplitter, QLineEdit, QSpinBox, QDoubleSpinBox,
                           QCheckBox, QDateTimeEdit, QScrollArea, QApplication)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QDateTime
from PyQt6.QtGui import QFont
import qtawesome as qta
from datetime import datetime, timedelta
import json

class TransportPlanningThread(QThread):
    """Background thread for transport planning operations."""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    operation_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, transport_planner, operation_type, parameters):
        super().__init__()
        self.transport_planner = transport_planner
        self.operation_type = operation_type
        self.parameters = parameters
    
    def run(self):
        try:
            if self.operation_type == 'create_plan':
                self.status_updated.emit("Taşıma planı oluşturuluyor...")
                self.progress_updated.emit(20)
                
                result = self.transport_planner.create_transport_plan(
                    self.parameters.get('cargo_data', []),
                    self.parameters.get('optimization_criteria', 'cost')
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit(result)
                
            elif self.operation_type == 'load_plans':
                self.status_updated.emit("Taşıma planları yükleniyor...")
                self.progress_updated.emit(50)
                
                plans = self.transport_planner.get_transport_plans(
                    self.parameters.get('status_filter')
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit({'success': True, 'plans': plans})
                
            elif self.operation_type == 'load_statistics':
                self.status_updated.emit("Network istatistikleri yükleniyor...")
                self.progress_updated.emit(50)
                
                stats = self.transport_planner.get_network_statistics()
                
                self.progress_updated.emit(100)
                self.operation_completed.emit({'success': True, 'statistics': stats})
                
        except Exception as e:
            self.error_occurred.emit(str(e))

class TransportPlanningDialog(QDialog):
    """Advanced transport planning system dialog."""
    
    def __init__(self, transport_planner, parent=None):
        try:
            super().__init__(parent)
            self.transport_planner = transport_planner
            self.current_plans = []
            self.cargo_items = []
            
            self.setWindowTitle("Gelişmiş Taşıma Planlama Sistemi")
            try:
                self.setWindowIcon(qta.icon('fa5s.route'))
            except Exception:
                pass  # Icon yüklenemezse devam et
                
            self.resize(1200, 800)
            self.setModal(True)
            
            print("🔧 DEBUG: Setting up UI...")
            self.setup_ui()
            print("✅ UI setup completed")
            
            # Bu metodlar çökme sebebi olabilir - güvenli hale getirelim
            try:
                print("🔧 DEBUG: Loading transport plans...")
                self.load_transport_plans()
                print("✅ Transport plans loaded")
            except Exception as e:
                print(f"⚠️  Warning: Could not load transport plans: {e}")
            
            try:
                print("🔧 DEBUG: Loading network statistics...")
                self.load_network_statistics()
                print("✅ Network statistics loaded")
            except Exception as e:
                print(f"⚠️  Warning: Could not load network statistics: {e}")
            
            print("✅ TransportPlanningDialog initialization completed")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"🔧 DEBUG: TransportPlanningDialog error: {e}")
            print(f"🔧 DEBUG: Full traceback: {error_details}")
            
            # Show error in a simple message box
            QMessageBox.critical(parent, "Taşıma Planlama Hatası", 
                f"Dialog açılırken hata oluştu:\n\n{str(e)}")
            raise e  # Re-raise so caller knows it failed

    def setup_ui(self):
        """Setup the main UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Gelişmiş Taşıma Planlama ve Optimizasyon")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(header_label)
        
        # Refresh button
        refresh_btn = QPushButton("Yenile")
        try:
            refresh_btn.setIcon(qta.icon('fa5s.sync-alt'))
        except Exception:
            pass  # Icon yüklenemezse devam et
        refresh_btn.clicked.connect(self.refresh_all_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Plan Creation tab
        create_tab = self.create_plan_creation_tab()
        try:
            self.tabs.addTab(create_tab, qta.icon('fa5s.plus'), "Plan Oluştur")
        except Exception:
            self.tabs.addTab(create_tab, "Plan Oluştur")
        
        # Plan Management tab
        management_tab = self.create_plan_management_tab()
        try:
            self.tabs.addTab(management_tab, qta.icon('fa5s.list'), "Plan Yönetimi")
        except Exception:
            self.tabs.addTab(management_tab, "Plan Yönetimi")
        
        # Network Overview tab
        network_tab = self.create_network_overview_tab()
        try:
            self.tabs.addTab(network_tab, qta.icon('fa5s.network-wired'), "Network Genel Bakış")
        except Exception:
            self.tabs.addTab(network_tab, "Network Genel Bakış")
        
        # Statistics tab
        stats_tab = self.create_statistics_tab()
        try:
            self.tabs.addTab(stats_tab, qta.icon('fa5s.chart-bar'), "İstatistikler")
        except Exception:
            self.tabs.addTab(stats_tab, "İstatistikler")
        
        layout.addWidget(self.tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Hazır")
        layout.addWidget(self.status_label)

    def create_plan_creation_tab(self):
        """Create plan creation tab."""
        print("DEBUG: Creating plan creation tab...")
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            print("DEBUG: Plan creation tab widget and layout created")
            
            # Splitter for cargo items and plan configuration
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Left panel - Cargo Items
            print("DEBUG: Creating cargo panel...")
            left_panel = self.create_cargo_panel()
            splitter.addWidget(left_panel)
            print("DEBUG: Cargo panel created and added")
            
            # Right panel - Plan Configuration
            print("DEBUG: Creating plan config panel...")
            right_panel = self.create_plan_config_panel()
            splitter.addWidget(right_panel)
            print("DEBUG: Plan config panel created and added")
            
            splitter.setSizes([600, 600])
            layout.addWidget(splitter)
            
            # Create plan button
            create_plan_btn = QPushButton("Taşıma Planı Oluştur")
            try:
                create_plan_btn.setIcon(qta.icon('fa5s.cogs'))
            except Exception as e:
                print(f"DEBUG: Could not set icon for create plan button: {e}")
            create_plan_btn.clicked.connect(self.create_transport_plan)
            layout.addWidget(create_plan_btn)
            print("DEBUG: Plan creation tab completed successfully")
            
            return tab
        except Exception as e:
            print(f"ERROR: Failed to create plan creation tab: {e}")
            print(f"ERROR: Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            # Return a simple widget as fallback
            fallback_tab = QWidget()
            fallback_layout = QVBoxLayout(fallback_tab)
            fallback_layout.addWidget(QLabel("Plan oluşturma sekmesi yüklenemedi"))
            return fallback_tab

    def create_cargo_panel(self):
        """Create cargo items panel."""
        print("DEBUG: Creating cargo panel...")
        try:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            
            # Header
            cargo_label = QLabel("Kargo Öğeleri")
            cargo_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(cargo_label)
            
            # Add cargo button
            add_cargo_btn = QPushButton("Kargo Öğesi Ekle")
            try:
                add_cargo_btn.setIcon(qta.icon('fa5s.plus'))
            except Exception as e:
                print(f"DEBUG: Could not set icon for add cargo button: {e}")
            print("DEBUG: Cargo panel created successfully")
            return panel
        except Exception as e:
            print(f"ERROR: Failed to create cargo panel: {e}")
            print(f"ERROR: Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            # Return a simple widget as fallback
            fallback_panel = QWidget()
            fallback_layout = QVBoxLayout(fallback_panel)
            fallback_layout.addWidget(QLabel("Kargo paneli yüklenemedi"))
            return fallback_panel
        add_cargo_btn.clicked.connect(self.add_cargo_item)
        layout.addWidget(add_cargo_btn)
        
        # Cargo list
        self.cargo_list = QListWidget()
        layout.addWidget(self.cargo_list)
        
        # Remove cargo button
        remove_cargo_btn = QPushButton("Seçili Öğeyi Kaldır")
        remove_cargo_btn.setIcon(qta.icon('fa5s.trash'))
        remove_cargo_btn.clicked.connect(self.remove_cargo_item)
        layout.addWidget(remove_cargo_btn)
        
        return panel

    def create_plan_config_panel(self):
        """Create plan configuration panel."""
        print("DEBUG: Creating plan config panel...")
        try:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            
            # Configuration group
            config_group = QGroupBox("Plan Yapılandırması")
            config_layout = QFormLayout(config_group)
            
            # Optimization criteria
            self.optimization_combo = QComboBox()
            self.optimization_combo.addItems(['cost', 'time', 'distance', 'environmental'])
            config_layout.addRow("Optimizasyon Kriteri:", self.optimization_combo)
            
            # Priority handling
            self.priority_check = QCheckBox("Öncelik Tabanlı Planlama")
            self.priority_check.setChecked(True)
            config_layout.addRow(self.priority_check)
            
            # Environmental consideration
            self.environmental_check = QCheckBox("Çevre Etkisini Minimize Et")
            config_layout.addRow(self.environmental_check)
            
            layout.addWidget(config_group)
            print("DEBUG: Plan config panel created successfully")
            return panel
        except Exception as e:
            print(f"ERROR: Failed to create plan config panel: {e}")
            print(f"ERROR: Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            # Return a simple widget as fallback
            fallback_panel = QWidget()
            fallback_layout = QVBoxLayout(fallback_panel)
            fallback_layout.addWidget(QLabel("Plan yapılandırma paneli yüklenemedi"))
            return fallback_panel
        
        # Results display
        results_group = QGroupBox("Plan Sonuçları")
        results_layout = QVBoxLayout(results_group)
        
        self.plan_results_text = QTextEdit()
        self.plan_results_text.setReadOnly(True)
        self.plan_results_text.setMaximumHeight(200)
        results_layout.addWidget(self.plan_results_text)
        
        layout.addWidget(results_group)
        
        layout.addStretch()
        return panel

    def create_plan_management_tab(self):
        """Create plan management tab."""
        print("DEBUG: Creating plan management tab...")
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            # Controls
            controls_layout = QHBoxLayout()
            
            # Status filter
            controls_layout.addWidget(QLabel("Durum Filtresi:"))
            self.status_filter_combo = QComboBox()
            self.status_filter_combo.addItems(['Tümü', 'planned', 'approved', 'in_progress', 'completed', 'cancelled'])
            self.status_filter_combo.currentTextChanged.connect(self.filter_plans)
            controls_layout.addWidget(self.status_filter_combo)
            
            controls_layout.addStretch()
            
            # Refresh plans button
            refresh_plans_btn = QPushButton("Planları Yenile")
            try:
                refresh_plans_btn.setIcon(qta.icon('fa5s.sync'))
            except Exception as e:
                print(f"DEBUG: Could not set icon for refresh plans button: {e}")
            refresh_plans_btn.clicked.connect(self.load_transport_plans)
            controls_layout.addWidget(refresh_plans_btn)
            
            layout.addLayout(controls_layout)
            print("DEBUG: Plan management tab created successfully")
            return tab
        except Exception as e:
            print(f"ERROR: Failed to create plan management tab: {e}")
            print(f"ERROR: Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            # Return a simple widget as fallback
            fallback_tab = QWidget()
            fallback_layout = QVBoxLayout(fallback_tab)
            fallback_layout.addWidget(QLabel("Plan yönetimi sekmesi yüklenemedi"))
            return fallback_tab
        
        # Plans table
        self.plans_table = QTableWidget()
        self.plans_table.setColumnCount(7)
        self.plans_table.setHorizontalHeaderLabels([
            "Plan ID", "Kargo Sayısı", "Toplam Maliyet", "Süre (saat)", 
            "Mesafe (km)", "Durum", "İşlemler"
        ])
        self.plans_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.plans_table)
        
        return tab

    def create_network_overview_tab(self):
        """Create network overview tab."""
        print("DEBUG: Creating network overview tab...")
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            # Network info display
            self.network_info_text = QTextEdit()
            self.network_info_text.setReadOnly(True)
            layout.addWidget(self.network_info_text)
            print("DEBUG: Network overview tab created successfully")
            
            return tab
        except Exception as e:
            print(f"ERROR: Failed to create network overview tab: {e}")
            print(f"ERROR: Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            # Return a simple widget as fallback
            fallback_tab = QWidget()
            fallback_layout = QVBoxLayout(fallback_tab)
            fallback_layout.addWidget(QLabel("Network genel bakış sekmesi yüklenemedi"))
            return fallback_tab

    def create_statistics_tab(self):
        """Create statistics tab."""
        print("DEBUG: Creating statistics tab...")
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            # Statistics display
            self.statistics_text = QTextEdit()
            self.statistics_text.setReadOnly(True)
            layout.addWidget(self.statistics_text)
            print("DEBUG: Statistics tab created successfully")
            
            return tab
        except Exception as e:
            print(f"ERROR: Failed to create statistics tab: {e}")
            print(f"ERROR: Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            # Return a simple widget as fallback
            fallback_tab = QWidget()
            fallback_layout = QVBoxLayout(fallback_tab)
            fallback_layout.addWidget(QLabel("İstatistikler sekmesi yüklenemedi"))
            return fallback_tab

    def add_cargo_item(self):
        """Add a new cargo item."""
        dialog = CargoItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cargo_data = dialog.get_cargo_data()
            self.cargo_items.append(cargo_data)
            
            # Add to list widget
            item_text = f"Konteyner: {cargo_data['container_id']} | Ağırlık: {cargo_data['weight_kg']}kg | {cargo_data['origin_id']} → {cargo_data['destination_id']}"
            self.cargo_list.addItem(item_text)

    def remove_cargo_item(self):
        """Remove selected cargo item."""
        current_row = self.cargo_list.currentRow()
        if current_row >= 0:
            self.cargo_list.takeItem(current_row)
            if current_row < len(self.cargo_items):
                self.cargo_items.pop(current_row)

    def create_transport_plan(self):
        """Create a new transport plan."""
        if not self.cargo_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir kargo öğesi ekleyin.")
            return
        
        optimization_criteria = self.optimization_combo.currentText()
        
        self.start_operation('create_plan', {
            'cargo_data': self.cargo_items,
            'optimization_criteria': optimization_criteria
        })

    def load_transport_plans(self):
        """Load transport plans."""
        try:
            status_filter = None
            try:
                status_filter = self.status_filter_combo.currentText()
                if status_filter == 'Tümü':
                    status_filter = None
            except AttributeError:
                # Combo box not yet created, use default
                pass
            
            self.start_operation('load_plans', {
                'status_filter': status_filter
            })
        except Exception as e:
            print(f"Error in load_transport_plans: {e}")
            # Fallback - set empty plans
            self.update_plans_table([])

    def load_network_statistics(self):
        """Load network statistics."""
        try:
            self.start_operation('load_statistics', {})
        except Exception as e:
            print(f"Error in load_network_statistics: {e}")
            # Fallback - show empty stats

    def filter_plans(self):
        """Filter plans by status."""
        self.load_transport_plans()

    def refresh_all_data(self):
        """Refresh all data."""
        self.load_transport_plans()
        self.load_network_statistics()

    def update_plans_table(self, plans):
        """Update the plans table."""
        self.plans_table.setRowCount(len(plans))
        
        for row, plan in enumerate(plans):
            # Plan ID
            id_item = QTableWidgetItem(plan['id'])
            self.plans_table.setItem(row, 0, id_item)
            
            # Cargo count
            cargo_count_item = QTableWidgetItem(str(plan['cargo_items_count']))
            self.plans_table.setItem(row, 1, cargo_count_item)
            
            # Total cost
            cost_item = QTableWidgetItem(f"${plan['total_cost']:.2f}")
            self.plans_table.setItem(row, 2, cost_item)
            
            # Total time
            time_item = QTableWidgetItem(f"{plan['total_time_hours']:.1f}")
            self.plans_table.setItem(row, 3, time_item)
            
            # Total distance
            distance_item = QTableWidgetItem(f"{plan['total_distance_km']:.1f}")
            self.plans_table.setItem(row, 4, distance_item)
            
            # Status
            status_item = QTableWidgetItem(plan['status'].title())
            self.plans_table.setItem(row, 5, status_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 2, 5, 2)
            
            view_btn = QPushButton("Görüntüle")
            view_btn.setIcon(qta.icon('fa5s.eye'))
            view_btn.clicked.connect(lambda checked, plan_id=plan['id']: self.view_plan_details(plan_id))
            actions_layout.addWidget(view_btn)
            
            if plan['status'] == 'planned':
                approve_btn = QPushButton("Onayla")
                approve_btn.setIcon(qta.icon('fa5s.check'))
                approve_btn.clicked.connect(lambda checked, plan_id=plan['id']: self.update_plan_status(plan_id, 'approved'))
                actions_layout.addWidget(approve_btn)
            
            self.plans_table.setCellWidget(row, 6, actions_widget)
        
        # Adjust column widths
        self.plans_table.resizeColumnsToContents()

    def view_plan_details(self, plan_id):
        """View detailed plan information."""
        QMessageBox.information(self, "Plan Detayları", f"Plan ID: {plan_id}\n\nDetaylar henüz implement edilmedi.")

    def update_plan_status(self, plan_id, new_status):
        """Update plan status."""
        success = self.transport_planner.update_plan_status(plan_id, new_status)
        if success:
            QMessageBox.information(self, "Başarılı", f"Plan durumu '{new_status}' olarak güncellendi.")
            self.load_transport_plans()
        else:
            QMessageBox.warning(self, "Hata", "Plan durumu güncellenemedi.")

    def update_network_info(self, statistics):
        """Update network information display."""
        info_text = f"""
TAŞIMA NETWORK GENEİL BAKIŞ

Düğümler (Nodes):
- Toplam: {statistics['nodes']['total']}
- Türe Göre Dağılım:
"""
        for node_type, count in statistics['nodes']['by_type'].items():
            info_text += f"  • {node_type.title()}: {count}\n"

        info_text += f"""
Rotalar (Routes):
- Toplam: {statistics['routes']['total']}
- Ortalama Mesafe: {statistics['routes']['avg_distance']} km
- Ortalama Maliyet: ${statistics['routes']['avg_cost']:.2f}
- Taşıma Moduna Göre:
"""
        for mode, count in statistics['routes']['by_mode'].items():
            info_text += f"  • {mode.title()}: {count}\n"

        info_text += f"""
Network Kapsamı: {statistics['network_coverage']}%
"""
        self.network_info_text.setText(info_text)

    def update_statistics_display(self, statistics):
        """Update statistics display."""
        stats_text = json.dumps(statistics, indent=2, ensure_ascii=False)
        self.statistics_text.setText(stats_text)

    def start_operation(self, operation_type, parameters):
        """Start background operation."""
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("İşlem başlatılıyor...")
            
            self.operation_thread = TransportPlanningThread(
                self.transport_planner,
                operation_type,
                parameters
            )
            
            self.operation_thread.progress_updated.connect(self.progress_bar.setValue)
            self.operation_thread.status_updated.connect(self.status_label.setText)
            self.operation_thread.operation_completed.connect(self.on_operation_completed)
            self.operation_thread.error_occurred.connect(self.on_error)
            
            self.operation_thread.start()
            
        except Exception as e:
            print(f"Error starting operation {operation_type}: {e}")
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Hata: {str(e)}")

    def on_operation_completed(self, result):
        """Handle operation completion."""
        self.progress_bar.setVisible(False)
        
        if result.get('success', False):
            if 'transport_plan' in result:
                # Plan creation completed
                plan = result['transport_plan']
                self.status_label.setText("Taşıma planı başarıyla oluşturuldu")
                
                plan_text = f"""
Plan ID: {result['plan_id']}
Toplam Maliyet: ${plan['total_cost']:.2f}
Toplam Süre: {plan['total_time_hours']:.1f} saat
Toplam Mesafe: {plan['total_distance_km']:.1f} km
Çevresel Etki: {plan['environmental_impact']['total_co2_kg']:.2f} kg CO2
Durum: {plan['status']}

Rota Sayısı: {len(plan['routes'])}
"""
                self.plan_results_text.setText(plan_text)
                
                QMessageBox.information(self, "Başarılı", "Taşıma planı başarıyla oluşturuldu!")
                self.load_transport_plans()  # Refresh plans list
                
            elif 'plans' in result:
                # Plans loaded
                self.current_plans = result['plans']
                self.update_plans_table(self.current_plans)
                self.status_label.setText(f"{len(self.current_plans)} plan yüklendi")
                
            elif 'statistics' in result:
                # Statistics loaded
                statistics = result['statistics']
                self.update_network_info(statistics)
                self.update_statistics_display(statistics)
                self.status_label.setText("İstatistikler güncellendi")
        else:
            error_msg = result.get('error', 'Bilinmeyen hata')
            self.status_label.setText(f"İşlem başarısız: {error_msg}")
            QMessageBox.warning(self, "Hata", f"İşlem başarısız:\n{error_msg}")

    def on_error(self, error_message):
        """Handle errors."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Hata: {error_message}")
        QMessageBox.critical(self, "Hata", f"İşlem sırasında hata oluştu:\n{error_message}")

    def closeEvent(self, event):
        """Handle dialog close."""
        if hasattr(self, 'operation_thread') and self.operation_thread.isRunning():
            self.operation_thread.terminate()
            self.operation_thread.wait()
        event.accept()


class CargoItemDialog(QDialog):
    """Dialog for adding/editing cargo items."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kargo Öğesi Ekle")
        self.setModal(True)
        self.resize(400, 500)
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Container ID
        self.container_id_edit = QLineEdit()
        self.container_id_edit.setPlaceholderText("CNT001")
        form_layout.addRow("Konteyner ID:", self.container_id_edit)
        
        # Weight
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.1, 50000.0)
        self.weight_spin.setValue(1000.0)
        self.weight_spin.setSuffix(" kg")
        form_layout.addRow("Ağırlık:", self.weight_spin)
        
        # Volume
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.1, 1000.0)
        self.volume_spin.setValue(20.0)
        self.volume_spin.setSuffix(" m³")
        form_layout.addRow("Hacim:", self.volume_spin)
        
        # Cargo type
        self.cargo_type_combo = QComboBox()
        self.cargo_type_combo.addItems(['general', 'hazmat', 'refrigerated', 'fragile', 'bulk'])
        form_layout.addRow("Kargo Türü:", self.cargo_type_combo)
        
        # Priority
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 5)
        self.priority_spin.setValue(3)
        form_layout.addRow("Öncelik (1-5):", self.priority_spin)
        
        # Hazmat
        self.hazmat_check = QCheckBox()
        form_layout.addRow("Tehlikeli Madde:", self.hazmat_check)
        
        # Temperature controlled
        self.temp_controlled_check = QCheckBox()
        form_layout.addRow("Sıcaklık Kontrollü:", self.temp_controlled_check)
        
        # Origin
        self.origin_combo = QComboBox()
        self.origin_combo.addItems(['port_main', 'warehouse_a', 'rail_terminal', 'customer_site_1'])
        form_layout.addRow("Başlangıç:", self.origin_combo)
        
        # Destination
        self.destination_combo = QComboBox()
        self.destination_combo.addItems(['warehouse_a', 'customer_site_1', 'rail_terminal', 'port_main'])
        form_layout.addRow("Hedef:", self.destination_combo)
        
        # Pickup time window
        self.pickup_start_edit = QDateTimeEdit()
        self.pickup_start_edit.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("Teslim Alma Başlangıç:", self.pickup_start_edit)
        
        self.pickup_end_edit = QDateTimeEdit()
        self.pickup_end_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        form_layout.addRow("Teslim Alma Bitiş:", self.pickup_end_edit)
        
        # Delivery time window
        self.delivery_start_edit = QDateTimeEdit()
        self.delivery_start_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        form_layout.addRow("Teslimat Başlangıç:", self.delivery_start_edit)
        
        self.delivery_end_edit = QDateTimeEdit()
        self.delivery_end_edit.setDateTime(QDateTime.currentDateTime().addDays(3))
        form_layout.addRow("Teslimat Bitiş:", self.delivery_end_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Ekle")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def get_cargo_data(self):
        """Get cargo data from form."""
        return {
            'id': f"cargo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'container_id': self.container_id_edit.text(),
            'weight_kg': self.weight_spin.value(),
            'volume_m3': self.volume_spin.value(),
            'cargo_type': self.cargo_type_combo.currentText(),
            'priority': self.priority_spin.value(),
            'hazmat': self.hazmat_check.isChecked(),
            'temperature_controlled': self.temp_controlled_check.isChecked(),
            'origin_id': self.origin_combo.currentText(),
            'destination_id': self.destination_combo.currentText(),
            'pickup_start': self.pickup_start_edit.dateTime().toPython().isoformat(),
            'pickup_end': self.pickup_end_edit.dateTime().toPython().isoformat(),
            'delivery_start': self.delivery_start_edit.dateTime().toPython().isoformat(),
            'delivery_end': self.delivery_end_edit.dateTime().toPython().isoformat()
        }
