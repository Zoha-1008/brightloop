# BrightLoop - Role-Based Customer & Enterprise Management Portal

A full-stack, enterprise-grade portal system built with **Python (Flask + SQLite/MySQL)** backend and **React (Vite + Tailwind CSS)** frontend.

---

## 📋 Responsibilities & Specifications

- **Welcome Screen**: Clean landing page introducing BrightLoop with quick action entry points.
- **Admin Login**: Secure administrator authentication leading directly to the Admin Command Center.
- **Customer Login**: Customer authentication leading directly to the personalized Customer Dashboard.
- **Forgot Password**: 2-step verification code (OTP) request and password reset workflow.
- **User Authentication**: JWT token-based authentication with `werkzeug.security` password hashing and role validation middleware.
- **Customer Registration**: Public customer self-registration capturing personal and contact profile details.
- **Staff Registration (Admin only)**: Restricted staff onboarding accessible exclusively to authenticated Administrators.
- **Customer Dashboard**: Personalized overview with loyalty perks, active subscriptions, activity feeds, and profile access.
- **Admin Dashboard**: Administrator command center with metrics, Staff registration modal, staff directory, customer directory, and live database tables inspector.
- **Profile Screen**: Comprehensive profile management for all user roles with personal details editing and password change functionality.

---

## 🗄️ Database Architecture (`database.py`)

The database manager (`DatabaseManager` in `database.py`) automatically supports both **MySQL** and **SQLite** (fallback), making it 100% compatible with teammate schemas:

### Primary Tables
1. **`users`**: User authentication credentials, role (`admin`, `customer`, `staff`), status, reset token, and last login.
2. **`customers`**: Customer profiles, phone, company, address, city, postal code, membership tier, and loyalty points.
3. **`staff`**: Enterprise staff records created exclusively by Admins, employee code, department, position, phone, and creator FK.
4. **`products`**: Product catalog (e.g. *CloudSync Pro*, *SoundWave VIP*, *BrightCRM Suite*, *CyberShield VPN*).
5. **`plans`**: Billing plans associated with products.
6. **`variants`**: Plan add-ons and feature variants.
7. **`subscriptions`**: Active and historic customer subscriptions displayed on the Customer Dashboard.

---

## 🖥️ Screens Implemented

| Screen | Route | Key Frontend File |
| :--- | :--- | :--- |
| **Welcome** | `/` | `client/src/pages/Welcome.jsx` |
| **Login** | `/login` | `client/src/pages/Login.jsx` |
| **Register** | `/register` | `client/src/pages/Register.jsx` |
| **Forgot Password** | `/forgot-password` | `client/src/pages/ForgotPassword.jsx` |
| **Customer Dashboard** | `/customer-dashboard` | `client/src/pages/CustomerDashboard.jsx` |
| **Admin Dashboard** | `/admin-dashboard` | `client/src/pages/AdminDashboard.jsx` |
| **Profile** | `/profile` | `client/src/pages/Profile.jsx` |

---

## 🔑 Pre-Seeded Test Credentials

| Role | Email | Password | Redirect Destination |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@brightloop.com` | `AdminPassword123!` | `/admin-dashboard` |
| **Customer** | `customer@brightloop.com` | `CustomerPassword123!` | `/customer-dashboard` |
| **Staff** | `staff@brightloop.com` | `StaffPassword123!` | `/customer-dashboard` / Portal |

*(The login screen also features 1-click **Autofill** buttons for instant testing).*

---

## 🚀 Running the Project

### 1. Install Dependencies
```bash
# Install Python backend dependencies
python -m pip install -r requirements.txt

# Install React frontend dependencies
cd client && npm install && cd ..
```

### 2. Initialize / Seed the Database
```bash
python database.py
```

### 3. Run the Application
Start both Python backend and React frontend concurrently:
```bash
npm run dev
```
Or run them in separate terminals:
- **Python Backend**: `python app.py` (Runs on `http://localhost:5000`)
- **React Frontend**: `npm run client` (Runs on `http://localhost:3000`)

### 4. Run Automated Test Suite
```bash
python test_python_api.py
```
*(Executes all 12 test assertions verifying login, registration, role separation, forgot password, staff registration restriction, and table queries).*
