import os
import sqlite3
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MySQLError = Exception

DB_TYPE = "mysql"  # 'mysql' or 'sqlite'
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'subscription_db',
    'port': 3306
}
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subscription_system.db')


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        """Determine whether to use MySQL or SQLite."""
        self.engine = "sqlite"
        if MYSQL_AVAILABLE:
            try:
                # Test server connection and create database if needed
                server_conn = mysql.connector.connect(
                    host=MYSQL_CONFIG['host'],
                    user=MYSQL_CONFIG['user'],
                    password=MYSQL_CONFIG['password'],
                    port=MYSQL_CONFIG.get('port', 3306)
                )
                if server_conn.is_connected():
                    cursor = server_conn.cursor()
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}`")
                    cursor.close()
                    server_conn.close()
                    self.engine = "mysql"
            except Exception as e:
                print(f"[Database] MySQL connection failed ({e}). Falling back to SQLite.")
                self.engine = "sqlite"
        else:
            print("[Database] mysql-connector-python not found. Using SQLite.")

    def get_connection(self):
        """Returns an active raw connection."""
        if self.engine == "mysql":
            return mysql.connector.connect(
                host=MYSQL_CONFIG['host'],
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                database=MYSQL_CONFIG['database'],
                port=MYSQL_CONFIG.get('port', 3306)
            )
        else:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    def _normalize_query(self, query):
        """Convert %s placeholders to ? if using SQLite, or preserve %s for MySQL."""
        if self.engine == "sqlite":
            return query.replace("%s", "?")
        return query

    def execute_query(self, query, params=None, commit=True):
        """Execute INSERT, UPDATE, DELETE queries. Returns lastrowid or affected rows."""
        conn = self.get_connection()
        norm_query = self._normalize_query(query)
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(norm_query, params)
            else:
                cursor.execute(norm_query)

            if commit:
                conn.commit()

            last_id = getattr(cursor, 'lastrowid', None)
            row_count = getattr(cursor, 'rowcount', 0)
            cursor.close()
            return last_id if last_id else row_count
        finally:
            conn.close()

    def fetch_all(self, query, params=None):
        """Execute a SELECT query and return list of dictionaries."""
        conn = self.get_connection()
        norm_query = self._normalize_query(query)
        try:
            if self.engine == "mysql":
                cursor = conn.cursor(dictionary=True)
            else:
                cursor = conn.cursor()

            if params:
                cursor.execute(norm_query, params)
            else:
                cursor.execute(norm_query)

            if self.engine == "mysql":
                results = cursor.fetchall()
            else:
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
            cursor.close()
            return results
        finally:
            conn.close()

    def fetch_one(self, query, params=None):
        """Execute a SELECT query and return a single dictionary or None."""
        results = self.fetch_all(query, params)
        return results[0] if results else None


db = DatabaseManager()


def init_db():
    """Initializes schema and seeds initial data if empty."""
    is_mysql = db.engine == "mysql"

    # Table creation statements (Customers, Products, Plans, Variants, Subscriptions, Users, Staff)
    if is_mysql:
        create_tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                reset_token VARCHAR(20) NULL,
                reset_expires_at VARCHAR(50) NULL,
                last_login TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                phone VARCHAR(25),
                company VARCHAR(100),
                address VARCHAR(255),
                city VARCHAR(100),
                postal_code VARCHAR(25),
                membership_tier VARCHAR(20) DEFAULT 'Standard',
                loyalty_points INT DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS staff (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                full_name VARCHAR(100) NOT NULL,
                employee_code VARCHAR(50) NOT NULL UNIQUE,
                department VARCHAR(100) NOT NULL,
                position VARCHAR(100) NOT NULL,
                phone VARCHAR(25),
                created_by INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_code VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(150) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL,
                plan_code VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(150) NOT NULL,
                billing_cycle VARCHAR(30) DEFAULT 'Monthly',
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                currency VARCHAR(10) DEFAULT 'USD',
                trial_days INT DEFAULT 0,
                features TEXT,
                status VARCHAR(20) DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS variants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plan_id INT NOT NULL,
                variant_code VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(150) NOT NULL,
                attribute_type VARCHAR(100) NOT NULL,
                attribute_value VARCHAR(100) NOT NULL,
                price_adjustment DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(20) DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subscription_code VARCHAR(50) NOT NULL UNIQUE,
                customer_id INT NOT NULL,
                product_id INT NOT NULL,
                plan_id INT NOT NULL,
                variant_id INT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                next_billing_date DATE NOT NULL,
                billing_cycle VARCHAR(30) NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(20) DEFAULT 'Active',
                auto_renew TINYINT(1) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
                FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE RESTRICT,
                FOREIGN KEY (variant_id) REFERENCES variants(id) ON DELETE SET NULL
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS taxes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                rate_percentage DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
                is_active TINYINT(1) DEFAULT 1
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS discounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                discount_type VARCHAR(20) NOT NULL,
                value DECIMAL(10, 2) NOT NULL,
                min_purchase DECIMAL(10, 2) DEFAULT 0.00,
                min_quantity INT DEFAULT 0,
                start_date DATE,
                end_date DATE,
                usage_limit INT DEFAULT -1,
                times_used INT DEFAULT 0,
                is_active TINYINT(1) DEFAULT 1
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(50) NOT NULL UNIQUE,
                subscription_id INT NULL,
                customer_id INT NOT NULL,
                invoice_date DATE NOT NULL,
                due_date DATE NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                amount_paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(20) NOT NULL DEFAULT 'Confirmed',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS invoice_lines (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_id INT NOT NULL,
                product_id INT NULL,
                description VARCHAR(255) NOT NULL,
                quantity INT NOT NULL DEFAULT 1,
                unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                line_total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            ) ENGINE=InnoDB;
            """,
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_id INT NOT NULL,
                customer_id INT NOT NULL,
                payment_date DATE NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                transaction_ref VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
            ) ENGINE=InnoDB;
            """
        ]
    else:
        create_tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                reset_token TEXT,
                reset_expires_at TEXT,
                last_login TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                company TEXT,
                address TEXT,
                city TEXT,
                postal_code TEXT,
                membership_tier TEXT DEFAULT 'Standard',
                loyalty_points INTEGER DEFAULT 100,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                employee_code TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                position TEXT NOT NULL,
                phone TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                billing_cycle TEXT DEFAULT 'Monthly',
                price REAL NOT NULL DEFAULT 0.00,
                currency TEXT DEFAULT 'USD',
                trial_days INTEGER DEFAULT 0,
                features TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                variant_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                attribute_type TEXT NOT NULL,
                attribute_value TEXT NOT NULL,
                price_adjustment REAL NOT NULL DEFAULT 0.00,
                status TEXT DEFAULT 'Active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_code TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                variant_id INTEGER NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                next_billing_date TEXT NOT NULL,
                billing_cycle TEXT NOT NULL,
                total_price REAL NOT NULL DEFAULT 0.00,
                status TEXT DEFAULT 'Active',
                auto_renew INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
                FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE RESTRICT,
                FOREIGN KEY (variant_id) REFERENCES variants(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS subscription_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                variant_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                line_total REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS taxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rate_percentage REAL NOT NULL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS discounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                description TEXT,
                discount_type TEXT NOT NULL,
                value REAL NOT NULL,
                min_purchase REAL DEFAULT 0.0,
                min_quantity INTEGER DEFAULT 0,
                start_date TEXT,
                end_date TEXT,
                usage_limit INTEGER DEFAULT -1,
                times_used INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                subscription_id INTEGER,
                customer_id INTEGER NOT NULL,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                discount_amount REAL NOT NULL DEFAULT 0.0,
                total_amount REAL NOT NULL DEFAULT 0.0,
                amount_paid REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS invoice_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                description TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                line_total REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0.0,
                transaction_ref TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
            );
            """
        ]

    for statement in create_tables:
        db.execute_query(statement)

    # In case teammate's customers table already existed without extra columns, add them safely
    ensure_customer_columns()

    # High-performance indexes for < 2.0s SLA
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);",
        "CREATE INDEX IF NOT EXISTS idx_subs_customer ON subscriptions(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status_due ON invoices(status, due_date);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);",
        "CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);"
    ]
    for idx_sql in indexes:
        try:
            db.execute_query(idx_sql)
        except Exception:
            pass

    seed_sample_data()
    print(f"[Database] Initialized successfully using {db.engine.upper()} engine.")


def ensure_customer_columns():
    """Ensure customer table has all required columns for profile and user linkage."""
    columns_to_check = [
        ('user_id', 'INTEGER'),
        ('address', 'TEXT'),
        ('city', 'TEXT'),
        ('postal_code', 'TEXT'),
        ('membership_tier', 'TEXT DEFAULT "Standard"'),
        ('loyalty_points', 'INTEGER DEFAULT 100')
    ]
    for col_name, col_def in columns_to_check:
        try:
            db.execute_query(f"ALTER TABLE customers ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass  # Column already exists


def seed_sample_data():
    """Seeds realistic sample data if the tables are empty."""
    # 0. Seed Users (Admin, Customer, Staff)
    existing_users = db.fetch_all("SELECT COUNT(*) as count FROM users")
    if not existing_users or existing_users[0]['count'] == 0:
        print("[Database] Seeding initial Users (Admin, Customer, Staff)...")
        admin_hash = generate_password_hash('AdminPassword123!')
        customer_hash = generate_password_hash('CustomerPassword123!')
        staff_hash = generate_password_hash('StaffPassword123!')

        # 1. Admin
        db.execute_query(
            "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, %s, 'active')",
            ('admin@brightloop.com', admin_hash, 'admin')
        )
        admin_user = db.fetch_one("SELECT id FROM users WHERE email = %s", ('admin@brightloop.com',))

        # 2. Customer User
        db.execute_query(
            "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, %s, 'active')",
            ('customer@brightloop.com', customer_hash, 'customer')
        )
        cust_user = db.fetch_one("SELECT id FROM users WHERE email = %s", ('customer@brightloop.com',))

        # 3. Staff User
        db.execute_query(
            "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, %s, 'active')",
            ('staff@brightloop.com', staff_hash, 'staff')
        )
        staff_user = db.fetch_one("SELECT id FROM users WHERE email = %s", ('staff@brightloop.com',))

        # Insert default customer profile
        db.execute_query(
            """
            INSERT INTO customers (user_id, name, email, phone, company, address, city, postal_code, membership_tier, loyalty_points)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                cust_user['id'],
                'Jane Doe',
                'customer@brightloop.com',
                '+1 (555) 234-5678',
                'BrightLoop Customer',
                '123 Sunset Boulevard, Apt 4B',
                'San Francisco',
                '94103',
                'Gold',
                450
            )
        )

        # Insert default staff profile (Admin only created)
        db.execute_query(
            """
            INSERT INTO staff (user_id, full_name, employee_code, department, position, phone, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                staff_user['id'],
                'Alex Mercer',
                'BL-STF-001',
                'Customer Support',
                'Operations Lead',
                '+1 (555) 876-5432',
                admin_user['id']
            )
        )

    # Check if products already exist
    existing_products = db.fetch_all("SELECT COUNT(*) as count FROM products")
    if existing_products and existing_products[0]['count'] > 0:
        return

    print("[Database] Seeding sample data for products, plans, variants, and customers...")

    # 1. Seed Customers from teammates
    customers_data = [
        ('Alice Smith', 'alice.smith@brightloop.io', '+1-555-0101', 'Nova Technologies'),
        ('Bob Johnson', 'bob.j@vanguard.co', '+1-555-0102', 'Vanguard Media'),
        ('Carol White', 'carol.w@apexcloud.net', '+1-555-0103', 'Apex Solutions'),
        ('David Miller', 'david.m@pulsecreative.org', '+1-555-0104', 'Pulse Agency'),
        ('Emma Davis', 'emma.davis@globex.com', '+1-555-0105', 'Globex Corporation')
    ]
    for c in customers_data:
        # Check if already present by email
        if not db.fetch_one("SELECT id FROM customers WHERE email = %s", (c[1],)):
            # Also create corresponding customer user so they can log in!
            default_pwd = generate_password_hash('CustomerPassword123!')
            db.execute_query(
                "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, 'customer', 'active')",
                (c[1], default_pwd)
            )
            u = db.fetch_one("SELECT id FROM users WHERE email = %s", (c[1],))
            db.execute_query(
                """
                INSERT INTO customers (user_id, name, email, phone, company, address, city, postal_code, membership_tier, loyalty_points)
                VALUES (%s, %s, %s, %s, %s, '100 Innovation Way', 'San Francisco', '94105', 'Silver', 250)
                """,
                (u['id'], c[0], c[1], c[2], c[3])
            )

    # 2. Seed Products
    products_data = [
        ('PRD-CLOUD', 'CloudSync Pro', 'Cloud Storage', 'Enterprise cloud storage, sync and automated file backup solution.', 'Active'),
        ('PRD-STREAM', 'SoundWave VIP', 'Digital Media', 'Lossless music streaming with offline sync and hi-fi audio.', 'Active'),
        ('PRD-SAAS', 'BrightCRM Suite', 'SaaS Business', 'Full-cycle customer relationship, lead management, and pipeline tracker.', 'Active'),
        ('PRD-SEC', 'CyberShield VPN', 'Cybersecurity', 'High-speed encrypted VPN with dedicated IP and zero-log policy.', 'Active')
    ]
    for p in products_data:
        db.execute_query(
            "INSERT INTO products (product_code, name, category, description, status) VALUES (%s, %s, %s, %s, %s)",
            p
        )

    # Fetch product IDs
    p_map = {row['product_code']: row['id'] for row in db.fetch_all("SELECT id, product_code FROM products")}

    # 3. Seed Plans
    plans_data = [
        # CloudSync Pro
        (p_map['PRD-CLOUD'], 'PLN-CLOUD-M', 'CloudSync Starter Monthly', 'Monthly', 9.99, 'USD', 14, '500GB Storage, 2 Devices, Basic Support', 'Active'),
        (p_map['PRD-CLOUD'], 'PLN-CLOUD-Y', 'CloudSync Pro Annual', 'Annual', 99.00, 'USD', 30, '2TB Storage, Unlimited Devices, Priority Support, 2 Months Free', 'Active'),
        # SoundWave VIP
        (p_map['PRD-STREAM'], 'PLN-STR-M', 'SoundWave Individual', 'Monthly', 11.99, 'USD', 30, 'Unlimited Hi-Fi Streaming, 1 Profile, Offline Downloads', 'Active'),
        (p_map['PRD-STREAM'], 'PLN-STR-FAM', 'SoundWave Family Plan', 'Monthly', 19.99, 'USD', 30, 'Up to 6 Accounts, Explicit Content Filter, Shared Playlists', 'Active'),
        # BrightCRM Suite
        (p_map['PRD-SAAS'], 'PLN-CRM-GROWTH', 'BrightCRM Growth', 'Monthly', 49.00, 'USD', 14, 'Up to 5 Users, Lead Pipeline, Email Marketing Integration', 'Active'),
        (p_map['PRD-SAAS'], 'PLN-CRM-ENT', 'BrightCRM Enterprise', 'Annual', 499.00, 'USD', 0, 'Unlimited Users, Dedicated Account Manager, Custom Workflows', 'Active'),
        # CyberShield VPN
        (p_map['PRD-SEC'], 'PLN-SEC-M', 'CyberShield Monthly', 'Monthly', 12.99, 'USD', 7, '10 Concurrent Connections, WireGuard Protocol, Malware Blocker', 'Active'),
        (p_map['PRD-SEC'], 'PLN-SEC-Y', 'CyberShield 2-Year Deal', 'Annual', 59.99, 'USD', 0, 'Unlimited Devices, Dedicated IP, Anti-DDoS, 70% Discount', 'Active')
    ]
    for pl in plans_data:
        db.execute_query(
            "INSERT INTO plans (product_id, plan_code, name, billing_cycle, price, currency, trial_days, features, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            pl
        )

    # Fetch plan IDs
    pl_map = {row['plan_code']: row['id'] for row in db.fetch_all("SELECT id, plan_code FROM plans")}

    # 4. Seed Variants
    variants_data = [
                (pl_map['PLN-CRM-ENT'], 'VAR-ODOO-ENT', 'Odoo Enterprise Certified', 'Brand', 'Odoo Certified Bridge', 560.00, 'Active'),
        # CloudSync Starter variants
        (pl_map['PLN-CLOUD-M'], 'VAR-CLD-1TB', '1TB Extra Booster', 'Storage Capacity', '1TB', 5.00, 'Active'),
        (pl_map['PLN-CLOUD-M'], 'VAR-CLD-2TB', '2TB Power Pack', 'Storage Capacity', '2TB', 9.00, 'Active'),
        # CloudSync Pro Annual variants
        (pl_map['PLN-CLOUD-Y'], 'VAR-CLD-5TB', '5TB Team Vault', 'Storage Capacity', '5TB', 39.00, 'Active'),
        # SoundWave Individual
        (pl_map['PLN-STR-M'], 'VAR-STR-LOSSLESS', 'Studio Master 24-bit', 'Audio Quality', 'Hi-Res Lossless 192kHz', 3.99, 'Active'),
        # BrightCRM Growth
        (pl_map['PLN-CRM-GROWTH'], 'VAR-CRM-SEATS5', 'Additional 5 User Seats', 'User Seats', '+5 Seats', 20.00, 'Active'),
        (pl_map['PLN-CRM-GROWTH'], 'VAR-CRM-SEATS10', 'Additional 10 User Seats', 'User Seats', '+10 Seats', 35.00, 'Active')
    ]
    for v in variants_data:
        db.execute_query(
            "INSERT INTO variants (plan_id, variant_code, name, attribute_type, attribute_value, price_adjustment, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            v
        )

    # Fetch variant IDs
    v_map = {row['variant_code']: row['id'] for row in db.fetch_all("SELECT id, variant_code FROM variants")}
    c_list = db.fetch_all("SELECT id FROM customers ORDER BY id ASC")

    # 5. Seed Subscriptions
    subs_data = [
        (
            'SUB-2026-001', c_list[0]['id'], p_map['PRD-CLOUD'], pl_map['PLN-CLOUD-M'], v_map['VAR-CLD-1TB'],
            '2026-10-01', '2026-11-01', '2026-11-01', 'Monthly', 14.99, 'Active', 1
        ),
        (
            'SUB-2026-002', c_list[1]['id'], p_map['PRD-STREAM'], pl_map['PLN-STR-M'], v_map['VAR-STR-LOSSLESS'],
            '2026-10-15', '2026-11-15', '2026-11-15', 'Monthly', 15.98, 'Active', 1
        ),
        (
            'SUB-2026-003', c_list[2]['id'], p_map['PRD-SAAS'], pl_map['PLN-CRM-GROWTH'], v_map['VAR-CRM-SEATS5'],
            '2026-09-01', '2026-10-01', '2026-11-01', 'Monthly', 69.00, 'Active', 1
        ),
        (
            'SUB-2026-004', c_list[3]['id'], p_map['PRD-SEC'], pl_map['PLN-SEC-Y'], None,
            '2026-10-20', '2027-10-20', '2027-10-20', 'Annual', 59.99, 'Active', 1
        ),
        (
            'SUB-2026-005', c_list[4]['id'], p_map['PRD-CLOUD'], pl_map['PLN-CLOUD-Y'], None,
            '2026-08-10', '2027-08-10', '2027-08-10', 'Annual', 99.00, 'Paused', 0
        )
    ]
    for s in subs_data:
        db.execute_query(
            """
            INSERT INTO subscriptions
            (subscription_code, customer_id, product_id, plan_id, variant_id, start_date, end_date, next_billing_date, billing_cycle, total_price, status, auto_renew)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            s
        )
    # 6. Seed Member 3 Data (Taxes, Discounts, Invoices, Payments)
    existing_taxes = db.fetch_all("SELECT COUNT(*) as count FROM taxes")
    if not existing_taxes or existing_taxes[0]['count'] == 0:
        print("[Database] Seeding Member 3 Billing, Tax & Discount data...")
        # Taxes
        taxes_data = [
            ('TAX-US-STD', 'United States - Standard', 'State Sales Tax', 7.50, 1),
            ('TAX-EU-VAT', 'European Union', 'VAT Standard Rate', 20.00, 1),
            ('TAX-IN-GST', 'India - Pan India', 'GST (Goods & Services Tax)', 18.00, 1),
            ('TAX-ZERO', 'Zero Tax Jurisdiction', 'Exempt / Zero Rate', 0.00, 1)
        ]
        for t in taxes_data:
            db.execute_query(
                "INSERT INTO taxes (tax_code, region_name, tax_name, rate, is_active) VALUES (%s, %s, %s, %s, %s)",
                t
            )

        # Discounts
        discounts_data = [
            ('WELCOME20', 'New Subscriber Welcome Voucher (20% Off)', 'percentage', 20.00, 0.00, '2026-01-01', '2026-12-31', 500, 12, 1),
            ('FLAT10OFF', 'Flat $10 Off Any Monthly Order', 'fixed', 10.00, 20.00, '2026-01-01', '2026-12-31', 200, 45, 1),
            ('SUMMER50', 'Summer Promo Tier Campaign (50% Off)', 'percentage', 50.00, 50.00, '2026-06-01', '2026-08-31', 100, 88, 1),
            ('ENTERPRISE100', 'Enterprise Tier Contract Voucher ($100 Off)', 'fixed', 100.00, 300.00, '2026-01-01', '2026-12-31', 50, 5, 1)
        ]
        for d in discounts_data:
            db.execute_query(
                "INSERT INTO discounts (code, description, discount_type, value, min_order_amount, valid_from, valid_until, usage_limit, times_used, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                d
            )

        # Invoices
        tax_eu = db.fetch_one("SELECT id FROM taxes WHERE tax_code = %s", ('TAX-EU-VAT',))
        tax_us = db.fetch_one("SELECT id FROM taxes WHERE tax_code = %s", ('TAX-US-STD',))
        disc_w20 = db.fetch_one("SELECT id FROM discounts WHERE code = %s", ('WELCOME20',))
        subs = db.fetch_all("SELECT id, customer_id, total_price FROM subscriptions ORDER BY id ASC")
        
        if subs:
            invoices_data = [
                ('INV-2026-0001', subs[0]['id'], subs[0]['customer_id'], '2026-10-01', '2026-10-15', 14.99, None, 0.00, tax_us['id'] if tax_us else None, 1.12, 16.11, 'Paid', 'Automatic subscription billing'),
                ('INV-2026-0002', subs[1]['id'], subs[1]['customer_id'], '2026-10-15', '2026-10-30', 15.98, disc_w20['id'] if disc_w20 else None, 3.20, tax_eu['id'] if tax_eu else None, 2.56, 15.34, 'Paid', 'Promotional voucher applied'),
                ('INV-2026-0003', subs[2]['id'], subs[2]['customer_id'], '2026-09-01', '2026-09-15', 69.00, None, 0.00, tax_us['id'] if tax_us else None, 5.18, 74.18, 'Paid', 'Standard renewal invoice'),
                ('INV-2026-0004', subs[3]['id'], subs[3]['customer_id'], '2026-10-20', '2026-11-04', 59.99, None, 0.00, None, 0.00, 59.99, 'Pending', 'Awaiting customer wire transfer')
            ]
            for inv in invoices_data:
                db.execute_query(
                    """
                    INSERT INTO invoices
                    (invoice_number, subscription_id, customer_id, issue_date, due_date, subtotal, discount_id, discount_amount, tax_id, tax_amount, total_amount, status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    inv
                )

            inv_list = db.fetch_all("SELECT id, customer_id, total_amount FROM invoices WHERE status = 'Paid' ORDER BY id ASC")
            # Payments
            if inv_list:
                payments_data = [
                    ('TXN-CC-9018241', inv_list[0]['id'], inv_list[0]['customer_id'], 'Credit Card', inv_list[0]['total_amount'], 'Success', 'Stripe Gateway settlement'),
                    ('TXN-PP-3841029', inv_list[1]['id'], inv_list[1]['customer_id'], 'PayPal', inv_list[1]['total_amount'], 'Success', 'PayPal Express settlement'),
                    ('TXN-UPI-7749102', inv_list[2]['id'], inv_list[2]['customer_id'], 'UPI', inv_list[2]['total_amount'], 'Success', 'Instant UPI mobile transfer')
                ]
                for p in payments_data:
                    db.execute_query(
                        """
                        INSERT INTO payments (transaction_id, invoice_id, customer_id, payment_method, amount, status, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        p
                    )
    print("[Database] Sample data seeding complete.")




def get_connection(db_path=None):
    """Returns raw sqlite3 connection with Row factory for compatibility."""
    if db_path:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    return db.get_connection()


def seed_billing_data(force=False):
    """Seeds realistic invoices and payments for all customer subscriptions."""
    inv_count = db.fetch_all("SELECT COUNT(*) as count FROM invoices")
    if inv_count and inv_count[0]['count'] > 0 and not force:
        return

    import random
    from datetime import datetime, timedelta

    if force:
        for tbl in ['payments', 'invoice_lines', 'invoices', 'discounts', 'taxes']:
            try:
                db.execute_query(f"DELETE FROM {tbl}")
            except Exception:
                pass

    # 1. Taxes
    taxes_data = [
        ("Standard VAT / GST", 18.0, 1),
        ("State Sales Tax", 8.25, 1),
        ("Zero Tax", 0.0, 1)
    ]
    for t in taxes_data:
        db.execute_query("INSERT INTO taxes (name, rate_percentage, is_active) VALUES (%s, %s, %s)", t)

    # 2. Discounts
    discounts_data = [
        ("STARTUP20", "20% Startup Discount", "percentage", 20.0, 100.0, 1, "2026-01-01", "2026-12-31", 50, 12, 1),
        ("FLAT50", "$50 Off Welcome Offer", "fixed", 50.0, 200.0, 1, "2026-01-01", "2026-12-31", 100, 38, 1),
        ("ANNUAL15", "15% Annual Contract Rebate", "percentage", 15.0, 500.0, 2, "2026-01-01", "2026-12-31", -1, 45, 1)
    ]
    for d in discounts_data:
        db.execute_query(
            "INSERT INTO discounts (code, description, discount_type, value, min_purchase, min_quantity, start_date, end_date, usage_limit, times_used, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            d
        )

    # 3. Invoices and Payments for Subscriptions
    subs = db.fetch_all("SELECT s.*, p.name as product_name FROM subscriptions s LEFT JOIN products p ON s.product_id = p.id")
    if not subs:
        return

    today = datetime.now()
    inv_counter = 1001
    methods = ['Credit Card', 'Bank Transfer', 'Stripe', 'PayPal']

    for s in subs:
        cust_id = s['customer_id']
        sub_id = s['id']
        price = float(s.get('total_price') or 49.00)

        # Create 2 to 4 historical invoices per subscription
        cycles = 3 if s.get('status') == 'Active' else 1
        for c in range(cycles):
            inv_code = f"INV-2026-{inv_counter}"
            inv_counter += 1

            days_ago = max(3, (c + 1) * 28)
            inv_dt = today - timedelta(days=days_ago)
            due_dt = inv_dt + timedelta(days=30)
            is_past_due = due_dt < today

            subtotal = price
            tax = round(subtotal * 0.18, 2)
            discount = 0.0
            total = round(subtotal + tax - discount, 2)

            if is_past_due and random.random() < 0.6:
                status = 'Overdue'
                paid = 0.0
            else:
                status = 'Paid'
                paid = total

            inv_id = db.execute_query(
                """
                INSERT INTO invoices
                (invoice_number, subscription_id, customer_id, invoice_date, due_date, subtotal, tax_amount, discount_amount, total_amount, amount_paid, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Automated BrightLoop Engine')
                """,
                (inv_code, sub_id, cust_id, inv_dt.strftime("%Y-%m-%d"), due_dt.strftime("%Y-%m-%d"), subtotal, tax, discount, total, paid, status)
            )

            if inv_id:
                # Invoice line
                db.execute_query(
                    """
                    INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, tax_amount, line_total)
                    VALUES (%s, %s, %s, 1, %s, %s, %s)
                    """,
                    (inv_id, s.get('product_id'), f"{s.get('product_name') or 'Service'} Subscription Charge", subtotal, tax, total)
                )

                if status == 'Paid':
                    pay_dt = (inv_dt + timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d")
                    db.execute_query(
                        """
                        INSERT INTO payments (invoice_id, customer_id, payment_date, payment_method, amount, transaction_ref, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, 'Settled via auto-pay')
                        """,
                        (inv_id, cust_id, pay_dt, random.choice(methods), total, f"TXN-{random.randint(100000, 999999)}")
                    )

    print("[Database] Invoices and Payments seeded successfully.")


def seed_demo_data(force=False, db_path=None):
    """Initializes schema and seeds demo data (both team models and billing)."""
    init_db()
    seed_billing_data(force=force)


if __name__ == '__main__':
    print("[Database] Testing connection & initializing tables...")
    init_db()
    prods = db.fetch_all("SELECT * FROM products")
    print(f"[Database] Found {len(prods)} products:")
    for p in prods:
        print(f"  - {p['product_code']}: {p['name']} ({p['category']})")
    users = db.fetch_all("SELECT id, email, role FROM users")
    print(f"[Database] Found {len(users)} users:")
    for u in users:
        print(f"  - User #{u['id']}: {u['email']} [{u['role']}]")
