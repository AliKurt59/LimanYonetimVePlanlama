# ui/main_window.py (Yeniden Tasarlanmış Ayarlar)

from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QDialog, QVBoxLayout, 
                             QFormLayout, QPushButton, QMessageBox, QComboBox, QToolBar, QWidget, QSizePolicy, QApplication)
from PyQt6.QtGui import QAction
import qtawesome as qta
import qdarkstyle
import sys
import os

import config_manager
from database import DatabaseConnection
from ui.port_yard_tab import PortYardTab
from ui.ship_planning_tab import ShipPlanningTab
from ui.transport_tab import TransportTab
from ui.reporting_tab import ReportingTab
from ui.ship_management_tab import ShipManagementTab
from ui.container_management_tab import ContainerManagementTab

# Global değişkenleri başlangıçta tanımla
LIFECYCLE_TAB_AVAILABLE = False
ADVANCED_FEATURES_AVAILABLE = False

# Yeni tab'ı import et
try:
    from ui.container_lifecycle_tab import ContainerLifecycleTab
    LIFECYCLE_TAB_AVAILABLE = True
except ImportError:
    print("⚠️  Container Lifecycle Tab henüz mevcut değil.")

# YENİ: Gelişmiş özellikler için import'lar
ADVANCED_FEATURES_AVAILABLE = False
try:
    from data_import_export import DataImportExport
    ADVANCED_FEATURES_AVAILABLE = True
    print("✅ Gelişmiş özellik modülleri başarıyla import edildi")
except ImportError as e:
    print(f"⚠️  Gelişmiş özellikler henüz mevcut değil: {e}")
    ADVANCED_FEATURES_AVAILABLE = False

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(300)
        self.config = config_manager.get_config()
        self.main_window = parent
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # YENİ: Tema Seçimi
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Koyu Tema", "Açık Tema"])
        current_theme = self.config.get("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self.apply_theme_instantly)
        form_layout.addRow("Uygulama Teması:", self.theme_combo)

        layout.addLayout(form_layout)
        
        save_button = QPushButton("Tamam")
        save_button.clicked.connect(self.save_and_close)
        layout.addWidget(save_button)
        
    def apply_theme_instantly(self):
        selected_theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"
        self.config["theme"] = selected_theme
        config_manager.save_config(self.config)
        
        # Ana pencereye tema değişikliğini uygula
        if self.main_window:
            self.main_window.apply_theme(selected_theme)
        
    def save_and_close(self):
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseConnection()
        
        # YENİ: Gelişmiş özellik sistemlerini başlat
        self.advanced_systems = {}
        if ADVANCED_FEATURES_AVAILABLE:
            try:
                self.advanced_systems['import_export'] = DataImportExport(self.db)
                print("✅ Data Import/Export yüklendi")
                
                print("✅ Gelişmiş özellikler başarıyla yüklendi")
            except Exception as e:
                print(f"⚠️  Gelişmiş özellikler yüklenirken hata: {e}")
                import traceback
                traceback.print_exc()
                # Gelişmiş özellikler yüklenemezse sistem yine de çalışmalı
        else:
            print("⚠️  ADVANCED_FEATURES_AVAILABLE = False - Gelişmiş özellikler yüklenmeyecek")
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Liman Yönetim ve Planlama Sistemi v2.5 ")
        self.setWindowIcon(qta.icon('fa5s.anchor'))
        self.setGeometry(100, 100, 1400, 900)

        if not self.db.conn:
            QMessageBox.critical(self, "Veritabanı Hatası", "Veritabanı bağlantısı kurulamadı. Lütfen config.json dosyasını kontrol edin.")
            # Uygulamanın daha fazla ilerlemesini engellemek iyi bir fikir olabilir
            # sys.exit()

        ### DÜZELTME: Menü çubuğu yerine araç çubuğu ###
        toolbar = QToolBar("Ana Araç Çubuğu")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # YENİ: Gelişmiş özellikler için araç çubuğu butonları
        if ADVANCED_FEATURES_AVAILABLE:
            # Data Import/Export
            import_export_action = QAction(qta.icon('fa5s.exchange-alt', color='lightblue'), "Veri İçe/Dışa Aktarım", self)
            import_export_action.triggered.connect(self.show_import_export)
            toolbar.addAction(import_export_action)
            
            toolbar.addSeparator()

        # Butonu sağa yaslamak için bir ayırıcı (spacer) ekle
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)

        settings_action = QAction(qta.icon('fa5s.cog', color='white'), "Ayarlar", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Sekmeleri oluştur
        self.port_yard_tab = PortYardTab(self.db, self)
        self.ship_planning_tab = ShipPlanningTab(self.db, self)
        self.transport_tab = TransportTab(self.db, self)
        self.container_management_tab = ContainerManagementTab(self.db, self)
        self.ship_management_tab = ShipManagementTab(self.db, self)
        self.reporting_tab = ReportingTab(self.db)
        
        # Yeni lifecycle tab'ını ekle
        if LIFECYCLE_TAB_AVAILABLE:
            self.container_lifecycle_tab = ContainerLifecycleTab(self.db)

        self.tabs.addTab(self.port_yard_tab, qta.icon('fa5s.th-large', color='orange'), "Saha Planı")
        self.tabs.addTab(self.ship_planning_tab, qta.icon('fa5s.ship', color='lightblue'), "Gemi Planlama")
        self.tabs.addTab(self.transport_tab, qta.icon('fa5s.truck', color='lightgreen'), "Taşıma Planlama")
        self.tabs.addTab(self.container_management_tab, qta.icon('fa5s.box-open', color='brown'), "Konteyner Yönetimi")
        self.tabs.addTab(self.ship_management_tab, qta.icon('fa5s.anchor', color='purple'), "Gemi Yönetimi")
        self.tabs.addTab(self.reporting_tab, qta.icon('fa5s.chart-bar', color='yellow'), "Raporlama")
        
        # Lifecycle tab'ını ekle
        if LIFECYCLE_TAB_AVAILABLE:
            self.tabs.addTab(self.container_lifecycle_tab, qta.icon('fa5s.recycle', color='cyan'), "Konteyner Döngüsü")
        
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # YENİ: Ana pencere gösterildikten sonra düzeltme
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self.force_tab_refresh)
        
    def force_tab_refresh(self):
        """Sekme boyutlarını zorla düzelt"""
        try:
            # Ana pencere minimum boyutunu belirle
            self.setMinimumSize(1200, 800)
            
            # Her tab için minimum boyut ayarla
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if widget:
                    widget.setMinimumSize(1000, 600)
                    widget.updateGeometry()
            
            # Tab widget'ını güncelle
            self.tabs.updateGeometry()
            self.updateGeometry()
            
            print("✅ Tab boyutları zorla düzeltildi")
            
        except Exception as e:
            print(f"⚠️  Tab düzeltme hatası: {e}")
        
    def apply_theme(self, theme):
        """Anlık tema değişikliği uygula"""
        app = QApplication.instance()
        
        if theme == "dark":
            app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
            custom_style = """
                QPushButton, QPushButton:disabled {
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 14px;
                    min-height: 32px;
                    line-height: 20px;
                    color: #E0E0E0;
                    background-color: #223;
                    border: 1px solid #444;
                    text-align: left;
                    padding-left: 16px;
                    font-weight: 500;
                }
                QListWidget::item:selected, QTableWidget::item:selected {
                    background-color: #5DADE2;
                    color: white;
                }
            """
        else:  # light theme
            custom_style = """
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background-color: white;
                }
                QTabBar::tab {
                    background-color: #e0e0e0;
                    color: #333333;
                    padding: 8px 16px;
                    margin: 2px;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-bottom: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-size: 14px;
                    color: #333333;
                    min-height: 32px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-color: #0078d4;
                }
                QPushButton:pressed {
                    background-color: #e6e6e6;
                }
                QLineEdit, QComboBox {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 6px;
                    color: #333333;
                }
                QLineEdit:focus, QComboBox:focus {
                    border-color: #0078d4;
                }
                QTableWidget {
                    background-color: #ffffff;
                    alternate-background-color: #f9f9f9;
                    gridline-color: #e0e0e0;
                    color: #333333;
                }
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QListWidget {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    color: #333333;
                }
                QListWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QLabel {
                    color: #333333;
                }
                QToolBar {
                    background-color: #ffffff;
                    border-bottom: 1px solid #cccccc;
                }
                QMenuBar {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    color: #333333;
                }
                QGraphicsView {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                }
            """
        
        app.setStyleSheet(custom_style)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_import_export(self):
        """Veri içe/dışa aktarım sistemini göster."""
        if ADVANCED_FEATURES_AVAILABLE and 'import_export' in self.advanced_systems:
            from ui.import_export_dialog import ImportExportDialog
            dialog = ImportExportDialog(self.advanced_systems['import_export'], self)
            dialog.exec()
        else:
            QMessageBox.information(self, "Bilgi", "Veri içe/dışa aktarım sistemi henüz mevcut değil.")

    # NOTE: Transport Planning geçici olarak devre dışı (QThread destroyed hatası)
    # def show_transport_planning(self):
    #     """Gelişmiş taşıma planlama sistemini göster."""
    #     QMessageBox.information(self, "Geçici Olarak Devre Dışı", 
    #         "Gelişmiş Taşıma Planlama özelliği şu anda QThread hatası nedeniyle\n"
    #         "geçici olarak devre dışı bırakılmıştır.\n\n"
    #         "Diğer özellikler normal şekilde çalışmaktadır.")

    def refresh_all_tabs(self):
        print("Tüm sekmeler yenileniyor...")
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'refresh_all'): widget.refresh_all()
            elif hasattr(widget, 'refresh_view'): widget.refresh_view()
            elif hasattr(widget, 'refresh_lists'): widget.refresh_lists()
            elif hasattr(widget, 'generate_report'): widget.generate_report()
            elif hasattr(widget, 'refresh_ships_list'): widget.refresh_ships_list()
            elif hasattr(widget, 'refresh_container_list'): widget.refresh_container_list()
            elif hasattr(widget, 'load_data'): widget.load_data()  # Lifecycle tab için
        
    def tab_changed(self, index):
        """Tab değiştiğinde düzeltme yap"""
        try:
            self.refresh_all_tabs()
            
            # Mevcut tab'ı al ve düzelt
            current_widget = self.tabs.currentWidget()
            if current_widget:
                # Widget'ın minimum boyutunu ayarla
                current_widget.setMinimumSize(1000, 600)
                current_widget.updateGeometry()
                
                # Kısa gecikme sonrası yenile
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(10, lambda: current_widget.update())
                
            print(f"✅ Tab değiştirildi: {self.tabs.tabText(index)}")
            
        except Exception as e:
            print(f"⚠️  Tab değişimi hatası: {e}")
    
    def showEvent(self, event):
        """Pencere gösterildiğinde çalışır"""
        super().showEvent(event)
        try:
            # Pencere tamamen yüklendikten sonra düzeltme yap
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.force_tab_refresh)
        except Exception as e:
            print(f"⚠️  Show event hatası: {e}")

    def closeEvent(self, event):
        if self.db:
            self.db.close_connection()
        event.accept()