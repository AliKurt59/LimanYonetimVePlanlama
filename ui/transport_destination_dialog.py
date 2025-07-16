# ui/transport_destination_dialog.py (Güncel Versiyon)

from collections import defaultdict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QComboBox, QMessageBox, QWidget, QFormLayout 
)
from PyQt6.QtGui import QBrush, QColor, QFont 
from PyQt6.QtCore import Qt, pyqtSignal 

# --- YENİ İMPORT ---
from utils import parse_container_type
# --------------------


# --- Ortak Yerleşim Kuralları ve Veri Çekme Yardımcısı ---
class LocationHelper:
    def __init__(self, db_connection, container_data):
        self.db = db_connection
        self.container_data = container_data
        self.active_size, self.active_is_reefer = parse_container_type(self.container_data['tip'])

    def _is_valid_placement(self, bottom_container_data, target_tier, lowest_placeable_tier_val):
        """
        Bir konteynerin hedef slota yerleştirilip yerleştirilemeyeceğini kontrol eder (yerçekimi, boyut, reefer).
        lowest_placeable_tier_val: Bu kolonda yerleştirilebilecek en alttaki katman numarası (0-indexed).
        """
        is_gravity_ok = (target_tier == lowest_placeable_tier_val)
        if not is_gravity_ok:
            return False, "Yerçekimi Kuralı İhlali (Altı Boş değil veya Üstü Dolu)"

        bottom_size, bottom_is_reefer = parse_container_type(bottom_container_data.get('tip')) if isinstance(bottom_container_data, dict) else (None, None) 
        
        is_size_compatible = True 
        if bottom_size is not None:
            if self.active_size > bottom_size:
                is_size_compatible = False
        
        is_reefer_compatible = True 
        if self.active_is_reefer is True and bottom_is_reefer is False:
            is_reefer_compatible = False
        
        reasons = []
        if not is_size_compatible: reasons.append(f"Boyut Uyumsuzluğu: Aktif {self.active_size}ft, Alt {bottom_size}ft")
        if not is_reefer_compatible: reasons.append("Reefer Uyumsuzluğu")
        
        if reasons:
            return False, ", ".join(reasons)
        return True, "Uygun Slot"


# --- Saha Hedefi Seçim Paneli (Dropdown Menüler ile) ---
class YardSelectionPanel(QWidget):
    location_selected = pyqtSignal(str, tuple) # (dest_type, coords_tuple)

    def __init__(self, db_connection, container_data, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.container_data = container_data
        self.location_helper = LocationHelper(self.db, self.container_data)
        
        self.BLOCKS = [chr(ord('A') + i) for i in range(10)]
        self.BAYS_PER_BLOCK = 10
        self.TIERS_PER_BAY = 7

        self.yard_data = {} # Tüm saha konteynerleri

        self.init_ui()
        self.refresh_data() # Verileri çek

    def init_ui(self):
        main_layout = QFormLayout(self) 
        
        self.block_combo = QComboBox()
        self.block_combo.addItem("Blok Seçin")
        self.block_combo.addItems(self.BLOCKS)
        self.block_combo.currentIndexChanged.connect(self.on_block_selected)
        main_layout.addRow("Blok:", self.block_combo)

        self.bay_combo = QComboBox()
        self.bay_combo.addItem("Sıra Seçin")
        self.bay_combo.setEnabled(False) # Başlangıçta pasif
        self.bay_combo.currentIndexChanged.connect(self.on_bay_selected)
        main_layout.addRow("Sıra (Bay):", self.bay_combo)

        self.tier_combo = QComboBox()
        self.tier_combo.addItem("Kat Seçin")
        self.tier_combo.setEnabled(False) # Başlangıçta pasif
        main_layout.addRow("Kat (Tier):", self.tier_combo)

        self.confirm_button = QPushButton("Bu Slotu Seç")
        self.confirm_button.clicked.connect(self.emit_selection)
        self.confirm_button.setEnabled(False) # Başlangıçta pasif
        main_layout.addRow(self.confirm_button)

    def refresh_data(self):
        all_containers = self.db.get_all_yard_containers()
        self.yard_data = defaultdict(lambda: defaultdict(dict))
        if all_containers:
            for c in all_containers:
                loc = c.get('saha_konum')
                if not loc: continue
                parts = loc.upper().split('-')
                if len(parts) == 3:
                    block, bay, tier_str = parts
                    try:
                        tier = int(tier_str)
                        self.yard_data[block][bay][tier] = c
                    except ValueError:
                        print(f"Uyarı: Geçersiz kat bilgisi '{tier_str}' for container {c['id']}")
        
        self.populate_block_combo() # Veriler çekildikten sonra blokları doldur

    def populate_block_combo(self):
        self.block_combo.blockSignals(True) # Sinyalleri geçici olarak engelle
        self.block_combo.clear()
        self.block_combo.addItem("Blok Seçin")
        self.block_combo.addItems(self.BLOCKS)
        self.block_combo.blockSignals(False)

    def on_block_selected(self):
        self.bay_combo.blockSignals(True)
        self.bay_combo.clear()
        self.bay_combo.addItem("Sıra Seçin")
        self.bay_combo.setEnabled(False)
        self.tier_combo.blockSignals(True) # Katman combo'sunu da sıfırla
        self.tier_combo.clear(); self.tier_combo.addItem("Kat Seçin"); self.tier_combo.setEnabled(False)
        self.tier_combo.blockSignals(False)
        self.confirm_button.setEnabled(False)

        selected_block = self.block_combo.currentText()
        if selected_block == "Blok Seçin":
            return

        for i in range(1, self.BAYS_PER_BLOCK + 1):
            self.bay_combo.addItem(str(i).zfill(2))
        
        self.bay_combo.setEnabled(True)
        self.bay_combo.blockSignals(False)

    def on_bay_selected(self):
        self.tier_combo.blockSignals(True)
        self.tier_combo.clear()
        self.tier_combo.addItem("Kat Seçin")
        self.tier_combo.setEnabled(False)
        self.confirm_button.setEnabled(False)

        selected_block = self.block_combo.currentText()
        selected_bay = self.bay_combo.currentText()
        if selected_bay == "Sıra Seçin":
            return
        
        tiers_in_stack = self.yard_data.get(selected_block, {}).get(selected_bay, {})

        lowest_placeable_tier = 1
        while lowest_placeable_tier in tiers_in_stack and lowest_placeable_tier <= self.TIERS_PER_BAY:
            lowest_placeable_tier += 1

        for tier_num in range(1, self.TIERS_PER_BAY + 1):
            container_at_tier = tiers_in_stack.get(tier_num)
            if container_at_tier: # Kat dolu
                continue # Dolu katları gösterme
            
            bottom_container_data = tiers_in_stack.get(tier_num - 1)
            # Yerleştirme kurallarını LocationHelper üzerinden kontrol et
            is_valid, validation_message = self.location_helper._is_valid_placement(bottom_container_data, tier_num, lowest_placeable_tier)

            if is_valid:
                item_text = f"Kat {str(tier_num).zfill(2)}"
                self.tier_combo.addItem(item_text)

        self.tier_combo.setEnabled(self.tier_combo.count() > 1) # "Kat Seçin" dışında item varsa aktif et
        self.tier_combo.blockSignals(False)
        self.tier_combo.currentIndexChanged.connect(self.on_tier_selected)

    def on_tier_selected(self):
        if self.tier_combo.currentText() != "Kat Seçin":
            self.confirm_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)

    def emit_selection(self):
        selected_block = self.block_combo.currentText()
        selected_bay = self.bay_combo.currentText()
        tier_text = self.tier_combo.currentText().replace("Kat ", "").strip()


        if selected_block == "Blok Seçin" or selected_bay == "Sıra Seçin" or not tier_text:
            QMessageBox.warning(self.parent(), "Eksik Seçim", "Lütfen tüm konum bilgilerini seçin.")
            return

        location_str = f"{selected_block}-{selected_bay}-{tier_text}"
        self.location_selected.emit('YARD', (location_str,))


# --- Gemi Hedefi Seçim Paneli (Dropdown Menüler ile) ---
class ShipSelectionPanel(QWidget):
    location_selected = pyqtSignal(str, tuple) # (dest_type, coords_tuple)

    def __init__(self, db_connection, container_data, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.container_data = container_data
        self.location_helper = LocationHelper(self.db, self.container_data)

        self.BAYS = [] 
        self.ROWS_PER_BAY = 0
        self.TIERS_PER_BAY = 0

        self.current_ship_details = {}
        self.filled_ship_slots = {} 

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        main_layout = QFormLayout(self)
        
        self.ship_combo = QComboBox()
        self.ship_combo.addItem("Gemi Seçin")
        self.ship_combo.currentIndexChanged.connect(self.on_ship_selected_in_dialog)
        main_layout.addRow("Gemi:", self.ship_combo)

        self.bay_combo = QComboBox()
        self.bay_combo.addItem("Bay Seçin")
        self.bay_combo.setEnabled(False) 
        self.bay_combo.currentIndexChanged.connect(self.on_bay_selected)
        main_layout.addRow("Bay:", self.bay_combo)

        self.row_combo = QComboBox()
        self.row_combo.addItem("Sıra Seçin")
        self.row_combo.setEnabled(False)
        self.row_combo.currentIndexChanged.connect(self.on_row_selected)
        main_layout.addRow("Sıra:", self.row_combo)

        self.tier_combo = QComboBox()
        self.tier_combo.addItem("Kat Seçin")
        self.tier_combo.setEnabled(False)
        main_layout.addRow("Kat:", self.tier_combo)

        self.confirm_button = QPushButton("Bu Slotu Seç")
        self.confirm_button.clicked.connect(self.emit_selection)
        self.confirm_button.setEnabled(False)
        main_layout.addRow(self.confirm_button)

    def refresh_data(self):
        ships = self.db.get_all_ships()
        
        self.ship_combo.blockSignals(True)
        self.ship_combo.clear()
        self.ship_combo.addItem("Gemi Seçin")
        
        if not ships:
            self.ship_combo.setEnabled(False)
            QMessageBox.information(self.parent(), "Bilgi", "Veritabanında yüklenecek gemi bulunamadı.")
        else:
            self.ship_combo.setEnabled(True)
            for ship in ships:
                self.ship_combo.addItem(f"{ship['gemi_adi']} ({ship['gemi_id']})", ship['gemi_id'])
            self.ship_combo.setCurrentIndex(0) 
        
        self.ship_combo.blockSignals(False)
        self.on_ship_selected_in_dialog(0)


    def on_ship_selected_in_dialog(self, index):
        if index <= 0: # "Gemi Seçin" veya geçersiz index
            self.current_ship_details = {}
            selected_ship_id = None
        else:
            selected_ship_id = self.ship_combo.itemData(index)
            ships = self.db.get_all_ships()
            self.current_ship_details = next((s for s in ships if s['gemi_id'] == selected_ship_id), {})
            
        if self.current_ship_details:
            self.BAYS = [f"B{str(i).zfill(2)}" for i in range(1, self.current_ship_details.get('toplam_bay_sayisi', 0) + 1)]
            self.ROWS_PER_BAY = self.current_ship_details.get('toplam_sira_sayisi', 0)
            self.TIERS_PER_BAY = self.current_ship_details.get('toplam_kat_sayisi', 0)
            self.filled_ship_slots = self.db.get_all_ship_slots(selected_ship_id)
        else:
            self.BAYS, self.ROWS_PER_BAY, self.TIERS_PER_BAY = [], 0, 0
            self.filled_ship_slots = {}

        self.populate_bay_combo()

        self.bay_combo.setEnabled(bool(self.BAYS))
        self.row_combo.setEnabled(False)
        self.tier_combo.setEnabled(False)
        self.confirm_button.setEnabled(False)

    def populate_bay_combo(self):
        self.bay_combo.blockSignals(True)
        self.bay_combo.clear()
        self.bay_combo.addItem("Bay Seçin")
        self.bay_combo.addItems(self.BAYS)
        self.bay_combo.blockSignals(False)
        self.on_bay_selected()

    def on_bay_selected(self):
        self.row_combo.blockSignals(True)
        self.row_combo.clear()
        self.row_combo.addItem("Sıra Seçin")
        self.tier_combo.clear(); self.tier_combo.addItem("Kat Seçin"); self.tier_combo.setEnabled(False)
        self.confirm_button.setEnabled(False)

        selected_bay = self.bay_combo.currentText()
        if selected_bay == "Bay Seçin":
            self.row_combo.setEnabled(False)
            self.row_combo.blockSignals(False)
            return
        
        for i in range(self.ROWS_PER_BAY):
            self.row_combo.addItem(str(i).zfill(2))
        
        self.row_combo.setEnabled(True)
        self.row_combo.blockSignals(False)

    def on_row_selected(self):
        self.tier_combo.blockSignals(True)
        self.tier_combo.clear()
        self.tier_combo.addItem("Kat Seçin")
        self.confirm_button.setEnabled(False)

        selected_bay = self.bay_combo.currentText()
        selected_row_str = self.row_combo.currentText()
        if selected_row_str == "Sıra Seçin":
            self.tier_combo.setEnabled(False)
            self.tier_combo.blockSignals(False)
            return
        
        selected_row_int = int(selected_row_str)
        current_bay_filled_slots_data = self.filled_ship_slots.get(selected_bay, {})

        lowest_placeable_tier_val = 0
        current_column_filled_tiers_set = {t_val for (r_val, t_val) in current_bay_filled_slots_data.keys() if r_val == selected_row_int}
        while lowest_placeable_tier_val in current_column_filled_tiers_set and lowest_placeable_tier_val < self.TIERS_PER_BAY:
            lowest_placeable_tier_val += 1
        
        for tier_num in range(self.TIERS_PER_BAY):
            coords = (selected_row_int, tier_num)
            if current_bay_filled_slots_data.get(coords):
                continue

            bottom_container_data = current_bay_filled_slots_data.get((selected_row_int, tier_num - 1))
            is_valid, validation_message = self.location_helper._is_valid_placement(bottom_container_data, tier_num, lowest_placeable_tier_val)
            
            if is_valid:
                self.tier_combo.addItem(str(tier_num).zfill(2))

        self.tier_combo.setEnabled(self.tier_combo.count() > 1)
        self.tier_combo.blockSignals(False)
        self.tier_combo.currentIndexChanged.connect(self.on_tier_selected)

    def on_tier_selected(self):
        if self.tier_combo.currentText() != "Kat Seçin":
            self.confirm_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)

    def emit_selection(self):
        selected_bay = self.bay_combo.currentText()
        selected_row_str = self.row_combo.currentText()
        selected_tier_str = self.tier_combo.currentText()
        selected_ship_id = self.ship_combo.itemData(self.ship_combo.currentIndex())

        if selected_bay == "Bay Seçin" or selected_row_str == "Sıra Seçin" or selected_tier_str == "Kat Seçin" or not selected_ship_id:
            QMessageBox.warning(self.parent(), "Eksik Seçim", "Lütfen tüm konum bilgilerini ve bir gemi seçin.")
            return
        
        selected_row_int = int(selected_row_str)
        selected_tier_int = int(selected_tier_str)

        self.location_selected.emit('SHIP', (selected_ship_id, selected_bay, selected_row_int, selected_tier_int))


# --- Ana Taşıma Hedefi Seçim Diyaloğu ---
class TransportDestinationDialog(QDialog):
    def __init__(self, db_connection, container_data, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.container_data = container_data
        self.selected_destination = None
        self.setWindowTitle(f"Hedef Seç: {container_data['id']} ({container_data['tip']})")
        self.setMinimumSize(400, 450) 
        self.setModal(True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        container_info_label = QLabel(f"<b>Konteyner:</b> {self.container_data['id']} ({self.container_data['tip']})")
        main_layout.addWidget(container_info_label)

        self.tab_widget = QTabWidget()
        self.yard_panel = YardSelectionPanel(self.db, self.container_data, self)
        self.ship_panel = ShipSelectionPanel(self.db, self.container_data, self)
        
        self.tab_widget.addTab(self.yard_panel, "Saha Hedefi")
        self.tab_widget.addTab(self.ship_panel, "Gemi Hedefi")
        main_layout.addWidget(self.tab_widget)

        self.yard_panel.location_selected.connect(self.on_location_selected)
        self.ship_panel.location_selected.connect(self.on_location_selected)

        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch(); button_layout.addWidget(self.cancel_button); button_layout.addStretch()
        main_layout.addLayout(button_layout)
    
    def on_location_selected(self, dest_type, coords):
        self.selected_destination = (dest_type,) + coords
        self.accept()