# ui/import_export_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QComboBox, QProgressBar, QTextEdit,
                           QTabWidget, QWidget, QFormLayout, QFileDialog,
                           QMessageBox, QGroupBox, QListWidget, QListWidgetItem,
                           QCheckBox, QSpinBox, QTableWidget, QTableWidgetItem,
                           QHeaderView, QSplitter, QLineEdit)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
import qtawesome as qta
from datetime import datetime
import os
import json

class ImportExportThread(QThread):
    """Background thread for import/export operations."""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    operation_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, import_export_system, operation_type, parameters):
        super().__init__()
        self.import_export_system = import_export_system
        self.operation_type = operation_type
        self.parameters = parameters
    
    def run(self):
        try:
            if self.operation_type == 'export_excel':
                self.status_updated.emit("Excel dosyası oluşturuluyor...")
                self.progress_updated.emit(20)
                
                success = self.import_export_system.export_to_excel(
                    self.parameters.get('output_path'),
                    self.parameters.get('tables', None)
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit({'success': success, 'type': 'export_excel'})
                
            elif self.operation_type == 'import_excel':
                self.status_updated.emit("Excel dosyası içe aktarılıyor...")
                self.progress_updated.emit(20)
                
                result = self.import_export_system.import_from_excel(
                    self.parameters.get('file_path'),
                    self.parameters.get('table_mappings', None)
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit(result)
                
            elif self.operation_type == 'export_csv':
                self.status_updated.emit("CSV dosyası oluşturuluyor...")
                self.progress_updated.emit(20)
                
                success = self.import_export_system.export_to_csv(
                    self.parameters.get('table_name'),
                    self.parameters.get('output_path'),
                    self.parameters.get('delimiter', ',')
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit({'success': success, 'type': 'export_csv'})
                
            elif self.operation_type == 'import_csv':
                self.status_updated.emit("CSV dosyası içe aktarılıyor...")
                self.progress_updated.emit(20)
                
                result = self.import_export_system.import_from_csv(
                    self.parameters.get('file_path'),
                    self.parameters.get('table_name'),
                    self.parameters.get('delimiter', ',')
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit(result)
                
            elif self.operation_type == 'create_backup':
                self.status_updated.emit("Yedek oluşturuluyor...")
                self.progress_updated.emit(20)
                
                result = self.import_export_system.create_full_backup(
                    self.parameters.get('backup_name')
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit(result)
                
            elif self.operation_type == 'restore_backup':
                self.status_updated.emit("Yedek geri yükleniyor...")
                self.progress_updated.emit(20)
                
                result = self.import_export_system.restore_from_backup(
                    self.parameters.get('backup_path'),
                    self.parameters.get('restore_options', {})
                )
                
                self.progress_updated.emit(100)
                self.operation_completed.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(str(e))

class ImportExportDialog(QDialog):
    """Data import/export system dialog."""
    
    def __init__(self, import_export_system, parent=None):
        super().__init__(parent)
        self.import_export_system = import_export_system
        
        self.setWindowTitle("Veri İçe/Dışa Aktarım Sistemi")
        self.setWindowIcon(qta.icon('fa5s.exchange-alt'))
        self.resize(1000, 700)
        self.setModal(True)
        
        self.setup_ui()
        self.load_backup_list()

    def setup_ui(self):
        """Setup the main UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Veri İçe/Dışa Aktarım ve Yedekleme")
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(header_label)
        
        # Refresh button
        refresh_btn = QPushButton("Yenile")
        refresh_btn.setIcon(qta.icon('fa5s.sync-alt'))
        refresh_btn.clicked.connect(self.load_backup_list)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Excel Import/Export tab
        excel_tab = self.create_excel_tab()
        self.tabs.addTab(excel_tab, qta.icon('fa5s.file-excel'), "Excel")
        
        # CSV Import/Export tab
        csv_tab = self.create_csv_tab()
        self.tabs.addTab(csv_tab, qta.icon('fa5s.file-csv'), "CSV")
        
        # Backup/Restore tab
        backup_tab = self.create_backup_tab()
        self.tabs.addTab(backup_tab, qta.icon('fa5s.database'), "Yedekleme")
        
        # Data Validation tab
        validation_tab = self.create_validation_tab()
        self.tabs.addTab(validation_tab, qta.icon('fa5s.check-circle'), "Doğrulama")
        
        layout.addWidget(self.tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Hazır")
        layout.addWidget(self.status_label)

    def create_excel_tab(self):
        """Create Excel import/export tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export section
        export_group = QGroupBox("Excel Dışa Aktarım")
        export_layout = QFormLayout(export_group)
        
        # Table selection
        self.excel_export_tables = QListWidget()
        self.excel_export_tables.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Add table items
        tables = ['containers', 'ships', 'container_lifecycle', 'notifications', 'transport_plans']
        for table in tables:
            item = QListWidgetItem(table.title())
            item.setData(Qt.ItemDataRole.UserRole, table)
            item.setCheckState(Qt.CheckState.Checked)
            self.excel_export_tables.addItem(item)
        
        export_layout.addRow("Tablolar:", self.excel_export_tables)
        
        excel_export_btn = QPushButton("Excel Dosyasına Dışa Aktar")
        excel_export_btn.setIcon(qta.icon('fa5s.download'))
        excel_export_btn.clicked.connect(self.export_to_excel)
        export_layout.addRow(excel_export_btn)
        
        layout.addWidget(export_group)
        
        # Import section
        import_group = QGroupBox("Excel İçe Aktarım")
        import_layout = QFormLayout(import_group)
        
        # File selection
        self.excel_import_file = QLineEdit()
        excel_file_btn = QPushButton("Dosya Seç")
        excel_file_btn.clicked.connect(self.select_excel_import_file)
        
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.excel_import_file)
        file_layout.addWidget(excel_file_btn)
        import_layout.addRow("Excel Dosyası:", file_layout)
        
        excel_import_btn = QPushButton("Excel Dosyasından İçe Aktar")
        excel_import_btn.setIcon(qta.icon('fa5s.upload'))
        excel_import_btn.clicked.connect(self.import_from_excel)
        import_layout.addRow(excel_import_btn)
        
        layout.addWidget(import_group)
        
        return tab

    def create_csv_tab(self):
        """Create CSV import/export tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export section
        export_group = QGroupBox("CSV Dışa Aktarım")
        export_layout = QFormLayout(export_group)
        
        # Table selection
        self.csv_table_combo = QComboBox()
        self.csv_table_combo.addItems(['containers', 'ships', 'container_lifecycle', 'notifications', 'transport_plans'])
        export_layout.addRow("Tablo:", self.csv_table_combo)
        
        # Delimiter selection
        self.csv_delimiter_combo = QComboBox()
        self.csv_delimiter_combo.addItems([',', ';', '\t'])
        export_layout.addRow("Ayırıcı:", self.csv_delimiter_combo)
        
        csv_export_btn = QPushButton("CSV Dosyasına Dışa Aktar")
        csv_export_btn.setIcon(qta.icon('fa5s.download'))
        csv_export_btn.clicked.connect(self.export_to_csv)
        export_layout.addRow(csv_export_btn)
        
        layout.addWidget(export_group)
        
        # Import section
        import_group = QGroupBox("CSV İçe Aktarım")
        import_layout = QFormLayout(import_group)
        
        # File selection
        self.csv_import_file = QLineEdit()
        csv_file_btn = QPushButton("Dosya Seç")
        csv_file_btn.clicked.connect(self.select_csv_import_file)
        
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.csv_import_file)
        file_layout.addWidget(csv_file_btn)
        import_layout.addRow("CSV Dosyası:", file_layout)
        
        # Target table
        self.csv_import_table_combo = QComboBox()
        self.csv_import_table_combo.addItems(['containers', 'ships', 'container_lifecycle', 'notifications'])
        import_layout.addRow("Hedef Tablo:", self.csv_import_table_combo)
        
        # Delimiter for import
        self.csv_import_delimiter_combo = QComboBox()
        self.csv_import_delimiter_combo.addItems([',', ';', '\t'])
        import_layout.addRow("Ayırıcı:", self.csv_import_delimiter_combo)
        
        csv_import_btn = QPushButton("CSV Dosyasından İçe Aktar")
        csv_import_btn.setIcon(qta.icon('fa5s.upload'))
        csv_import_btn.clicked.connect(self.import_from_csv)
        import_layout.addRow(csv_import_btn)
        
        layout.addWidget(import_group)
        
        return tab

    def create_backup_tab(self):
        """Create backup/restore tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Splitter for backup creation and list
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Backup operations
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create backup section
        create_group = QGroupBox("Yedek Oluştur")
        create_layout = QFormLayout(create_group)
        
        self.backup_name_edit = QLineEdit()
        self.backup_name_edit.setPlaceholderText(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        create_layout.addRow("Yedek Adı:", self.backup_name_edit)
        
        create_backup_btn = QPushButton("Tam Yedek Oluştur")
        create_backup_btn.setIcon(qta.icon('fa5s.save'))
        create_backup_btn.clicked.connect(self.create_backup)
        create_layout.addRow(create_backup_btn)
        
        left_layout.addWidget(create_group)
        
        # Restore options
        restore_group = QGroupBox("Geri Yükleme Seçenekleri")
        restore_layout = QFormLayout(restore_group)
        
        self.clear_existing_check = QCheckBox("Mevcut verileri temizle")
        restore_layout.addRow(self.clear_existing_check)
        
        self.backup_existing_check = QCheckBox("Önce mevcut verileri yedekle")
        self.backup_existing_check.setChecked(True)
        restore_layout.addRow(self.backup_existing_check)
        
        left_layout.addWidget(restore_group)
        left_layout.addStretch()
        
        splitter.addWidget(left_panel)
        
        # Right panel - Backup list
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        backup_list_label = QLabel("Mevcut Yedekler")
        backup_list_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(backup_list_label)
        
        self.backup_list_table = QTableWidget()
        self.backup_list_table.setColumnCount(4)
        self.backup_list_table.setHorizontalHeaderLabels(["Ad", "Boyut", "Tarih", "İşlemler"])
        self.backup_list_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.backup_list_table)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        return tab

    def create_validation_tab(self):
        """Create data validation tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Validation controls
        controls_group = QGroupBox("Veri Doğrulama")
        controls_layout = QFormLayout(controls_group)
        
        self.validation_table_combo = QComboBox()
        self.validation_table_combo.addItems(['containers', 'ships', 'container_lifecycle', 'notifications'])
        controls_layout.addRow("Tablo:", self.validation_table_combo)
        
        validate_btn = QPushButton("Veri Bütünlüğünü Doğrula")
        validate_btn.setIcon(qta.icon('fa5s.check'))
        validate_btn.clicked.connect(self.validate_data)
        controls_layout.addRow(validate_btn)
        
        layout.addWidget(controls_group)
        
        # Results display
        self.validation_results = QTextEdit()
        self.validation_results.setReadOnly(True)
        layout.addWidget(self.validation_results)
        
        return tab

    def select_excel_import_file(self):
        """Select Excel file for import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.excel_import_file.setText(file_path)

    def select_csv_import_file(self):
        """Select CSV file for import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CSV Dosyası Seç", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.csv_import_file.setText(file_path)

    def export_to_excel(self):
        """Export selected tables to Excel."""
        # Get selected tables
        selected_tables = []
        for i in range(self.excel_export_tables.count()):
            item = self.excel_export_tables.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tables.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not selected_tables:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir tablo seçin.")
            return
        
        # Get output file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyası Kaydet", f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            self.start_operation('export_excel', {
                'output_path': file_path,
                'tables': selected_tables
            })

    def import_from_excel(self):
        """Import data from Excel file."""
        file_path = self.excel_import_file.text().strip()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir Excel dosyası seçin.")
            return
        
        self.start_operation('import_excel', {
            'file_path': file_path
        })

    def export_to_csv(self):
        """Export table to CSV."""
        table_name = self.csv_table_combo.currentText()
        delimiter = self.csv_delimiter_combo.currentText()
        
        # Get output file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSV Dosyası Kaydet", f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            self.start_operation('export_csv', {
                'table_name': table_name,
                'output_path': file_path,
                'delimiter': delimiter
            })

    def import_from_csv(self):
        """Import data from CSV file."""
        file_path = self.csv_import_file.text().strip()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir CSV dosyası seçin.")
            return
        
        table_name = self.csv_import_table_combo.currentText()
        delimiter = self.csv_import_delimiter_combo.currentText()
        
        self.start_operation('import_csv', {
            'file_path': file_path,
            'table_name': table_name,
            'delimiter': delimiter
        })

    def create_backup(self):
        """Create full database backup."""
        backup_name = self.backup_name_edit.text().strip()
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.start_operation('create_backup', {
            'backup_name': backup_name
        })

    def restore_backup(self, backup_path):
        """Restore from backup."""
        restore_options = {
            'clear_existing': self.clear_existing_check.isChecked(),
            'backup_existing': self.backup_existing_check.isChecked()
        }
        
        reply = QMessageBox.question(
            self, "Yedek Geri Yükleme",
            f"Bu işlem mevcut verileri etkileyebilir. Devam etmek istiyor musunuz?\n\n"
            f"Mevcut veriler temizlenecek: {'Evet' if restore_options['clear_existing'] else 'Hayır'}\n"
            f"Önce yedek oluşturulacak: {'Evet' if restore_options['backup_existing'] else 'Hayır'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_operation('restore_backup', {
                'backup_path': backup_path,
                'restore_options': restore_options
            })

    def validate_data(self):
        """Validate data integrity for selected table."""
        table_name = self.validation_table_combo.currentText()
        
        try:
            result = self.import_export_system.validate_data_integrity(table_name)
            
            # Display results
            if result.get('valid', False):
                self.validation_results.setText(f"""
Tablo: {result['table_name']}
Toplam Kayıt: {result['total_records']}
Bütünlük Skoru: {result['integrity_score']}/100
Durum: ✅ Geçerli

Tüm veriler bütünlük kurallarına uygun.
                """)
            else:
                null_violations = result.get('null_violations', {})
                violations_text = "\n".join([f"- {col}: {count} null değer" for col, count in null_violations.items()])
                
                self.validation_results.setText(f"""
Tablo: {result['table_name']}
Toplam Kayıt: {result['total_records']}
Bütünlük Skoru: {result['integrity_score']}/100
Durum: ⚠️ Sorunlu

Tespit Edilen Sorunlar:
{violations_text}
                """)
                
        except Exception as e:
            self.validation_results.setText(f"Doğrulama hatası: {str(e)}")

    def load_backup_list(self):
        """Load list of available backups."""
        try:
            backups = self.import_export_system.get_backup_list()
            
            self.backup_list_table.setRowCount(len(backups))
            
            for row, backup in enumerate(backups):
                # Name
                name_item = QTableWidgetItem(backup['name'])
                self.backup_list_table.setItem(row, 0, name_item)
                
                # Size
                size_mb = backup['size'] / (1024 * 1024)
                size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
                self.backup_list_table.setItem(row, 1, size_item)
                
                # Date
                created_at = backup['created_at']
                if isinstance(created_at, str):
                    # If created_at is a string (from backup_info.json), try to parse it
                    try:
                        if 'T' in created_at:
                            # ISO format
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            # Try other common formats
                            created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # If parsing fails, use current time
                        created_at = datetime.now()
                
                date_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                date_item = QTableWidgetItem(date_str)
                self.backup_list_table.setItem(row, 2, date_item)
                
                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(5, 2, 5, 2)
                
                restore_btn = QPushButton("Geri Yükle")
                restore_btn.setIcon(qta.icon('fa5s.upload'))
                restore_btn.clicked.connect(lambda checked, path=backup['file_path']: self.restore_backup(path))
                actions_layout.addWidget(restore_btn)
                
                delete_btn = QPushButton("Sil")
                delete_btn.setIcon(qta.icon('fa5s.trash'))
                delete_btn.clicked.connect(lambda checked, name=backup['name']: self.delete_backup(name))
                actions_layout.addWidget(delete_btn)
                
                self.backup_list_table.setCellWidget(row, 3, actions_widget)
            
            # Adjust column widths
            self.backup_list_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Yedek listesi yüklenirken hata: {str(e)}")

    def delete_backup(self, backup_name):
        """Delete a backup."""
        reply = QMessageBox.question(
            self, "Yedek Silme",
            f"'{backup_name}' yedeğini silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.import_export_system.delete_backup(backup_name)
            if success:
                QMessageBox.information(self, "Başarılı", "Yedek başarıyla silindi.")
                self.load_backup_list()
            else:
                QMessageBox.warning(self, "Hata", "Yedek silinemedi.")

    def start_operation(self, operation_type, parameters):
        """Start background operation."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("İşlem başlatılıyor...")
        
        self.operation_thread = ImportExportThread(
            self.import_export_system,
            operation_type,
            parameters
        )
        
        self.operation_thread.progress_updated.connect(self.progress_bar.setValue)
        self.operation_thread.status_updated.connect(self.status_label.setText)
        self.operation_thread.operation_completed.connect(self.on_operation_completed)
        self.operation_thread.error_occurred.connect(self.on_error)
        
        self.operation_thread.start()

    def on_operation_completed(self, result):
        """Handle operation completion."""
        self.progress_bar.setVisible(False)
        success = result.get('success', False)
        operation_type = result.get('type', 'unknown')
        
        if success:
            if operation_type == 'export_excel':
                self.status_label.setText("Excel dışa aktarımı tamamlandı")
                QMessageBox.information(self, "Başarılı", "Excel dosyası başarıyla oluşturuldu.")
            elif operation_type == 'export_csv':
                self.status_label.setText("CSV dışa aktarımı tamamlandı")
                QMessageBox.information(self, "Başarılı", "CSV dosyası başarıyla oluşturuldu.")
            elif operation_type == 'create_backup':
                self.status_label.setText("Yedek oluşturma tamamlandı")
                QMessageBox.information(self, "Başarılı", "Veritabanı yedeği başarıyla oluşturuldu.")
                self.load_backup_list()
            elif 'import' in operation_type or 'restore' in operation_type:
                imported_count = result.get('imported_count', result.get('total_restored', 0))
                self.status_label.setText(f"İçe aktarım tamamlandı: {imported_count} kayıt")
                
                # Show detailed results
                self.show_import_results(result)
        else:
            error_msg = result.get('error', 'Bilinmeyen hata')
            self.status_label.setText(f"İşlem başarısız: {error_msg}")
            QMessageBox.warning(self, "Hata", f"İşlem başarısız:\n{error_msg}")

    def show_import_results(self, result):
        """Show detailed import results."""
        if 'imported_tables' in result:
            # Backup restore results
            tables = result['imported_tables']
            total = result.get('total_restored', 0)
            errors = result.get('errors', [])
            
            message = f"Geri yükleme tamamlandı!\n\nToplam geri yüklenen kayıt: {total}\n\n"
            message += "Tablo detayları:\n"
            for table, count in tables.items():
                message += f"- {table}: {count} kayıt\n"
            
            if errors:
                message += f"\nHatalar ({len(errors)}):\n"
                for error in errors[:5]:  # Show first 5 errors
                    message += f"- {error}\n"
                if len(errors) > 5:
                    message += f"... ve {len(errors) - 5} hata daha"
        
        else:
            # Regular import results
            imported_count = result.get('imported_count', 0)
            skipped_rows = result.get('skipped_rows', 0)
            errors = result.get('errors', [])
            
            message = f"İçe aktarım tamamlandı!\n\n"
            message += f"Başarıyla içe aktarılan: {imported_count} kayıt\n"
            message += f"Atlanan satır: {skipped_rows}\n"
            
            if errors:
                message += f"\nHatalar ({len(errors)}):\n"
                for error in errors[:5]:  # Show first 5 errors
                    message += f"- {error}\n"
                if len(errors) > 5:
                    message += f"... ve {len(errors) - 5} hata daha"
        
        QMessageBox.information(self, "İçe Aktarım Sonuçları", message)

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
