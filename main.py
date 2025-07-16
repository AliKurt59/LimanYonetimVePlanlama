# main.py

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
import qdarkstyle

# Offline mode kontrolü
OFFLINE_MODE = False
try:
    from offline_mode import OFFLINE_MODE as OFFLINE_MODE_SETTING, create_offline_config
    OFFLINE_MODE = OFFLINE_MODE_SETTING
    
    if OFFLINE_MODE:
        print("🎭 Başlatılıyor: Offline Mode (PostgreSQL gerektirmez)")
        create_offline_config()
    else:
        print("🗄️  Başlatılıyor: Online Mode (PostgreSQL gerekli)")
        # PostgreSQL bağlantısını test et
        try:
            from database import DatabaseConnection
            test_db = DatabaseConnection()
            print("✅ PostgreSQL bağlantısı başarılı")
        except Exception as db_error:
            print(f"❌ PostgreSQL bağlantı hatası: {db_error}")
            print("🎭 Offline mode'a geçiliyor...")
            OFFLINE_MODE = True
            create_offline_config()
except ImportError:
    print("🗄️  Başlatılıyor: Normal Mode")

import config_manager
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    try:
        main_window = MainWindow()
        
        # YENİ: Başlangıçta temayı uygula
        config = config_manager.get_config()
        initial_theme = config.get("theme", "dark")
        main_window.apply_theme(initial_theme)
        
        if OFFLINE_MODE:
            # Offline mode bilgilendirmesi
            QMessageBox.information(
                main_window,
                "🎭 Offline Mode Aktif",
                "Uygulama offline modda çalışıyor.\n\n"
                "✅ Tüm özellikler demo verilerle çalışacak\n"
                "✅ PostgreSQL gerekmez\n"
                "✅ Container Lifecycle sistemi aktif\n\n"
                "PostgreSQL bağlantısı kurulamadığı için\n"
                "otomatik olarak offline mode aktif edildi.\n\n"
                "Gerçek verilerle çalışmak için:\n"
                "1. PostgreSQL servisini başlatın\n"
                "2. Veritabanı ayarlarını kontrol edin (config.json)\n"
                "3. Uygulamayı yeniden başlatın"
            )
        else:
            # Online mode başarılı
            QMessageBox.information(
                main_window,
                "🗄️ Online Mode Aktif",
                "✅ PostgreSQL bağlantısı başarılı!\n\n"
                "Gerçek verilerle çalışıyorsunuz."
            )
        
        main_window.show()
        
        # YENİ: Pencere gösterildikten sonra layout düzelt
        from PyQt6.QtCore import QTimer
        def final_layout_fix():
            try:
                main_window.updateGeometry()
                main_window.update()
            except Exception as e:
                pass
        
        QTimer.singleShot(150, final_layout_fix)
        
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = f"Uygulama başlatma hatası: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Hata durumunda PyQt varsa dialog göster
        try:
            QMessageBox.critical(None, "Başlatma Hatası", 
                               f"{error_msg}\n\nOffline mode için 'offline_mode.py' çalıştırın.")
        except:
            pass
        
        sys.exit(1)