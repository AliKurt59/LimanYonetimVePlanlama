from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QPushButton

class ContainerDetailDialog(QDialog):
    """
    Bir konteynerin detaylarını gösteren standart diyalog kutusu.
    """
    def __init__(self, container_data, location_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Konteyner Detayları: {container_data.get('id', 'N/A')}")
        self.setMinimumWidth(350)

        layout = QFormLayout(self)
        layout.addRow("Konteyner ID:", QLabel(container_data.get('id', 'N/A')))
        layout.addRow("Türü:", QLabel(container_data.get('tip', 'N/A')))
        
        # 'durum' bilgisi her zaman olmayabilir, varsayılan değer ekleyelim
        status = container_data.get('durum', 'Bilinmiyor')
        if not status: # Eğer durum None veya boş ise
            status = 'Bilinmiyor'
        layout.addRow("Durumu:", QLabel(status))
        
        layout.addRow("Mevcut Konum:", QLabel(location_str))
        layout.addRow("Çıkış Limanı:", QLabel(container_data.get('cikis_limani', 'N/A')))
        layout.addRow("Varış Limanı:", QLabel(container_data.get('varis_limani', 'N/A')))

        entry_date = container_data.get('giris_tarihi')
        if entry_date:
            # Gelen verinin str mi datetime mı olduğunu kontrol et
            if hasattr(entry_date, 'strftime'):
                layout.addRow("Giriş Tarihi:", QLabel(entry_date.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                 layout.addRow("Giriş Tarihi:", QLabel(str(entry_date)))

        close_button = QPushButton("Kapat")
        close_button.clicked.connect(self.accept)
        layout.addRow(close_button)