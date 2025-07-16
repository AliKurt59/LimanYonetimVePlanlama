# config_manager.py

import json
import os
from PyQt6.QtGui import QColor

# Çevre değişkenlerini yükle (isteğe bağlı)
ENV_LOADED = False

def load_environment_variables():
    """Çevre değişkenlerini yükler (dotenv paketi varsa)."""
    global ENV_LOADED
    try:
        # .env dosyasını manuel olarak oku
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
            ENV_LOADED = True
            print("✅ .env dosyası manuel olarak yüklendi")
        else:
            ENV_LOADED = False
            print("📝 .env dosyası bulunamadı, sistem çevre değişkenleri kullanılacak")
    except Exception as e:
        ENV_LOADED = False
        print(f"⚠️  .env dosyası yüklenemedi: {e}")

# Başlangıçta yükle
load_environment_variables()

def get_env_var(key, default=""):
    """Çevre değişkenini güvenli bir şekilde al."""
    return os.getenv(key, default)

# Varsayılan ayarlar
DEFAULT_CONFIG = {
    "database": {
        "dbname": get_env_var("DB_NAME", "liman_yonetim_db_v2"),
        "user": get_env_var("DB_USER", "postgres"),
        "password": get_env_var("DB_PASSWORD", ""),
        "host": get_env_var("DB_HOST", "localhost"),
        "port": get_env_var("DB_PORT", "5432")
    },
    "theme": get_env_var("APP_THEME", "dark"), # YENİ: Tema ayarı eklendi (dark/light)
    "colors": {
        "filled": "#e74c3c",
        "pending": "#f1c40f",
        "placeable": "#2ecc71",
        "incompatible": "#e67e22",
        "empty": "#bdc3c7",
        "reefer": "#3498db" 
    }
}

CONFIG_FILE = "config.json"

def get_config():
    """Yapılandırma dosyasını okur, yoksa varsayılanlarla oluşturur."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Eğer tema ayarı eski config'de yoksa ekle
            if 'theme' not in config:
                config['theme'] = 'dark'
            return config
    except (json.JSONDecodeError, IOError):
        # Dosya bozuksa varsayılanı döndür
        return DEFAULT_CONFIG

def save_config(config_data):
    """Yapılandırma verisini dosyaya kaydeder."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    except IOError:
        return False

def get_color(name):
    """Belirtilen isimdeki rengi yapılandırmadan QColor olarak alır."""
    config = get_config()
    hex_color = config.get("colors", {}).get(name, DEFAULT_CONFIG["colors"][name])
    return QColor(hex_color)