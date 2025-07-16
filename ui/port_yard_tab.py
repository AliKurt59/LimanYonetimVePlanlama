# ui/port_yard_tab.py (Doğru Ortalama Metoduyla Düzeltilmiş Tam Hali)

import copy
from collections import defaultdict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QLabel, QPushButton, QGraphicsSimpleTextItem, QDialog, 
    QFormLayout, QListWidget, QListWidgetItem, QMessageBox, QDialogButtonBox, QMenu
)
from PyQt6.QtGui import QBrush, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QRectF, QPoint

import qtawesome as qta
import config_manager
from utils import parse_container_type
from ui.common.dialogs import ContainerDetailDialog
from ui.common.widgets import InteractiveRectItem

class PlacementDialog(QDialog):
    # Bu sınıf aynı kalıyor
    def __init__(self, containers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yerleştirmek İçin Konteyner Seçin")
        self.selected_container = None
        layout = QVBoxLayout(self)
        self.container_list = QListWidget()
        for c in containers:
            item_text = f"{c['id']} ({c['tip']}) -> {c.get('varis_limani', 'N/A')}"
            item = QListWidgetItem(item_text); item.setData(Qt.ItemDataRole.UserRole, c)
            self.container_list.addItem(item)
        layout.addWidget(self.container_list)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject)
        layout.addWidget(button_box); self.container_list.itemDoubleClicked.connect(self.accept)
    def accept(self):
        if self.container_list.currentItem():
            self.selected_container = self.container_list.currentItem().data(Qt.ItemDataRole.UserRole)
            super().accept()
        else: QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen bir konteyner seçin.")

class RelocationDialog(QDialog):
    # Bu sınıf aynı kalıyor
    def __init__(self, target_slots, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Taşıma Hedefi Seçin")
        self.selected_slot = None
        layout = QVBoxLayout(self)
        self.slot_list = QListWidget()
        for slot in target_slots:
            item = QListWidgetItem(f"Blok: {slot[0]}, Sıra: {slot[1]}, Kat: {slot[2]}")
            item.setData(Qt.ItemDataRole.UserRole, slot)
            self.slot_list.addItem(item)
        layout.addWidget(self.slot_list)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject)
        layout.addWidget(button_box); self.slot_list.itemDoubleClicked.connect(self.accept)
    def accept(self):
        if self.slot_list.currentItem():
            self.selected_slot = self.slot_list.currentItem().data(Qt.ItemDataRole.UserRole)
            super().accept()
        else: QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen bir hedef slot seçin.")

class PortYardTab(QWidget):
    def __init__(self, db_connection, main_window, parent=None):
        super().__init__(parent)
        self.db, self.main_window = db_connection, main_window
        self.BLOCKS = [chr(ord('A') + i) for i in range(10)]; self.BAYS_PER_BLOCK, self.TIERS_PER_BAY = 10, 7
        self.current_view, self.current_block, self.current_bay = 'BLOCKS', None, None
        self.yard_data, self.unassigned_containers = {}, []
        self.pending_placement, self.active_relocation_container = {}, None
        self.init_ui()

    def init_ui(self):
        # YENİ: Minimum boyut ayarla
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout(self); header_layout = QHBoxLayout()
        self.back_button = QPushButton(qta.icon('fa5s.arrow-left', color='white'), " Geri"); self.back_button.clicked.connect(self.go_back); self.back_button.setVisible(False)
        header_layout.addWidget(self.back_button)
        self.title_label = QLabel("Liman Saha Planı"); self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold)); self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label, 1); layout.addLayout(header_layout)
        
        self.scene = QGraphicsScene()
        # DÜZELTME: Standart QGraphicsView'e geri dönüldü
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(self.view.renderHints().Antialiasing)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.open_slot_menu)
        layout.addWidget(self.view)
        
        self.legend_widget = QWidget()
        legend_layout = QHBoxLayout(self.legend_widget)
        legend_layout.addStretch()
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("reefer"), "Reefer"))
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("filled"), "Standart"))
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("pending"), "Beklemede"))
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("placeable"), "Uygun Slot"))
        legend_layout.addStretch()
        layout.addWidget(self.legend_widget)
        
        action_button_layout = QHBoxLayout()
        self.confirm_button = QPushButton(qta.icon('fa5s.check', color='lightgreen'), " Onayla"); self.cancel_button = QPushButton(qta.icon('fa5s.times', color='red'), " İptal")
        self.confirm_button.clicked.connect(self.confirm_actions); self.cancel_button.clicked.connect(self.cancel_actions)
        action_button_layout.addStretch(); action_button_layout.addWidget(self.cancel_button); action_button_layout.addWidget(self.confirm_button); action_button_layout.addStretch()
        self.action_widget = QWidget(); self.action_widget.setLayout(action_button_layout); self.action_widget.setVisible(False)
        layout.addWidget(self.action_widget); self.refresh_view()

    def _create_legend_item(self, color, text):
        widget = QWidget(); layout = QHBoxLayout(widget); color_label = QLabel(); color_label.setFixedSize(15, 15)
        color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid white;")
        layout.addWidget(color_label); layout.addWidget(QLabel(text)); layout.setContentsMargins(0,0,0,0)
        return widget

    def _get_container_color(self, container):
        return config_manager.get_color("reefer") if "REEFER" in container.get('tip', '').upper() else config_manager.get_color("filled")

    ### YENİ: Sahneyi ortalayan doğru yardımcı metod ###
    def _center_scene_contents(self):
        """Çizim sonrası sahnedeki tüm elemanların merkezini görünümün ortasına alır (zum yapmadan)."""
        if not self.scene.items():
            return
        # Tüm elemanların merkez noktasını bul
        center_point = self.scene.itemsBoundingRect().center()
        # Görünümü bu noktaya ortala
        self.view.centerOn(center_point)

    def get_fullness_color(self, fullness):
        if fullness <= 30: return QColor("#2ecc71")
        elif fullness <= 70: return QColor("#f1c40f")
        else: return QColor("#c0392b")

    def refresh_view(self):
        if not self.db.conn: return
        self.unassigned_containers = self.db.get_unassigned_containers() or []
        all_containers = self.db.get_all_yard_containers() or []
        self.yard_data = defaultdict(lambda: defaultdict(dict))
        for c in all_containers:
            loc = c.get('saha_konum')
            if loc and isinstance(loc, str):
                parts = loc.upper().split('-')
                if len(parts) == 3:
                    try: self.yard_data[parts[0]][parts[1]][int(parts[2])] = c
                    except (ValueError, IndexError): continue
        self.update_display()

    def update_display(self):
        self.scene.clear()
        self.action_widget.setVisible(bool(self.pending_placement or self.active_relocation_container))
        self.legend_widget.setVisible(self.current_view == 'TIERS')

        if self.current_view == 'BLOCKS': self.title_label.setText("Liman Saha Planı - Blok Görünümü"); self.back_button.setVisible(False); self.draw_block_view()
        elif self.current_view == 'BAYS': self.title_label.setText(f"Blok {self.current_block} - Sıra (Bay) Görünümü"); self.back_button.setVisible(True); self.draw_bay_view()
        elif self.current_view == 'TIERS':
            title = f"Blok {self.current_block}, Sıra {self.current_bay} - Kat Görünümü"
            if self.active_relocation_container: title = f"TAŞIMA: {self.active_relocation_container['id']} için yeni hedef seçin"
            self.title_label.setText(title); self.back_button.setVisible(True); self.draw_tier_view()

        ### DÜZELTME: Her çizimden sonra doğru ortalama fonksiyonunu çağır ###
        self._center_scene_contents()

    def draw_block_view(self):
        cols, w, h = 5, 150, 150
        for i, block_id in enumerate(self.BLOCKS):
            r, c = divmod(i, cols)
            block_containers = sum(len(bay) for bay in self.yard_data.get(block_id, {}).values())
            total = self.BAYS_PER_BLOCK * self.TIERS_PER_BAY
            fullness = (block_containers / total) * 100 if total > 0 else 0
            rect = InteractiveRectItem(c * (w + 20), r * (h + 20), w, h); rect.setBrush(QBrush(self.get_fullness_color(fullness))); rect.setPen(QPen(Qt.PenStyle.NoPen))
            rect.setData(0, {'type': 'block', 'id': block_id}); rect.clicked.connect(self.handle_item_click)
            rect.setToolTip(f"Blok {block_id}\nDolu: {block_containers}/{total}\nOran: {fullness:.1f}%"); self.scene.addItem(rect)
            text = QGraphicsSimpleTextItem(block_id); text.setFont(QFont("Arial", 48, QFont.Weight.Bold)); text.setPos(rect.boundingRect().center() - text.boundingRect().center()); text.setParentItem(rect)

    def draw_bay_view(self):
        cols, w, h = 5, 120, 120
        for i in range(self.BAYS_PER_BLOCK):
            bay_id = f"{(i + 1):02d}"; r, c = divmod(i, cols)
            bay_containers = len(self.yard_data.get(self.current_block, {}).get(bay_id, {}))
            total = self.TIERS_PER_BAY
            fullness = (bay_containers / total) * 100 if total > 0 else 0
            rect = InteractiveRectItem(c * (w + 20), r * (h + 20), w, h); rect.setBrush(QBrush(self.get_fullness_color(fullness))); rect.setPen(QPen(Qt.PenStyle.NoPen))
            rect.setData(0, {'type': 'bay', 'id': bay_id}); rect.clicked.connect(self.handle_item_click)
            rect.setToolTip(f"Sıra (Bay) {bay_id}\nDolu: {bay_containers}/{total}\nOran: {fullness:.1f}%"); self.scene.addItem(rect)
            text = QGraphicsSimpleTextItem(f"Sıra\n{bay_id}"); text.setFont(QFont("Arial", 24, QFont.Weight.Bold)); text.setPos(rect.boundingRect().center() - text.boundingRect().center()); text.setParentItem(rect)
            
    def draw_tier_view(self):
        w, h = 100, 50
        display_tiers = self.yard_data.get(self.current_block, {}).get(self.current_bay, {}).copy()
        if self.pending_placement:
            plan = self.pending_placement
            if plan['type'] == 'RELOCATION':
                from_loc = plan['from_loc'].split('-')
                if from_loc[0] == self.current_block and from_loc[1] == self.current_bay and int(from_loc[2]) in display_tiers:
                    del display_tiers[int(from_loc[2])]
            to_coords = plan.get('coords') or plan.get('to_coords')
            if to_coords and to_coords[0] == self.current_block and to_coords[1] == self.current_bay:
                display_tiers[int(to_coords[2])] = plan['container']
        lowest_placeable_tier = 1
        while lowest_placeable_tier in display_tiers: lowest_placeable_tier += 1
        for i in range(self.TIERS_PER_BAY):
            tier_num, y_pos = i + 1, (self.TIERS_PER_BAY - 1 - i) * (h + 10)
            
            # <<< YENİ/DEĞİŞEN SATIRLAR BAŞLANGICI >>>
            # "Kat XX" etiketini slotların sol tarafına ekle
            tier_label = QGraphicsSimpleTextItem(f"Kat {tier_num:02d}")
            tier_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            tier_label.setBrush(QBrush(Qt.GlobalColor.white))
            # Etiketi dikey olarak ortala ve slotların soluna yerleştir
            label_y = y_pos + (h / 2) - (tier_label.boundingRect().height() / 2)
            tier_label.setPos(-70, label_y) # X pozisyonu slotların solunda olacak şekilde ayarlandı
            self.scene.addItem(tier_label)

            rect = InteractiveRectItem(0, y_pos, w, h)
            container = display_tiers.get(tier_num)
            is_placeable = (tier_num == lowest_placeable_tier) and not container

            if container:
                is_pending = self.pending_placement.get('container', {}).get('id') == container.get('id')
                color = config_manager.get_color("pending") if is_pending else self._get_container_color(container)
                tooltip = f"ID: {container.get('id')}"
                
                # Slotun içine sadece Konteyner ID'sini yaz
                id_text = QGraphicsSimpleTextItem(container.get('id', 'HATA'))
                id_text.setFont(QFont("Arial", 10, QFont.Weight.Bold)) # Tek satır olduğu için font biraz büyütüldü
                id_text.setBrush(QBrush(Qt.GlobalColor.white))
                id_text.setPos(rect.boundingRect().center() - id_text.boundingRect().center())
                id_text.setParentItem(rect)
            else:
                color = config_manager.get_color("placeable") if is_placeable else config_manager.get_color("empty")
                tooltip = "Uygun Slot" if is_placeable else "Yerleştirilemez"
            
            rect.setBrush(QBrush(color))
            rect.setPen(QPen(Qt.PenStyle.NoPen))
            rect.setData(0, {'type': 'tier', 'id': str(tier_num), 'filled': bool(container), 'placeable': is_placeable})
            rect.setToolTip(tooltip)
            rect.clicked.connect(self.handle_item_click)
            self.scene.addItem(rect)
            # <<< YENİ/DEĞİŞEN SATIRLAR BİTİŞİ >>>

    def handle_item_click(self, data):
        if data['type'] in ('block', 'bay'):
            self.current_block = data['id'] if data['type'] == 'block' else self.current_block
            self.current_bay = data['id'] if data['type'] == 'bay' else None
            self.current_view = 'BAYS' if data['type'] == 'block' else 'TIERS'
            self.cancel_actions()
        elif data['type'] == 'tier' and data.get('placeable'):
            if self.active_relocation_container: 
                coords = (self.current_block, self.current_bay, data['id'])
                self.pending_placement = {
                    'type': 'RELOCATION', 
                    'from_loc': self.active_relocation_container['saha_konum'], 
                    'to_coords': coords, 
                    'container': self.active_relocation_container
                }
                self.active_relocation_container = None
                self.update_display()
            else: self.show_placement_dialog(data)

    def open_slot_menu(self, position: QPoint):
        item = self.view.itemAt(position)
        if not (item and isinstance(item, InteractiveRectItem)): return
        data = item.data(0)
        if not (data and data['type'] == 'tier' and data['filled']): return
        container = self.yard_data.get(self.current_block, {}).get(self.current_bay, {}).get(int(data['id']))
        if not container: return
        menu = QMenu(); 
        menu.addAction("Detayları Göster").triggered.connect(lambda: self.show_container_details(container))
        move_action = menu.addAction("Bu Konteyneri Taşı")
        if self.is_container_movable(container): move_action.triggered.connect(lambda: self.start_relocation_dialog(container))
        else: move_action.setEnabled(False); move_action.setToolTip("Üstü dolu olan bir konteyner taşınamaz.")
        menu.exec(self.view.mapToGlobal(position))
                
    def is_container_movable(self, container):
        loc = container.get('saha_konum')
        if not loc: return False
        try:
            block, bay, tier_str = loc.split('-'); tier = int(tier_str)
            return not self.yard_data.get(block, {}).get(bay, {}).get(tier + 1)
        except (ValueError, IndexError): return False

    def show_container_details(self, container_data):
        if not container_data: return
        ContainerDetailDialog(container_data, container_data.get('saha_konum', 'Bilinmiyor'), self).exec()

    def show_placement_dialog(self, slot_data):
        bottom_container = self.yard_data.get(self.current_block, {}).get(self.current_bay, {}).get(int(slot_data['id']) - 1)
        req_size, req_is_reefer = parse_container_type(bottom_container.get('tip')) if bottom_container else (None, None)
        suitable_containers = []
        for c in self.unassigned_containers:
            c_size, c_is_reefer = parse_container_type(c['tip'])
            size_ok = (req_size is None) or (c_size == req_size)
            reefer_ok = (req_is_reefer is None) or (c_is_reefer == req_is_reefer)
            if size_ok and reefer_ok: suitable_containers.append(c)
        if not suitable_containers:
            QMessageBox.information(self, "Bilgi", "Bu slota yerleştirmek için kurallara uygun (aynı boyut ve tipte) atanmamış bir konteyner bulunamadı.")
            return
        dialog = PlacementDialog(suitable_containers, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_container:
            coords = (self.current_block, self.current_bay, slot_data['id'])
            self.pending_placement = {'type': 'NEW_PLACEMENT', 'coords': coords, 'container': dialog.selected_container}
            self.update_display()

    def start_relocation_dialog(self, container_to_relocate):
        self.cancel_actions()
        target_slots = self.find_suitable_relocation_slots(container_to_relocate)
        if not target_slots:
            QMessageBox.warning(self, "Uygun Yer Yok", "Bu konteyneri taşımak için sahada kurallara uygun boş bir yer bulunamadı.")
            return
        dialog = RelocationDialog(target_slots, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_slot:
            self.pending_placement = {'type': 'RELOCATION', 'from_loc': container_to_relocate['saha_konum'], 'to_coords': dialog.selected_slot, 'container': container_to_relocate}
            self.update_display()
            
    def find_suitable_relocation_slots(self, container_to_move):
        suitable_slots = []
        c_size, c_is_reefer = parse_container_type(container_to_move['tip'])
        from_loc_str = container_to_move.get('saha_konum')
        if not from_loc_str: return []
        
        temp_yard_data = copy.deepcopy(self.yard_data)
        from_block, from_bay, from_tier_str = from_loc_str.split('-')
        if int(from_tier_str) in temp_yard_data.get(from_block, {}).get(from_bay, {}):
            del temp_yard_data[from_block][from_bay][int(from_tier_str)]
        for block_id in self.BLOCKS:
            for i in range(self.BAYS_PER_BLOCK):
                bay_id = f"{(i+1):02d}"
                stack = temp_yard_data.get(block_id, {}).get(bay_id, {})
                lowest_placeable_tier = 1
                while lowest_placeable_tier in stack: lowest_placeable_tier += 1
                if lowest_placeable_tier > self.TIERS_PER_BAY: continue
                bottom_container = stack.get(lowest_placeable_tier - 1)
                req_size, req_is_reefer = parse_container_type(bottom_container.get('tip')) if bottom_container else (None, None)
                size_ok = (req_size is None) or (c_size == req_size)
                reefer_ok = (req_is_reefer is None) or (c_is_reefer == req_is_reefer)
                if size_ok and reefer_ok:
                    new_slot_tuple = (block_id, bay_id, str(lowest_placeable_tier))
                    if f"{new_slot_tuple[0]}-{new_slot_tuple[1]}-{new_slot_tuple[2]}" != from_loc_str:
                        suitable_slots.append(new_slot_tuple)
        return suitable_slots

    def confirm_actions(self):
        if not self.pending_placement: return
        container = self.pending_placement['container']
        coords = self.pending_placement.get('coords') or self.pending_placement.get('to_coords')
        new_loc = f"{coords[0]}-{coords[1]}-{coords[2]}"
        if self.db.update_container_yard_location(container['id'], new_loc):
            QMessageBox.information(self, "Başarılı", "İşlem başarıyla kaydedildi.")
            self.main_window.refresh_all_tabs()
        else:
            QMessageBox.critical(self, "Hata", "İşlem sırasında bir veritabanı hatası oluştu.")
        self.cancel_actions()

    def cancel_actions(self):
        self.pending_placement, self.active_relocation_container = {}, None
        self.refresh_view()

    def go_back(self):
        self.cancel_actions()
        if self.current_view == 'TIERS': self.current_view = 'BAYS'; self.current_bay = None
        elif self.current_view == 'BAYS': self.current_view = 'BLOCKS'; self.current_block = None
        self.update_display()