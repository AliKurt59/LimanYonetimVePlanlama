# ui/transport_tab.py (Sürükle-Bırak Kaldırılmış Stabil Versiyon)

from collections import defaultdict
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QLabel, 
    QListWidget, QListWidgetItem, QPushButton, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QMenu ,QDialog
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QBrush, QColor
import qtawesome as qta

from ui.transport_destination_dialog import TransportDestinationDialog 

class TransportTab(QWidget):
    def __init__(self, db_connection, main_window, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        container_panel = QWidget()
        container_layout = QVBoxLayout(container_panel)
        container_layout.addWidget(QLabel("Taşınacak Konteyneri Seçin"))
        self.container_list = QListWidget()
        # Sürükleme özelliği kaldırıldı
        container_layout.addWidget(self.container_list)
        
        vehicle_panel = QWidget()
        vehicle_layout = QVBoxLayout(vehicle_panel)
        vehicle_layout.addWidget(QLabel("Araç Filosu ve Atama"))
        
        # Standart QTreeWidget kullanılıyor
        self.vehicle_tree = QTreeWidget()
        self.vehicle_tree.setHeaderLabels(["Araç", "Durum"])
        self.vehicle_tree.setColumnWidth(0, 200)
        self.vehicle_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.vehicle_tree.customContextMenuRequested.connect(self.open_vehicle_menu)
        vehicle_layout.addWidget(self.vehicle_tree)
        
        self.plan_button = QPushButton(qta.icon('fa5s.cogs', color='white'), " Seçilen Konteynere Araç Ata")
        self.plan_button.setToolTip("Bir konteyner ve boşta bir araç seçerek iş emri oluşturun.")
        self.plan_button.clicked.connect(self.create_transport_plan)
        
        main_panel = QWidget()
        main_layout = QVBoxLayout(main_panel)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.plan_button)
        
        splitter.addWidget(container_panel)
        splitter.addWidget(vehicle_panel)
        splitter.setSizes([400, 500])
        layout.addWidget(main_panel)
        
        self.refresh_lists()

    def create_transport_plan(self):
        selected_container_item = self.container_list.currentItem()
        selected_vehicle_item = self.vehicle_tree.currentItem()

        if not selected_container_item:
            QMessageBox.warning(self.main_window, "Eksik Seçim", "Lütfen sol listeden bir konteyner seçin.")
            return
        if not selected_vehicle_item or selected_vehicle_item.childCount() > 0:
            QMessageBox.warning(self.main_window, "Eksik Seçim", "Lütfen sağdaki listeden bir araç seçin.")
            return

        container_data = selected_container_item.data(Qt.ItemDataRole.UserRole)
        vehicle_data = selected_vehicle_item.data(0, Qt.ItemDataRole.UserRole)

        if vehicle_data['durum'] != 'BOŞTA':
            QMessageBox.warning(self.main_window, "Araç Meşgul", "Lütfen 'BOŞTA' durumunda bir araç seçin.")
            return
            
        self.process_transport_plan(container_data, vehicle_data)

    def process_transport_plan(self, container_data, vehicle_data):
        destination_dialog = TransportDestinationDialog(self.db, container_data, self.main_window)
        if destination_dialog.exec() == QDialog.DialogCode.Accepted:
            selected_destination = destination_dialog.selected_destination
            if not selected_destination:
                return

            dest_type = selected_destination[0]
            current_location = container_data.get('saha_konum')
            if current_location:
                self.db.update_container_yard_location(container_data['id'], None)

            success = False
            operation_message = ""
            if dest_type == 'YARD':
                location_str = selected_destination[1]
                success = self.db.update_container_yard_location(container_data['id'], location_str)
                operation_message = f"Konteyner '{container_data['id']}' sahadaki '{location_str}' konumuna taşındı."
            elif dest_type == 'SHIP':
                ship_id, bay, row, tier = selected_destination[1:]
                success = self.db.add_container_to_ship(container_id=container_data['id'], ship_id=ship_id, row=row, tier=tier, bay_id=bay)
                operation_message = f"Konteyner '{container_data['id']}' gemiye yüklendi."
            
            if success:
                if self.db.assign_vehicle_to_transport(vehicle_data['id'], container_data['id']):
                    QMessageBox.information(self.main_window, "Başarılı", operation_message)
                    self.main_window.refresh_all_tabs()
                else:
                    QMessageBox.critical(self.main_window, "Hata", "İş emri oluşturulamadı.")
            else:
                QMessageBox.critical(self.main_window, "Veritabanı Hatası", "Konteyner taşınamadı.")
                if current_location:
                    self.db.update_container_yard_location(container_data['id'], current_location)
    
    def open_vehicle_menu(self, position: QPoint):
        item = self.vehicle_tree.itemAt(position)
        if not item or item.childCount() > 0:
            return

        vehicle_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not vehicle_data:
            return

        menu = QMenu()
        if vehicle_data['durum'] == 'MEŞGUL':
            complete_action = menu.addAction(qta.icon('fa5s.check-square', color='lightgreen'), "Görevi Tamamla")
            action = menu.exec(self.vehicle_tree.mapToGlobal(position))
            
            if action == complete_action:
                self.complete_task(vehicle_data['id'])
    
    def complete_task(self, vehicle_id):
        reply = QMessageBox.question(self, "Onay", f"'{vehicle_id}' aracının görevini tamamlayıp 'BOŞTA' duruma getirmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.update_vehicle_status(vehicle_id, 'BOŞTA'):
                QMessageBox.information(self, "Başarılı", f"'{vehicle_id}' aracı boşa çıkarıldı.")
                self.main_window.refresh_all_tabs()
            else:
                QMessageBox.critical(self, "Hata", "Araç durumu güncellenemedi.")

    def refresh_lists(self):
        self.container_list.clear()
        containers = self.db.get_all_yard_containers()
        if containers:
            for c in containers:
                item = QListWidgetItem(f"{c['id']} (Yer: {c.get('saha_konum', 'N/A')})")
                item.setData(Qt.ItemDataRole.UserRole, c)
                self.container_list.addItem(item)
            
        self.vehicle_tree.clear()
        vehicles = self.db.get_vehicles()
        if not vehicles: return

        grouped_vehicles = defaultdict(list)
        for v in vehicles:
            grouped_vehicles[v['tip']].append(v)

        for v_type, v_list in sorted(grouped_vehicles.items()):
            parent_item = QTreeWidgetItem(self.vehicle_tree, [v_type])
            parent_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            for v in sorted(v_list, key=lambda x: x['id']):
                is_available = v['durum'] == 'BOŞTA'
                icon = qta.icon('fa5s.check-circle', color='lightgreen') if is_available else qta.icon('fa5s.times-circle', color='#E74C3C')
                child_item = QTreeWidgetItem(parent_item, [v['id'], v['durum']])
                child_item.setIcon(0, icon)
                child_item.setData(0, Qt.ItemDataRole.UserRole, v)
                
                if not is_available:
                    child_item.setForeground(1, QBrush(QColor("#E74C3C")))
                else:
                    child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsSelectable)
        
        self.vehicle_tree.expandAll()