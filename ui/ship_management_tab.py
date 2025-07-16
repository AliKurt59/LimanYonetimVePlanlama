# ui/ship_management_tab.py (Nihai Buton Düzeltmesi)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import qtawesome as qta

class ShipManagementTab(QWidget):
    def on_ship_selected(self):
        selected_rows = self.ships_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            self.gemi_id_input.setText(self.ships_table.item(row, 0).text())
            self.gemi_id_input.setReadOnly(True)
            self.gemi_adi_input.setText(self.ships_table.item(row, 1).text())
            self.toplam_bay_input.setText(self.ships_table.item(row, 2).text())
            self.toplam_sira_input.setText(self.ships_table.item(row, 3).text())
            self.toplam_kat_input.setText(self.ships_table.item(row, 4).text())
            self.add_button.setEnabled(False)
            self.update_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.clear_form()
    def __init__(self, db_connection, main_window, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.main_window = main_window
        self.init_ui()
        self.refresh_ships_list()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        title_label = QLabel("Gemi Yönetimi"); title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold)); title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        self.ships_table = QTableWidget()
        self.ships_table.setColumnCount(5)
        self.ships_table.setHorizontalHeaderLabels(["Gemi ID", "Gemi Adı", "Toplam Bay", "Toplam Sıra", "Toplam Kat"])
        self.ships_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ships_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ships_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.ships_table.itemSelectionChanged.connect(self.on_ship_selected)
        main_layout.addWidget(self.ships_table)
        form_layout = QFormLayout()
        self.gemi_id_input = QLineEdit(); self.gemi_id_input.setReadOnly(True)
        self.gemi_adi_input = QLineEdit()
        self.toplam_bay_input = QLineEdit("20"); self.toplam_sira_input = QLineEdit("10"); self.toplam_kat_input = QLineEdit("12")
        form_layout.addRow("Gemi ID:", self.gemi_id_input); form_layout.addRow("Gemi Adı:", self.gemi_adi_input)
        form_layout.addRow("Toplam Bay Sayısı:", self.toplam_bay_input); form_layout.addRow("Toplam Sıra Sayısı:", self.toplam_sira_input)
        form_layout.addRow("Toplam Kat Sayısı:", self.toplam_kat_input)
        main_layout.addLayout(form_layout)
        button_layout = QHBoxLayout()
        self.add_button = QPushButton(qta.icon('fa5s.plus-circle', color='lightgreen'), " Gemi Ekle"); self.add_button.clicked.connect(self.add_ship)
        self.update_button = QPushButton(qta.icon('fa5s.edit', color='lightblue'), " Gemi Güncelle"); self.update_button.clicked.connect(self.update_ship)
        self.delete_button = QPushButton(qta.icon('fa5s.trash-alt', color='red'), " Gemi Sil"); self.delete_button.clicked.connect(self.delete_ship)
        self.clear_button = QPushButton(qta.icon('fa5s.eraser', color='grey'), " Temizle"); self.clear_button.clicked.connect(self.clear_form)

        # Tüm butonlara aynı genişlikte esneme ver ve ikon/metin hizalamasını düzelt
        for btn in [self.add_button, self.update_button, self.delete_button, self.clear_button]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(120)
            btn.setIconSize(QSize(20, 20))
            btn.setStyleSheet('''
                QPushButton {
                    text-align: left;
                    padding-left: 16px;
                }
                QPushButton:disabled {
                    color: #888;
                    background-color: #222C36;
                    border: 1px solid #444;
                    text-align: left;
                    padding-left: 16px;
                }
            ''')

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

    def refresh_ships_list(self):
        """Refresh the table of ships and clear the form."""
        self.ships_table.setRowCount(0)
        ships = self.db.get_all_ships()
        if ships:
            self.ships_table.setRowCount(len(ships))
            for row, ship in enumerate(ships):
                self.ships_table.setItem(row, 0, QTableWidgetItem(ship.get('gemi_id', '')))
                self.ships_table.setItem(row, 1, QTableWidgetItem(ship.get('gemi_adi', '')))
                self.ships_table.setItem(row, 2, QTableWidgetItem(str(ship.get('toplam_bay_sayisi', ''))))
                self.ships_table.setItem(row, 3, QTableWidgetItem(str(ship.get('toplam_sira_sayisi', ''))))
                self.ships_table.setItem(row, 4, QTableWidgetItem(str(ship.get('toplam_kat_sayisi', ''))))
        self.clear_form()
    def add_ship(self):
        gemi_adi = self.gemi_adi_input.text().strip()
        if not gemi_adi:
            QMessageBox.warning(self, "Eksik Bilgi", "Gemi Adı boş bırakılamaz.")
            return
        try:
            toplam_bay = int(self.toplam_bay_input.text().strip() or 20)
            toplam_sira = int(self.toplam_sira_input.text().strip() or 10)
            toplam_kat = int(self.toplam_kat_input.text().strip() or 12)
        except ValueError:
            QMessageBox.warning(self, "Geçersiz Sayı", "Sayısal alanlar geçerli tam sayı olmalıdır.")
            return
        # Gemi ID her zaman otomatik ve readonly olmalı
        gemi_id = self.gemi_id_input.text().strip()
        if not gemi_id:
            gemi_id = self.db.generate_next_ship_id()
            self.gemi_id_input.setText(gemi_id)
        self.gemi_id_input.setReadOnly(True)
        result = self.db.add_ship(gemi_id, gemi_adi, toplam_bay, toplam_sira, toplam_kat)
        if result:
            QMessageBox.information(self, "Başarılı", f"'{gemi_adi}' gemisi eklendi.")
            self.refresh_and_notify()
        else:
            QMessageBox.critical(self, "Hata", "Gemi eklenirken bir hata oluştu.")
        # Sonraki ekleme için yeni ID ata
        next_id = self.db.generate_next_ship_id()
        self.gemi_id_input.setText(next_id)
        self.gemi_id_input.setReadOnly(True)

    def update_ship(self):
        gemi_id = self.gemi_id_input.text().strip(); gemi_adi = self.gemi_adi_input.text().strip()
        if not gemi_id or not gemi_adi: QMessageBox.warning(self, "Eksik Bilgi", "Gemi ID ve Adı boş bırakılamaz."); return
        try:
            toplam_bay = int(self.toplam_bay_input.text().strip() or 20)
            toplam_sira = int(self.toplam_sira_input.text().strip() or 10)
            toplam_kat = int(self.toplam_kat_input.text().strip() or 12)
        except ValueError: QMessageBox.warning(self, "Geçersiz Sayı", "Sayısal alanlar geçerli tam sayı olmalıdır."); return
        if self.db.update_ship(gemi_id, gemi_adi, toplam_bay, toplam_sira, toplam_kat):
            QMessageBox.information(self, "Başarılı", f"'{gemi_adi}' gemisi güncellendi."); self.refresh_and_notify()
        else:
            QMessageBox.critical(self, "Hata", "Gemi güncellenirken bir hata oluştu.")

    def delete_ship(self):
        gemi_id = self.gemi_id_input.text().strip()
        if not gemi_id: return
        reply = QMessageBox.question(self, "Onay", f"'{gemi_id}' ID'li gemiyi ve tüm ilgili yükleme kayıtlarını silmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_ship(gemi_id):
                QMessageBox.information(self, "Başarılı", f"'{gemi_id}' gemisi silindi."); self.refresh_and_notify()
            else:
                QMessageBox.critical(self, "Hata", "Gemi silinirken bir hata oluştu.")

        self.gemi_id_input.clear(); self.gemi_adi_input.clear()
        self.toplam_bay_input.setText("20"); self.toplam_sira_input.setText("10"); self.toplam_kat_input.setText("12")
        self.gemi_id_input.setReadOnly(False); self.ships_table.clearSelection()
        self.add_button.setEnabled(True); self.update_button.setEnabled(False); self.delete_button.setEnabled(False)
        next_id = self.db.generate_next_ship_id()
        if next_id: self.gemi_id_input.setText(next_id)
    def clear_form(self):
        self.gemi_adi_input.clear()
        self.toplam_bay_input.setText("20")
        self.toplam_sira_input.setText("10")
        self.toplam_kat_input.setText("12")
        self.ships_table.clearSelection()
        self.add_button.setEnabled(True)
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        # Always ensure new ship ID is set
        try:
            next_id = self.db.generate_next_ship_id()
            if next_id:
                self.gemi_id_input.setText(next_id)
            else:
                self.gemi_id_input.setText("GEMI-01")
        except Exception:
            self.gemi_id_input.setText("GEMI-01")
        self.gemi_id_input.setReadOnly(True)

    def refresh_and_notify(self):
        self.refresh_ships_list()
        self.main_window.refresh_all_tabs()