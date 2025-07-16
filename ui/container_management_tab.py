# ui/container_management_tab.py (ISO 6346 Entegrasyonu ile)

import random
import string
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QMessageBox, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QValidator, QRegularExpressionValidator
import qtawesome as qta

# --- YENİ FONKSİYONLAR ---
def calculate_check_digit(owner_code, serial_number):
    """ISO 6346 standardına göre kontrol basamağını hesaplar."""
    # ISO 6346 standardındaki harfların değerleri (L harfi atlandığı için 22 yok)
    letter_values = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18,
        'I': 19, 'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27,
        'Q': 28, 'R': 29, 'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35, 'X': 36,
        'Y': 37, 'Z': 38
    }
    
    # Owner code (4 harف) + serial number (6 rakam) = 10 karakter
    full_code = owner_code + serial_number
    total_sum = 0
    
    # İlk 4 karakter (owner code) - harfler
    for i, char in enumerate(full_code[:4]):
        if char.upper() in letter_values:
            total_sum += letter_values[char.upper()] * (2**i)
        else:
            raise ValueError(f"Invalid character in owner code: {char}")
    
    # Son 6 karakter (serial number) - rakamlar  
    for i, digit in enumerate(full_code[4:10]):
        if digit.isdigit():
            total_sum += int(digit) * (2**(i + 4))
        else:
            raise ValueError(f"Invalid digit in serial number: {digit}")
    
    # Check digit hesapla
    check_digit = total_sum % 11
    return 0 if check_digit == 10 else check_digit

def is_valid_container_id(container_id):
    """Bir konteyner ID'sinin ISO 6346 formatına ve kontrol basamağına uygunluğunu kontrol eder."""
    container_id = container_id.strip().upper()
    if not re.match(r"^[A-Z]{4}\d{7}$", container_id):
        return False, "Format Hatalı (4 Harf + 7 Rakam olmalı)."
    
    owner_code = container_id[:4]
    serial_number = container_id[4:10]
    provided_check_digit = int(container_id[10])
    
    if owner_code[3] != 'U':
         return False, "Ekipman Kategorisi 'U' olmalı."

    calculated_check_digit = calculate_check_digit(owner_code, serial_number)
    
    if provided_check_digit == calculated_check_digit:
        return True, "Geçerli ID."
    else:
        return False, f"Kontrol Basamağı Hatalı (Hesaplanan: {calculated_check_digit})."
# -------------------------


class ContainerManagementTab(QWidget):
    def __init__(self, db_connection, main_window, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # YENİ: Minimum boyut ayarla
        self.setMinimumSize(1000, 600)
        
        # Title
        title_label = QLabel("Konteyner Yönetimi")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Search layout
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Konteyner ID ile Ara:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Aramak için yazın...")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        self.container_table = QTableWidget()
        self.container_table.setColumnCount(6)
        self.container_table.setHorizontalHeaderLabels(["ID", "Tip", "Durum", "Konum", "Çıkış Limanı", "Varış Limanı"])
        self.container_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.container_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.container_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.container_table.itemSelectionChanged.connect(self.on_container_selected)
        main_layout.addWidget(self.container_table)

        # Form layout
        form_layout = QFormLayout()
        
        # Container ID input with validation
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Örn: MSKU1234567")
        self.id_input.textChanged.connect(self.validate_id_input_live)
        
        # Container type combo
        self.tip_input = QComboBox()
        self.tip_input.addItems(["20ft DC", "40ft DC", "40ft HC", "45ft HC", "20ft REEFER", "40ft REEFER"])
        
        # Port inputs
        self.cikis_limani_input = QLineEdit()
        self.varis_limani_input = QLineEdit()
        
        # Status and location
        self.durum_combo = QComboBox()
        self.durum_combo.addItems(['ATANMAMIS', 'SAHA', 'GEMI'])
        self.konum_input = QLineEdit()
        self.konum_input.setPlaceholderText("Durum 'SAHA' ise doldurun (örn: A-01-01)")
        
        # ID feedback label
        self.id_feedback_label = QLabel("")
        self.id_feedback_label.setStyleSheet("color: #E67E22;")
        
        # Add form rows
        form_layout.addRow("Konteyner ID:", self.id_input)
        form_layout.addRow("", self.id_feedback_label)  # ID feedback label
        form_layout.addRow("Konteyner Tipi:", self.tip_input)
        form_layout.addRow("Durum:", self.durum_combo)
        form_layout.addRow("Saha Konumu:", self.konum_input)
        form_layout.addRow("Çıkış Limanı:", self.cikis_limani_input)
        form_layout.addRow("Varış Limanı:", self.varis_limani_input)
        main_layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton(qta.icon('fa5s.plus-circle', color='lightgreen'), " Yeni Konteyner Ekle")
        self.add_button.clicked.connect(self.add_container)
        
        self.random_button = QPushButton(qta.icon('fa5s.magic', color='#5DADE2'), " Rastgele Konteyner Oluştur")
        self.random_button.clicked.connect(self.generate_random_container)
        
        self.update_button = QPushButton(qta.icon('fa5s.edit', color='lightblue'), " Konteyner Güncelle")
        self.update_button.clicked.connect(self.update_container)
        
        self.delete_button = QPushButton(qta.icon('fa5s.trash-alt', color='red'), " Konteyner Sil")
        self.delete_button.clicked.connect(self.delete_container)
        
        self.clear_button = QPushButton(qta.icon('fa5s.eraser', color='grey'), " Formu Temizle")
        self.clear_button.clicked.connect(self.clear_form)

        for btn in [self.add_button, self.random_button, self.update_button, self.delete_button, self.clear_button]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(120)
            btn.setIconSize(QSize(20, 20))
            btn.setStyleSheet('''
                QPushButton { text-align: left; padding-left: 16px; }
                QPushButton:disabled { color: #888; background-color: #222C36; border: 1px solid #444; text-align: left; padding-left: 16px; }
            ''')

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.random_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)
        self.refresh_container_list()

    def validate_id_input_live(self, text):
        """Kullanıcı ID girerken canlı olarak formatı kontrol eder ve geri bildirim verir."""
        if not text:
            self.id_feedback_label.setText("")
            return
        
        is_valid, message = is_valid_container_id(text)
        if is_valid:
            self.id_feedback_label.setText(f"✓ {message}")
            self.id_feedback_label.setStyleSheet("color: #2ECC71;")  # Green
        else:
            self.id_feedback_label.setText(f"✗ {message}")
            self.id_feedback_label.setStyleSheet("color: #E74C3C;")  # Red
        self.add_button.setEnabled(is_valid)

    # --- GÜNCELLENMİŞ FONKSİYON ---
    def generate_random_container(self):
        """ISO 6346 standardına uygun rastgele ve geçerli bir konteyner ID'si oluşturur."""
        try:
            # Database connection kontrolü
            if not self.db or not hasattr(self.db, 'get_container_details_by_id'):
                QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı mevcut değil!")
                return
            
            tip_list = [self.tip_input.itemText(i) for i in range(self.tip_input.count())]
            port_list = ["İstanbul", "Mersin", "İzmir", "Rotterdam", "Hamburg", "Şangay", "New York", "Singapur", "Anvers"]
            durum_list = ["ATANMAMIS", "SAHA", "GEMI"]  # Valid database statuses only
            
            max_attempts = 10
            attempt = 0
            random_id = None
            
            while attempt < max_attempts:
                # Python uyumluluğu için random.choice kullan
                owner_code = ''.join([random.choice(string.ascii_uppercase) for _ in range(3)]) + 'U'
                serial_number = ''.join([random.choice(string.digits) for _ in range(6)])
                check_digit = calculate_check_digit(owner_code, serial_number)
                random_id = f"{owner_code}{serial_number}{check_digit}"
                
                # Konteyner ID'si daha önce kullanılmış mı kontrol et
                existing = self.db.get_container_details_by_id(random_id)
                
                if not existing:
                    break
                attempt += 1
            else:
                QMessageBox.critical(self, "Hata", "10 denemede benzersiz konteyner ID'si üretilemedi!")
                return

            random_tip = random.choice(tip_list) if tip_list else "20ft DC"
            cikis_limani = random.choice(port_list)
            varis_limani = random.choice(port_list)
            while varis_limani == cikis_limani: 
                varis_limani = random.choice(port_list)
            random_durum = random.choice(durum_list)
            
            # Konteyneri veritabanına ekle
            result = self.db.add_new_container(random_id, random_tip, cikis_limani, varis_limani, random_durum)
            
            if result is True:
                # Show success message
                QMessageBox.information(self, "Başarılı", 
                    f"Rastgele Konteyner Oluşturuldu!\n\n"
                    f"ID: {random_id}\n"
                    f"Tip: {random_tip}\n"
                    f"Durum: {random_durum}\n"
                    f"Rota: {cikis_limani} → {varis_limani}")
                
                # Refresh the list first
                self.refresh_and_notify()
                
                # Then set search to the new container ID to help user find it
                print(f"🔍 Setting search to new container ID: {random_id}")
                self.search_input.setText(random_id)
                
                print(f"✅ New container {random_id} created and search set")
            else:
                error_msg = result if isinstance(result, str) else "Veritabanı hatası!"
                QMessageBox.critical(self, "Hata", f"Konteyner eklenemedi!\n\nID: {random_id}\nHata: {error_msg}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "Hata", f"Rastgele konteyner oluşturma hatası:\n\n{str(e)}")
            return

    def filter_table(self):
        """Enhanced search function that searches across multiple columns."""
        search_text = self.search_input.text().lower().strip()
        
        if not search_text:
            # If search is empty, show all rows
            for row in range(self.container_table.rowCount()):
                self.container_table.setRowHidden(row, False)
            print(f"🔍 Showing all {self.container_table.rowCount()} containers")
            return
        
        print(f"🔍 Searching for: '{search_text}' in {self.container_table.rowCount()} containers")
        
        visible_count = 0
        for row in range(self.container_table.rowCount()):
            # Search in multiple columns: ID, Tip, Durum, Konum, Çıkış, Varış
            should_show = False
            
            for col in range(6):  # 6 columns total
                item = self.container_table.item(row, col)
                if item and search_text in item.text().lower():
                    should_show = True
                    # For debugging: show which column matched
                    if visible_count < 3:  # Only log first 3 matches to avoid spam
                        col_names = ["ID", "Tip", "Durum", "Konum", "Çıkış", "Varış"]
                        print(f"  ✅ Match in {col_names[col]}: '{item.text()}'")
                    break
            
            self.container_table.setRowHidden(row, not should_show)
            if should_show:
                visible_count += 1
        
        print(f"🔍 Search '{search_text}' found {visible_count} matching containers")
        
        if visible_count == 0:
            print("⚠️  No matches found. Check:")
            print("   - Is the search term spelled correctly?")
            print("   - Try searching with partial terms")
            print("   - Clear search to see all containers")

    def refresh_container_list(self):
        """Refresh the container list with enhanced logging."""
        print("🔄 Refreshing container list...")
        self.container_table.setRowCount(0)
        
        containers = self.db.get_all_containers_detailed()
        print(f"🔄 Retrieved {len(containers) if containers else 0} containers from database")
        
        if not containers: 
            self.clear_form()
            print("⚠️  No containers found in database")
            return
        
        self.container_table.setRowCount(len(containers))
        print(f"🔄 Setting up table with {len(containers)} rows")
        
        for row, c in enumerate(containers):
            # Column 0: ID
            container_id = c.get('id', '')
            self.container_table.setItem(row, 0, QTableWidgetItem(container_id))
            
            # Column 1: Type
            container_type = c.get('tip', '')
            self.container_table.setItem(row, 1, QTableWidgetItem(container_type))
            
            # Column 2: Status
            durum = c.get('durum', 'Bilinmiyor')
            self.container_table.setItem(row, 2, QTableWidgetItem(durum))
            
            # Column 3: Location
            konum_str = ""
            if durum == 'SAHA': 
                konum_str = c.get('saha_konum') or 'Konum Hatası!'
            elif durum == 'GEMI': 
                konum_str = c.get('gemi_konum') or f"GEMI: {c.get('gemi_id', '?')}"
            elif durum == 'ATANMAMIS': 
                konum_str = 'Atanmamış'
            self.container_table.setItem(row, 3, QTableWidgetItem(konum_str))
            
            # Column 4: Origin Port
            origin = c.get('cikis_limani', '')
            self.container_table.setItem(row, 4, QTableWidgetItem(origin))
            
            # Column 5: Destination Port
            destination = c.get('varis_limani', '')
            self.container_table.setItem(row, 5, QTableWidgetItem(destination))
        
        print(f"✅ Container table updated with {len(containers)} containers")
        self.clear_form()

    def on_container_selected(self):
        selected_rows = self.container_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        self.id_input.setText(self.container_table.item(row, 0).text()); self.tip_input.setCurrentText(self.container_table.item(row, 1).text())
        self.durum_combo.setCurrentText(self.container_table.item(row, 2).text())
        konum_text = self.container_table.item(row, 3).text()
        if self.container_table.item(row, 2).text() == 'SAHA': self.konum_input.setText(konum_text if konum_text != 'Konum Hatası!' else '')
        else: self.konum_input.clear()
        self.cikis_limani_input.setText(self.container_table.item(row, 4).text()); self.varis_limani_input.setText(self.container_table.item(row, 5).text())
        self.id_input.setReadOnly(True)
        self.id_feedback_label.setText("") # Seçim yapıldığında geri bildirimi temizle
        self.add_button.setEnabled(False); self.random_button.setEnabled(False)
        self.update_button.setEnabled(True); self.delete_button.setEnabled(True)

    def clear_form(self):
        self.id_input.clear(); self.tip_input.setCurrentIndex(0); self.cikis_limani_input.clear(); self.varis_limani_input.clear()
        self.durum_combo.setCurrentText('ATANMAMIS'); self.konum_input.clear()
        self.id_input.setReadOnly(False); self.container_table.clearSelection()
        self.add_button.setEnabled(True); self.random_button.setEnabled(True)
        self.update_button.setEnabled(False); self.delete_button.setEnabled(False)
        self.id_feedback_label.setText("")

    def add_container(self):
        c_id = self.id_input.text().strip().upper()
        c_tip = self.tip_input.currentText()
        c_cikis = self.cikis_limani_input.text().strip()
        c_varis = self.varis_limani_input.text().strip()
        
        # ID geçerliliğini kontrol et
        is_valid, message = is_valid_container_id(c_id)
        if not is_valid:
            QMessageBox.warning(self, "Geçersiz ID", f"Konteyner ID'si geçerli değil: {message}")
            return

        if not all([c_tip, c_cikis, c_varis]): 
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen Tip, Çıkış ve Varış Limanı alanlarını doldurun.")
            return

        if self.db.get_container_details_by_id(c_id): 
            QMessageBox.warning(self, "Mevcut ID", f"'{c_id}' ID'li bir konteyner zaten var.")
            return
        
        try:
            result = self.db.add_new_container(c_id, c_tip, c_cikis, c_varis, self.durum_combo.currentText())
            if result is True:
                QMessageBox.information(self, "Başarılı", f"'{c_id}' konteyneri eklendi.")
                
                # Refresh the list first
                self.refresh_and_notify()
                
                # Then set search to the new container ID to help user find it
                print(f"🔍 Setting search to new container ID: {c_id}")
                self.search_input.setText(c_id)
                
                print(f"✅ Container {c_id} added and search set")
            else:
                raise Exception(result or "Bilinmeyen veritabanı hatası")
        except Exception as e:
            err = str(e)
            QMessageBox.critical(self, "Hata", f"Konteyner eklenemedi!\n\nID: {c_id}\nHata: {err}")

    def update_container(self):
        c_id = self.id_input.text().strip(); c_tip = self.tip_input.currentText(); c_cikis = self.cikis_limani_input.text().strip(); c_varis = self.varis_limani_input.text().strip()
        c_durum = self.durum_combo.currentText(); c_konum = self.konum_input.text().strip()
        if not c_id: return
        if self.db.update_container_full_details(c_id, c_tip, c_durum, c_konum, c_cikis, c_varis):
            QMessageBox.information(self, "Başarılı", f"'{c_id}' konteyneri güncellendi."); self.refresh_and_notify()
        else:
            QMessageBox.critical(self, "Hata", "Konteyner güncellenirken bir hata oluştu.")
            
    def delete_container(self):
        c_id = self.id_input.text().strip()
        if not c_id: return
        reply = QMessageBox.question(self, "Onay", f"'{c_id}' ID'li konteyneri kalıcı olarak silmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_container_by_id(c_id):
                QMessageBox.information(self, "Başarılı", f"'{c_id}' konteyneri silindi."); self.refresh_and_notify()
            else:
                QMessageBox.critical(self, "Hata", "Konteyner silinirken hata oluştu.")

    def refresh_and_notify(self):
        """Refresh container list and clear any active filters."""
        print("🔄 Refreshing and notifying...")
        
        # Clear search filter to show all containers
        current_search = self.search_input.text()
        if current_search:
            print(f"🔄 Clearing current search filter: '{current_search}'")
        
        # Temporarily disconnect to prevent recursive calls
        self.search_input.textChanged.disconnect()
        self.search_input.setText("")  # Clear search
        self.search_input.textChanged.connect(self.filter_table)
        
        # Refresh the container list
        self.refresh_container_list()
        
        # Notify main window
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.refresh_all_tabs()
        
        print("✅ Refresh completed - all containers should be visible")