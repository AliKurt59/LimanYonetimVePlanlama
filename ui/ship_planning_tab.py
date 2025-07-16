# ui/ship_planning_tab.py (Çökme Sorunu Giderilmiş Son Hali)
from collections import defaultdict
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QPushButton, QMessageBox, QFormLayout,QLineEdit, QGraphicsSimpleTextItem,
    QMenu, QComboBox, QFrame
)
from PyQt6.QtGui import QFont, QBrush, QColor, QPen
from PyQt6.QtCore import Qt, QRectF, QPoint

import qtawesome as qta
import config_manager
from utils import parse_container_type
from ui.common.dialogs import ContainerDetailDialog
from ui.common.widgets import InteractiveRectItem

class ShipPlanningTab(QWidget):
    def __init__(self, db_connection, main_window, parent=None):
        super().__init__(parent)
        self.db = db_connection; self.main_window = main_window
        self.BAYS, self.ROWS_PER_BAY, self.TIERS_PER_BAY = [], 0, 0
        self.current_view, self.current_bay = 'OVERVIEW', None
        self.all_loadable_containers, self.pending_placements = [], {}
        self.filled_ship_slots = {} 
        self.active_container_for_placement = None
        self.active_relocation_container, self.pending_relocation_from_coords = None, None
        self.current_ship_id, self.current_ship_details = None, {}
        self.init_ui()

    def init_ui(self):
        # YENİ: Minimum boyut ayarla
        self.setMinimumSize(1000, 600)
        
        main_layout = QHBoxLayout(self); splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel)
        ship_selection_layout = QHBoxLayout()
        ship_selection_layout.addWidget(QLabel("Gemi Seç:"))
        self.ship_combo = QComboBox(); self.ship_combo.currentIndexChanged.connect(self.on_ship_selected)
        ship_selection_layout.addWidget(self.ship_combo); left_layout.addLayout(ship_selection_layout)
        filter_frame = QFrame(); filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        filter_layout = QFormLayout(filter_frame)
        filter_layout.addRow(QLabel("<b>Filtrele:</b>"))
        self.type_filter_combo = QComboBox(); self.dest_filter_combo = QComboBox()
        filter_layout.addRow("Konteyner Tipi:", self.type_filter_combo); filter_layout.addRow("Varış Limanı:", self.dest_filter_combo)
        self.type_filter_combo.currentIndexChanged.connect(self._filter_and_populate_list)
        self.dest_filter_combo.currentIndexChanged.connect(self._filter_and_populate_list)
        left_layout.addWidget(filter_frame)
        left_layout.addWidget(QLabel("Yüklenecek Konteyneri Seçin"))
        self.container_list = QListWidget(); self.container_list.itemClicked.connect(self.on_container_selected_for_planning)
        left_layout.addWidget(self.container_list)
        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel)
        header_layout = QHBoxLayout()
        self.back_button = QPushButton(qta.icon('fa5s.arrow-left', color='white'), " Geri"); self.back_button.clicked.connect(self.go_back); self.back_button.setVisible(False)
        header_layout.addWidget(self.back_button)
        self.title_label = QLabel("Gemi Planlama"); self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold)); self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label, 1); right_layout.addLayout(header_layout)
        self.scene = QGraphicsScene(); self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(self.view.renderHints().Antialiasing)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.open_slot_menu)
        right_layout.addWidget(self.view)
        legend_layout = QHBoxLayout(); legend_layout.addStretch()
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("reefer"), "Reefer"))
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("filled"), "Standart"))
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("pending"), "Beklemede"))
        legend_layout.addWidget(self._create_legend_item(config_manager.get_color("placeable"), "Uygun Slot"))
        legend_layout.addStretch(); right_layout.addLayout(legend_layout)
        action_button_layout = QHBoxLayout()
        self.confirm_button = QPushButton(qta.icon('fa5s.check', color='lightgreen'), " Planı Onayla"); self.confirm_button.clicked.connect(self.confirm_actions)
        self.cancel_button = QPushButton(qta.icon('fa5s.times', color='red'), " İptal"); self.cancel_button.clicked.connect(self.cancel_actions)
        action_button_layout.addStretch(); action_button_layout.addWidget(self.cancel_button); action_button_layout.addWidget(self.confirm_button); action_button_layout.addStretch()
        self.action_widget = QWidget(); self.action_widget.setLayout(action_button_layout); self.action_widget.setVisible(False)
        right_layout.addWidget(self.action_widget)
        splitter.addWidget(left_panel); splitter.addWidget(right_panel); splitter.setSizes([350, 900]); main_layout.addWidget(splitter)
        self.refresh_all()
    def _create_legend_item(self, color, text):
        widget = QWidget(); layout = QHBoxLayout(widget); color_label = QLabel(); color_label.setFixedSize(15, 15)
        color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid white;"); layout.addWidget(color_label); layout.addWidget(QLabel(text)); layout.setContentsMargins(0,0,0,0)
        return widget
    def refresh_all(self):
        if not self.db.conn: return
        self.all_loadable_containers = self.db.get_all_loadable_containers() or []
        self._populate_filters(); self._populate_ship_combo()
    def _populate_filters(self):
        self.type_filter_combo.blockSignals(True); self.dest_filter_combo.blockSignals(True)
        self.type_filter_combo.clear(); self.dest_filter_combo.clear()
        self.type_filter_combo.addItem("Tüm Tipler"); self.dest_filter_combo.addItem("Tüm Limanlar")
        types = sorted(list(set(c['tip'] for c in self.all_loadable_containers))); dests = sorted(list(set(c.get('varis_limani') for c in self.all_loadable_containers if c.get('varis_limani'))))
        self.type_filter_combo.addItems(types); self.dest_filter_combo.addItems(dests)
        self.type_filter_combo.blockSignals(False); self.dest_filter_combo.blockSignals(False)
    def _filter_and_populate_list(self):
        self.container_list.clear()
        selected_type = self.type_filter_combo.currentText(); selected_dest = self.dest_filter_combo.currentText()
        pending_ids = set(self.pending_placements.values())
        if self.active_relocation_container: pending_ids.add(self.active_relocation_container['id'])
        for c in self.all_loadable_containers:
            if c['id'] in pending_ids: continue
            type_match = (selected_type == "Tüm Tipler" or c['tip'] == selected_type)
            dest_match = (selected_dest == "Tüm Limanlar" or c.get('varis_limani') == selected_dest)
            if type_match and dest_match:
                item = QListWidgetItem(f"{c['id']} ({c['tip']})"); item.setData(Qt.ItemDataRole.UserRole, c); self.container_list.addItem(item)
    def _populate_ship_combo(self):
        ships = self.db.get_all_ships(); current_id = self.current_ship_id
        self.ship_combo.blockSignals(True); self.ship_combo.clear()
        if not ships: self.ship_combo.addItem("Gemi Yok"); self.ship_combo.blockSignals(False); self.on_ship_selected(-1); return
        for ship in ships: self.ship_combo.addItem(f"{ship['gemi_adi']} ({ship['gemi_id']})", ship['gemi_id'])
        index = self.ship_combo.findData(current_id); self.ship_combo.setCurrentIndex(index if index != -1 else 0)
        self.ship_combo.blockSignals(False); self.on_ship_selected(self.ship_combo.currentIndex())
    def on_ship_selected(self, index):
        if index == -1 or not self.db.conn: self.current_ship_id, self.current_ship_details = None, {}; self.BAYS, self.ROWS_PER_BAY, self.TIERS_PER_BAY = [], 0, 0
        else:
            self.current_ship_id = self.ship_combo.itemData(index)
            self.current_ship_details = self.db.execute_query("SELECT * FROM public.gemiler WHERE gemi_id=%s", (self.current_ship_id,), fetchone=True)
            if self.current_ship_details:
                self.BAYS = [f"B{i:02d}" for i in range(1, self.current_ship_details.get('toplam_bay_sayisi', 0) + 1)]
                self.ROWS_PER_BAY = self.current_ship_details.get('toplam_sira_sayisi', 0)
                self.TIERS_PER_BAY = self.current_ship_details.get('toplam_kat_sayisi', 0)
        self.cancel_actions()
    def update_display(self):
        self.scene.clear()
        is_action_pending = bool(self.pending_placements or self.active_relocation_container)
        self.action_widget.setVisible(is_action_pending)
        current_ship_name = self.current_ship_details.get('gemi_adi', 'Seçilmedi') if self.current_ship_details else 'Seçilmedi'
        if self.current_view == 'OVERVIEW':
            self.title_label.setText(f"{current_ship_name}: Genel Görünüm"); self.back_button.setVisible(False)
            if self.current_ship_id: self.draw_bay_overview()
        elif self.current_view == 'DETAIL':
            title = f"{current_ship_name}, Bay {self.current_bay} - Detaylı Görünüm"
            if self.active_relocation_container: title = f"TAŞIMA: {self.active_relocation_container['id']} için yeni hedef seçin"
            elif self.active_container_for_placement: title += f" | Planlanan: {self.active_container_for_placement['id']}"
            self.title_label.setText(title); self.back_button.setVisible(True); self.draw_detailed_bay_view()
    def draw_bay_overview(self):
        cols, w, h = 10, 80, 80
        if not self.BAYS: return
        for i, bay_id in enumerate(self.BAYS):
            r, c = divmod(i, cols)
            rect = InteractiveRectItem(c * (w + 10), r * (h + 10), w, h); rect.setBrush(QBrush(QColor("#0077b6")))
            rect.setData(0, {'type': 'bay_overview', 'id': bay_id}); rect.clicked.connect(self.handle_item_click); self.scene.addItem(rect)
            text = QGraphicsSimpleTextItem(bay_id.replace("B", "")); text.setFont(QFont("Arial", 24, QFont.Weight.Bold)); text.setBrush(QBrush(Qt.GlobalColor.white))
            text.setPos(rect.boundingRect().center() - text.boundingRect().center()); text.setParentItem(rect); rect.setToolTip(f"Bay {bay_id}")
    def _get_container_color(self, container): return config_manager.get_color("reefer") if "REEFER" in container.get('tip', '').upper() else config_manager.get_color("filled")
    def draw_detailed_bay_view(self):
        slot_w, slot_h, x_off, y_off = 60, 40, 50, 50
        if not self.ROWS_PER_BAY or not self.TIERS_PER_BAY: return
        for i in range(self.TIERS_PER_BAY):
            tier_lbl = QGraphicsSimpleTextItem(f"{i:02d}"); self.scene.addItem(tier_lbl)
            tier_lbl.setPos(0, y_off + (self.TIERS_PER_BAY - 1 - i) * (slot_h + 5) + slot_h/4)
        for i in range(self.ROWS_PER_BAY):
            row_lbl = QGraphicsSimpleTextItem(f"{i:02d}"); self.scene.addItem(row_lbl)
            row_lbl.setPos(x_off + i * (slot_w + 5) + slot_w/3, 20)
        display_slots = self.filled_ship_slots.get(self.current_bay, {}).copy()
        if self.pending_relocation_from_coords in display_slots: del display_slots[self.pending_relocation_from_coords]
        for coords, c_id in self.pending_placements.items():
            if coords != 'RELOCATION': display_slots[coords] = next((c for c in self.all_loadable_containers if c['id'] == c_id), {})
        if 'RELOCATION' in self.pending_placements:
            coords, _ = self.pending_placements['RELOCATION']; display_slots[coords] = self.active_relocation_container
        active_c_data = self.active_container_for_placement or self.active_relocation_container
        for r in range(self.ROWS_PER_BAY):
            col_tiers = {t for r_k, t in display_slots.keys() if r_k == r}; lowest_placeable = 0
            while lowest_placeable in col_tiers: lowest_placeable += 1
            for t in range(self.TIERS_PER_BAY):
                coords, container = (r, t), display_slots.get((r, t))
                rect = InteractiveRectItem(x_off + r * (slot_w + 5), y_off + (self.TIERS_PER_BAY - 1 - t) * (slot_h + 5), slot_w, slot_h)
                is_placeable, is_pending = False, (self.pending_placements.get(coords) or self.pending_placements.get('RELOCATION', [None])[0] == coords)
                if container:
                    color, tooltip = config_manager.get_color("pending") if is_pending else self._get_container_color(container), f"ID: {container.get('id', 'N/A')}"
                    
                    # <<< YENİ/DEĞİŞEN SATIRLAR BAŞLANGICI >>>
                    # Konteyner ID'sini tek satırda göster
                    id_text = QGraphicsSimpleTextItem(container.get('id', ''))
                    # Yazının slota sığması için font boyutu belirgin şekilde küçültüldü
                    id_text.setFont(QFont("Arial", 6, QFont.Weight.Bold))
                    id_text.setBrush(QBrush(Qt.GlobalColor.white))
                    # Yazıyı dikdörtgenin içinde ortala
                    id_text.setPos(rect.boundingRect().center() - id_text.boundingRect().center())
                    id_text.setParentItem(rect)
                    # <<< YENİ/DEĞİŞEN SATIRLAR BİTİŞİ >>>

                else:
                    is_gravity_ok = (t == lowest_placeable)
                    if not is_gravity_ok: color, tooltip = config_manager.get_color("empty"), "Yerleştirilemez (Altı Boş)"
                    elif active_c_data:
                        bottom_container = display_slots.get((r, t - 1))
                        req_size, req_is_reefer = parse_container_type(bottom_container.get('tip')) if bottom_container else (None, None)
                        c_size, c_is_reefer = parse_container_type(active_c_data.get('tip'))
                        size_ok = (req_size is None) or (c_size == req_size)
                        reefer_ok = (req_is_reefer is None) or (c_is_reefer == req_is_reefer)
                        if size_ok and reefer_ok: is_placeable, color, tooltip = True, config_manager.get_color("placeable"), "Uygun Slot"
                        else: is_placeable, color, tooltip = False, config_manager.get_color("incompatible"), "Uyumsuz! (Boyut veya Tip)"
                    else: color, tooltip = config_manager.get_color("empty"), "Slot Boş"
                rect.setBrush(QBrush(color)); rect.setPen(QPen(Qt.GlobalColor.white, 0.5))
                rect.setData(0, {'type': 'slot', 'row': r, 'tier': t, 'filled': bool(container), 'placeable': is_placeable})
                rect.setToolTip(tooltip); rect.clicked.connect(self.handle_item_click); self.scene.addItem(rect)
    def handle_item_click(self, data):
        if data['type'] == 'bay_overview': self.current_bay = data['id']; self.current_view = 'DETAIL'; self.cancel_actions()
        elif data['type'] == 'slot':
            coords = (data['row'], data['tier'])
            if self.active_relocation_container and data.get('placeable'): self.stage_relocation(coords)
            elif self.active_container_for_placement and data.get('placeable'): self.stage_placement(self.active_container_for_placement['id'], coords)
            elif data.get('placeable'): QMessageBox.information(self, "Bilgi", "Önce soldan bir konteyner seçin.")
    def open_slot_menu(self, position: QPoint):
        item = self.view.itemAt(position)
        if not (item and isinstance(item, InteractiveRectItem)): return
        data = item.data(0)
        if not (data and data['type'] == 'slot' and data['filled']): return
        coords = (data['row'], data['tier'])
        if self.pending_placements.get(coords) or self.pending_placements.get('RELOCATION', [None])[0] == coords: return
        container = self.filled_ship_slots.get(self.current_bay, {}).get(coords)
        if not container: return 
        menu = QMenu()
        menu.addAction("Detayları Göster").triggered.connect(lambda: self.show_container_details(container))
        menu.addAction("Bu Konteyneri Taşı").triggered.connect(lambda: self.start_relocation(container, coords))
        menu.exec(self.view.mapToGlobal(position))
    def show_container_details(self, container_data):
        if not container_data: return
        location = container_data.get('gemi_konum', f"Gemi: {self.current_ship_id}, Bay: {self.current_bay}")
        ContainerDetailDialog(container_data, location, self).exec()
    def on_container_selected_for_planning(self, item_clicked: QListWidgetItem):
        if not item_clicked: return
        container_data = item_clicked.data(Qt.ItemDataRole.UserRole)
        self.cancel_actions() 
        self.active_container_for_placement = container_data
        self.update_display()
    def start_relocation(self, container, from_coords):
        self.cancel_actions()
        self.active_relocation_container = container
        self.pending_relocation_from_coords = from_coords
        self._filter_and_populate_list()
        self.update_display()
    def stage_placement(self, container_id, coords):
        self.pending_placements[coords] = container_id
        self.active_container_for_placement = None
        self._filter_and_populate_list(); self.update_display()
    def stage_relocation(self, to_coords):
        self.pending_placements['RELOCATION'] = (to_coords, self.active_relocation_container['id'])
        self.active_relocation_container = None
        self.update_display()
    def confirm_actions(self):
        if not self.pending_placements: return
        if 'RELOCATION' in self.pending_placements:
            to_coords, c_id = self.pending_placements.pop('RELOCATION')
            self.db.update_container_ship_location(c_id, self.current_bay, to_coords[0], to_coords[1])
        for coords, c_id in self.pending_placements.items():
            self.db.add_container_to_ship(c_id, self.current_ship_id, coords[0], coords[1], self.current_bay)
        QMessageBox.information(self, "Başarılı", "Tüm işlemler kaydedildi.")
        self.main_window.refresh_all_tabs()
    def cancel_actions(self):
        self.pending_placements.clear()
        self.active_container_for_placement, self.active_relocation_container, self.pending_relocation_from_coords = None, None, None
        if self.current_ship_id: self.filled_ship_slots = self.db.get_all_ship_slots(self.current_ship_id)
        else: self.filled_ship_slots = {}
        self._filter_and_populate_list(); self.update_display()
    def go_back(self):
        self.current_view = 'OVERVIEW'; self.current_bay = None; self.cancel_actions()