# Port Management System

A comprehensive port and container management system built with PyQt6 and PostgreSQL.

## 🚢 Features

### Container Management
- Container lifecycle tracking
- Real-time container status monitoring
- Container placement and movement
- Import/export functionality

### Ship Planning
- Ship berth management
- Container loading/unloading planning
- Ship capacity optimization
- Departure/arrival scheduling

### Transport Management
- Transport planning and scheduling
- Route optimization
- Transport status tracking
- Destination management

### Reporting & Analytics
- Performance metrics dashboard
- Container utilization reports
- Ship efficiency analytics
- Export capabilities

### Advanced Features
- **Offline Mode**: Works without PostgreSQL connection
- **Theme Support**: Dark/Light theme switching
- **Data Export/Import**: Comprehensive backup system
- **Performance Optimization**: Caching and query optimization
- **Logging System**: Detailed audit trails

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+ (optional for offline mode)
- pip package manager

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/port-management-system.git
cd port-management-system
```

2. **Create virtual environment:**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. **Run the application:**
```bash
python main.py
```

## 📋 Configuration

### Database Setup (Optional)
If you want to use PostgreSQL:

1. Install PostgreSQL
2. Create database: `CREATE DATABASE liman_yonetim_db_v2;`
3. Configure `.env` file with your credentials

### Offline Mode
The application automatically switches to offline mode if PostgreSQL is not available.

## 🎨 Usage

### Basic Operations
1. **Container Management**: Add, edit, and track containers
2. **Ship Planning**: Plan ship loading/unloading operations
3. **Transport Planning**: Schedule and manage transport operations
4. **Reporting**: Generate performance and utilization reports

### Advanced Features
- **Import/Export**: Backup and restore data
- **Theme Switching**: Toggle between dark and light themes
- **Performance Monitoring**: View system performance metrics

## 🔧 Technical Details

### Architecture
- **Frontend**: PyQt6 with modern UI components
- **Backend**: Python with PostgreSQL/SQLite
- **Data Layer**: ORM-like database abstraction
- **Caching**: Redis-like in-memory caching


