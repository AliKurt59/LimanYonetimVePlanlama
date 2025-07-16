# ui/reporting_tab.py (Yeni Grafik Eklenmiş ve Hataları Giderilmiş Tam Hali)

import io
from datetime import datetime
import csv 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QDateEdit, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import QDate, Qt
import qtawesome as qta
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader

class ReportingTab(QWidget):
    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.figure = Figure() 
        self.canvas = FigureCanvas(self.figure) 
        self.init_ui()

    def init_ui(self):
        # YENİ: Minimum boyut ayarla
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout(self)
        control_panel = QGridLayout() 
        
        control_panel.addWidget(QLabel("Rapor Türü:"), 0, 0)
        self.report_combo = QComboBox()
        self.report_combo.addItems([
            "Saha Doluluk Oranı", "Gemi Bazında Doluluk Oranı", "Konteyner Tipi Dağılımı", 
            "Liman Trafik Hacmi", "Varış Limanlarına Göre Dağılım", "Araç Kullanım Verileri" 
        ])
        self.report_combo.currentIndexChanged.connect(self.update_filter_options)
        control_panel.addWidget(self.report_combo, 0, 1, 1, 3)
        
        self.start_date_label = QLabel("Başlangıç Tarihi:")
        control_panel.addWidget(self.start_date_label, 1, 0)
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30)) 
        self.start_date_edit.dateChanged.connect(self.generate_report)
        control_panel.addWidget(self.start_date_edit, 1, 1)

        self.end_date_label = QLabel("Bitiş Tarihi:")
        control_panel.addWidget(self.end_date_label, 1, 2)
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(self.generate_report)
        control_panel.addWidget(self.end_date_edit, 1, 3)

        self.filter_combo_label = QLabel("Filtre:")
        control_panel.addWidget(self.filter_combo_label, 2, 0) 
        self.filter_combo = QComboBox(); self.filter_combo.addItem("Tümü")
        self.filter_combo.currentIndexChanged.connect(self.generate_report)
        control_panel.addWidget(self.filter_combo, 2, 1, 1, 3)
        
        self.filter_combo_2_label = QLabel("Filtre 2:")
        control_panel.addWidget(self.filter_combo_2_label, 3, 0)
        self.filter_combo_2 = QComboBox(); self.filter_combo_2.addItem("Tümü")
        self.filter_combo_2.currentIndexChanged.connect(self.generate_report)
        control_panel.addWidget(self.filter_combo_2, 3, 1, 1, 3)

        button_layout = QHBoxLayout()
        self.generate_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Raporu Oluştur")
        self.export_pdf_button = QPushButton(qta.icon('fa5s.file-pdf', color='white'), " PDF Olarak Dışa Aktar")
        self.export_excel_button = QPushButton(qta.icon('fa5s.file-excel', color='white'), " Excel Olarak Dışa Aktar") 
        
        for btn in [self.generate_button, self.export_pdf_button, self.export_excel_button]:
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            button_layout.addWidget(btn)

        self.generate_button.clicked.connect(self.generate_report)
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        self.export_excel_button.clicked.connect(self.export_to_excel)
        
        layout.addLayout(control_panel)
        layout.addLayout(button_layout)
        layout.addWidget(self.canvas) 
        self.update_filter_options() 

    def update_filter_options(self):
        report_type = self.report_combo.currentText()
        self.filter_combo_label.hide(); self.filter_combo.hide(); self.filter_combo.clear(); self.filter_combo.addItem("Tümü")
        self.filter_combo_2_label.hide(); self.filter_combo_2.hide(); self.filter_combo_2.clear(); self.filter_combo_2.addItem("Tümü")
        self.start_date_label.hide(); self.start_date_edit.hide()
        self.end_date_label.hide(); self.end_date_edit.hide()

        try: self.filter_combo.currentIndexChanged.disconnect()
        except TypeError: pass
        self.filter_combo.currentIndexChanged.connect(self.generate_report)

        if report_type == "Gemi Bazında Doluluk Oranı":
            self.filter_combo_label.setText("Gemi Seç:"); self.filter_combo_label.show(); self.filter_combo.show()
            ships = self.db.get_all_ships()
            if ships:
                for ship in ships: self.filter_combo.addItem(f"{ship['gemi_adi']} ({ship['gemi_id']})", ship['gemi_id'])
        elif report_type == "Konteyner Tipi Dağılımı":
            self.filter_combo_label.setText("Yerleşim Yeri:"); self.filter_combo_label.show(); self.filter_combo.show()
            self.filter_combo.addItems(["SAHA", "GEMI", "ATANMAMIS"])
            self.filter_combo.currentIndexChanged.connect(self.on_location_type_changed_for_container_type)
        elif report_type in ["Liman Trafik Hacmi", "Araç Kullanım Verileri"]:
            self.start_date_label.show(); self.start_date_edit.show()
            self.end_date_label.show(); self.end_date_edit.show()
            if report_type == "Liman Trafik Hacmi":
                self.filter_combo_label.setText("Trafik Tipi:"); self.filter_combo_label.show(); self.filter_combo.show(); self.filter_combo.addItems(["Çıkış", "Varış", "Toplam"])
            else:
                self.filter_combo_label.setText("Araç Tipi:"); self.filter_combo_label.show(); self.filter_combo.show()
                vehicle_types = sorted(list(set(v['tip'] for v in self.db.get_vehicles() or []))) 
                self.filter_combo.addItems(vehicle_types)
        
        self.on_location_type_changed_for_container_type()
        self.generate_report()

    def on_location_type_changed_for_container_type(self):
        is_type_dist = (self.report_combo.currentText() == "Konteyner Tipi Dağılımı")
        is_ship_loc = (self.filter_combo.currentText() == "GEMI")
        if is_type_dist and is_ship_loc:
            self.filter_combo_2_label.setText("Gemi Seç (Opsiyonel):"); self.filter_combo_2_label.show(); self.filter_combo_2.show()
            ships = self.db.get_all_ships()
            self.filter_combo_2.blockSignals(True); self.filter_combo_2.clear(); self.filter_combo_2.addItem("Tümü")
            if ships:
                for ship in ships: self.filter_combo_2.addItem(f"{ship['gemi_adi']} ({ship['gemi_id']})", ship['gemi_id'])
            self.filter_combo_2.blockSignals(False)
        else:
            self.filter_combo_2_label.hide(); self.filter_combo_2.hide()

    def generate_report(self):
        if not self.db.conn: return
        report_type = self.report_combo.currentText()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._configure_plot_style(ax)

        start_date = self.start_date_edit.date().toString(Qt.DateFormat.ISODate) 
        end_date = self.end_date_edit.date().toString(Qt.DateFormat.ISODate) 
        
        filter1_data = self.filter_combo.currentData(); filter1_text = self.filter_combo.currentText()
        filter2_data = self.filter_combo_2.currentData()

        data = None
        if report_type == "Saha Doluluk Oranı":
            data = self.db.get_report_data(); self.plot_pie_chart(ax, data.get('occupancy_rate', 0), "Saha Doluluk Oranı")
        elif report_type == "Gemi Bazında Doluluk Oranı":
            data = self.db.get_ship_occupancy_data(ship_id=filter1_data)
            if data and len(data) == 1: self.plot_pie_chart(ax, data[0]['doluluk_orani'], f"{data[0]['gemi_adi']} Doluluk Oranı")
            elif data: self.plot_bar_chart(ax, [d['gemi_adi'] for d in data], [d['doluluk_orani'] for d in data], "Gemi Doluluk Oranları", "Doluluk Oranı (%)")
        elif report_type == "Konteyner Tipi Dağılımı":
            data = self.db.get_container_type_distribution_data(location_type=filter1_text, ship_id=filter2_data)
            if data: self.plot_bar_chart(ax, [d['tip'] for d in data], [d['count'] for d in data], "Konteyner Tipi Dağılımı", "Konteyner Sayısı")
        elif report_type == "Liman Trafik Hacmi":
            data = self.db.get_port_traffic_data(start_date=start_date, end_date=end_date, traffic_type=filter1_text)
            if data: self.plot_bar_chart(ax, [d.get('liman', 'Bilinmiyor') for d in data], [d['count'] for d in data], "Liman Trafik Hacmi", "Konteyner Sayısı")
        elif report_type == "Varış Limanlarına Göre Dağılım":
            data = self.db.get_destination_port_distribution()
            if data: self.plot_bar_chart(ax, [d['varis_limani'] for d in data], [d['count'] for d in data], "Varış Limanlarına Göre Konteyner Dağılımı", "Konteyner Sayısı")
        elif report_type == "Araç Kullanım Verileri":
            data = self.db.get_vehicle_usage_data(start_date=start_date, end_date=end_date, vehicle_type=filter1_text)
            if data:
                # Eğer işlem sayısı sıfırsa (taşıma logu yoksa), araç durumunu göster
                if all(d.get('islem_sayisi', 0) == 0 for d in data):
                    # Araç durumuna göre sınıflandır
                    durum_counts = {}
                    for d in data:
                        durum = d.get('durum', 'BİLİNMİYOR')
                        if durum not in durum_counts:
                            durum_counts[durum] = 0
                        durum_counts[durum] += 1
                    
                    if durum_counts:
                        self.plot_bar_chart(ax, list(durum_counts.keys()), list(durum_counts.values()), 
                                          f"Araç Durumu Dağılımı ({filter1_text})", "Araç Sayısı")
                    else:
                        ax.text(0.5, 0.5, "Bu Rapor İçin Veri Bulunamadı", ha='center', va='center', transform=ax.transAxes, color='white', fontsize=14)
                else:
                    # İşlem sayısına göre göster
                    labels = [f"{d.get('arac_tipi', 'Bilinmiyor')}-{d.get('arac_id', 'N/A')}" for d in data]
                    self.plot_bar_chart(ax, labels, [d['islem_sayisi'] for d in data], 
                                      f"Araç Kullanım İstatistikleri ({filter1_text})", "İşlem Sayısı")
            else:
                ax.text(0.5, 0.5, "Bu Rapor İçin Veri Bulunamadı", ha='center', va='center', transform=ax.transAxes, color='white', fontsize=14)

        if not data: ax.text(0.5, 0.5, "Bu Rapor İçin Veri Bulunamadı", ha='center', va='center', transform=ax.transAxes, color='white', fontsize=14)
        self.canvas.draw()

    def plot_pie_chart(self, ax, value, title):
        value = value or 0
        dolu = min(value, 100); bos = 100 - dolu
        ax.pie([dolu, bos], labels=['Dolu', 'Boş'], autopct='%1.1f%%', startangle=90, colors=['#e74c3c', '#2ecc71'], textprops={'color':"w"})
        ax.set_title(title); ax.axis('equal')

    def plot_bar_chart(self, ax, labels, values, title, ylabel):
        ax.bar(labels, values, color='#3498db')
        ax.set_title(title); ax.set_ylabel(ylabel); ax.tick_params(axis='x', rotation=45)
        self.figure.tight_layout()

    def _configure_plot_style(self, ax):
        ax.set_facecolor('#34495e'); self.figure.set_facecolor('#2c3e50')
        ax.tick_params(axis='x', colors='white'); ax.tick_params(axis='y', colors='white')
        for spine in ax.spines.values(): spine.set_edgecolor('white')
        ax.yaxis.label.set_color('white'); ax.xaxis.label.set_color('white'); ax.title.set_color('white')

    def export_to_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Kaydet", f"Rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", "PDF Dosyaları (*.pdf)")
        if not file_path: return
        try:
            img_data = io.BytesIO()
            self.figure.savefig(img_data, format='png', dpi=300, facecolor=self.figure.get_facecolor(), bbox_inches='tight')
            img_data.seek(0); img_reader = ImageReader(img_data)
            c = pdf_canvas.Canvas(file_path, pagesize=letter); width, height = letter
            c.setFont("Helvetica-Bold", 18); c.drawCentredString(width / 2.0, height - 50, "Liman Yönetim Sistemi Raporu")
            c.setFont("Helvetica", 12); c.drawString(72, height - 80, f"Rapor Türü: {self.report_combo.currentText()}")
            c.drawString(72, height - 100, f"Oluşturma Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            img_width, img_height = 500, 350; img_x = (width - img_width) / 2; img_y = height - 150 - img_height - 50
            c.drawImage(img_reader, img_x, img_y, width=img_width, height=img_height, preserveAspectRatio=True)
            c.save()
            QMessageBox.information(self, "Başarılı", f"Rapor başarıyla '{file_path}' adresine kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken bir hata oluştu:\n{e}")
    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Excel Olarak Kaydet", f"Rapor_Verisi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV Dosyaları (*.csv)")
        if not file_path: return
        # ... (Bu metodun geri kalanı aynı)