import os
import random
import datetime
import jwt
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import db, init_db

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.environ.get("JWT_SECRET", "brightloop_python_jwt_secret_2026")
JWT_EXPIRES_DAYS = 7

# Ensure database is initialized on startup
init_db()


def generate_token(user_id, email, role):
    payload = {
        "id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXPIRES_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication token required. Please sign in."}), 401

        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user = db.fetch_one("SELECT id, email, role, status, last_login, created_at FROM users WHERE id = %s", (decoded["id"],))
            if not user:
                return jsonify({"error": "User account no longer exists."}), 404
            if user.get("status") != "active":
                return jsonify({"error": "Account is inactive or suspended."}), 403
            request.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired. Please sign in again."}), 403
        except Exception:
            return jsonify({"error": "Invalid authentication token."}), 403

        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, "current_user") or request.current_user.get("role") != "admin":
            return jsonify({"error": "Access denied. Administrator privileges required."}), 403
        return f(*args, **kwargs)
    return decorated


def get_user_profile(user_id, role):
    if role == "customer":
        cust = db.fetch_one("SELECT * FROM customers WHERE user_id = %s", (user_id,))
        if not cust:
            # Fallback by email match
            u = db.fetch_one("SELECT email FROM users WHERE id = %s", (user_id,))
            if u:
                cust = db.fetch_one("SELECT * FROM customers WHERE email = %s", (u["email"],))
        if cust:
            cust["full_name"] = cust.get("name") or cust.get("full_name") or "Valued Customer"
        return cust
    elif role == "staff":
        return db.fetch_one("SELECT * FROM staff WHERE user_id = %s", (user_id,))
    elif role == "admin":
        return {
            "full_name": "System Administrator",
            "department": "Executive Management",
            "role": "admin"
        }
    return None


# -------------------------------------------------------------
# 1. Health Endpoint
# -------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "BrightLoop Python API Server",
        "database_engine": db.engine.upper(),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })


# -------------------------------------------------------------
# 2. Authentication Routes
# -------------------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    expected_role = data.get("expectedRole")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    if user.get("status") != "active":
        return jsonify({"error": "Your account has been deactivated."}), 403

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    if expected_role and expected_role == "admin" and user.get("role") != "admin":
        return jsonify({"error": "Account does not have Administrator privileges."}), 403

    # Update last login
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db.execute_query("UPDATE users SET last_login = %s WHERE id = %s", (now_str, user["id"]))

    token = generate_token(user["id"], user["email"], user["role"])
    profile = get_user_profile(user["id"], user["role"])

    return jsonify({
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "status": user["status"],
            "last_login": now_str,
            "profile": profile
        }
    })


@app.route("/api/auth/register", methods=["POST"])
def register_customer():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    city = data.get("city", "").strip()
    postal_code = data.get("postal_code", "").strip()

    if not email or not password or not full_name:
        return jsonify({"error": "Full name, email, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    existing = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 409

    pwd_hash = generate_password_hash(password)
    db.execute_query(
        "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, 'customer', 'active')",
        (email, pwd_hash)
    )
    new_user = db.fetch_one("SELECT id, email, role, created_at FROM users WHERE email = %s", (email,))

    db.execute_query(
        """
        INSERT INTO customers (user_id, name, email, phone, company, address, city, postal_code, membership_tier, loyalty_points)
        VALUES (%s, %s, %s, %s, 'Individual Customer', %s, %s, %s, 'Standard', 100)
        """,
        (new_user["id"], full_name, email, phone, address, city, postal_code)
    )
    customer_profile = get_user_profile(new_user["id"], "customer")
    token = generate_token(new_user["id"], new_user["email"], "customer")

    return jsonify({
        "message": "Customer registered successfully.",
        "token": token,
        "user": {
            "id": new_user["id"],
            "email": new_user["email"],
            "role": new_user["role"],
            "profile": customer_profile
        }
    }), 201


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Please provide your registered email."}), 400

    user = db.fetch_one("SELECT id, email FROM users WHERE email = %s", (email,))
    if not user:
        return jsonify({
            "message": "If an account exists with this email, a 6-digit code has been generated.",
            "resetCode": None
        })

    code = str(random.randint(100000, 999999))
    expires = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).isoformat()

    db.execute_query(
        "UPDATE users SET reset_token = %s, reset_expires_at = %s WHERE id = %s",
        (code, expires, user["id"])
    )

    return jsonify({
        "message": "A 6-digit verification code has been sent to your email.",
        "resetCode": code,
        "expiresInMinutes": 15
    })


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    reset_code = data.get("resetCode", "").strip()
    new_password = data.get("newPassword", "")

    if not email or not reset_code or not new_password:
        return jsonify({"error": "Email, verification code, and new password are required."}), 400

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long."}), 400

    user = db.fetch_one("SELECT id, reset_token, reset_expires_at FROM users WHERE email = %s", (email,))
    if not user or not user.get("reset_token"):
        return jsonify({"error": "Invalid or expired password reset request."}), 400

    if user["reset_token"] != reset_code:
        return jsonify({"error": "Incorrect verification code. Please check and try again."}), 400

    new_hash = generate_password_hash(new_password)
    db.execute_query(
        "UPDATE users SET password_hash = %s, reset_token = NULL, reset_expires_at = NULL WHERE id = %s",
        (new_hash, user["id"])
    )

    return jsonify({"message": "Password updated successfully! You can now log in."})


@app.route("/api/auth/me", methods=["GET"])
@token_required
def get_me():
    user = request.current_user
    profile = get_user_profile(user["id"], user["role"])
    return jsonify({
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "status": user["status"],
            "last_login": user.get("last_login"),
            "created_at": user.get("created_at"),
            "profile": profile
        }
    })


# -------------------------------------------------------------
# 3. Admin Routes (Staff Registration - Admin only)
# -------------------------------------------------------------
@app.route("/api/admin/register-staff", methods=["POST"])
@token_required
@admin_required
def register_staff():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    department = data.get("department", "").strip()
    position = data.get("position", "").strip()
    phone = data.get("phone", "").strip()
    emp_code = data.get("employee_code", "").strip()

    if not email or not password or not full_name or not department or not position:
        return jsonify({"error": "Name, email, password, department, and position are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    existing_user = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing_user:
        return jsonify({"error": "An account with this email already exists."}), 409

    if not emp_code:
        count_res = db.fetch_one("SELECT COUNT(*) as count FROM staff")
        curr_count = count_res["count"] if count_res else 0
        emp_code = f"BL-STF-{str(curr_count + 1).zfill(3)}"
    else:
        existing_code = db.fetch_one("SELECT id FROM staff WHERE employee_code = %s", (emp_code,))
        if existing_code:
            return jsonify({"error": f"Employee code {emp_code} is already in use."}), 409

    pwd_hash = generate_password_hash(password)
    db.execute_query(
        "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, 'staff', 'active')",
        (email, pwd_hash)
    )
    new_user = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,))

    db.execute_query(
        """
        INSERT INTO staff (user_id, full_name, employee_code, department, position, phone, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (new_user["id"], full_name, emp_code, department, position, phone, request.current_user["id"])
    )

    created = db.fetch_one(
        """
        SELECT s.*, u.email, u.status 
        FROM staff s JOIN users u ON s.user_id = u.id 
        WHERE s.user_id = %s
        """,
        (new_user["id"],)
    )

    return jsonify({
        "message": f"Staff member {full_name} registered successfully with code {emp_code}.",
        "staff": created
    }), 201


@app.route("/api/admin/dashboard", methods=["GET"])
@token_required
@admin_required
def admin_dashboard():
    total_users = db.fetch_one("SELECT COUNT(*) as c FROM users")["c"]
    total_customers = db.fetch_one("SELECT COUNT(*) as c FROM customers")["c"]
    total_staff = db.fetch_one("SELECT COUNT(*) as c FROM staff")["c"]
    active_users = db.fetch_one("SELECT COUNT(*) as c FROM users WHERE status = 'active'")["c"]

    recent_customers = db.fetch_all(
        """
        SELECT c.id, c.name as full_name, c.email, c.phone, c.city, c.membership_tier, c.loyalty_points, c.created_at
        FROM customers c
        ORDER BY c.created_at DESC
        LIMIT 5
        """
    )

    recent_staff = db.fetch_all(
        """
        SELECT s.id, s.full_name, s.employee_code, s.department, s.position, s.created_at, u.email,
               admin.email as created_by_email
        FROM staff s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN users admin ON s.created_by = admin.id
        ORDER BY s.created_at DESC
        LIMIT 5
        """
    )

    return jsonify({
        "metrics": {
            "totalUsers": total_users,
            "totalCustomers": total_customers,
            "totalStaff": total_staff,
            "activeUsers": active_users
        },
        "recentCustomers": recent_customers,
        "recentStaff": recent_staff
    })


@app.route("/api/admin/staff", methods=["GET"])
@token_required
@admin_required
def list_staff():
    staff_list = db.fetch_all(
        """
        SELECT s.*, u.email, u.status, u.last_login, admin.email as created_by_admin
        FROM staff s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN users admin ON s.created_by = admin.id
        ORDER BY s.created_at DESC
        """
    )
    return jsonify({"staff": staff_list})


@app.route("/api/admin/customers", methods=["GET"])
@token_required
@admin_required
def list_customers():
    customers = db.fetch_all(
        """
        SELECT c.*, c.name as full_name, u.status, u.last_login
        FROM customers c
        LEFT JOIN users u ON c.user_id = u.id
        ORDER BY c.created_at DESC
        """
    )
    return jsonify({"customers": customers})


@app.route("/api/admin/tables", methods=["GET"])
@token_required
@admin_required
def inspect_tables():
    users = db.fetch_all("SELECT id, email, role, status, reset_token, last_login, created_at FROM users ORDER BY id ASC")
    customers = db.fetch_all("SELECT id, user_id, name as full_name, email, phone, city, membership_tier, loyalty_points, created_at FROM customers ORDER BY id ASC")
    staff = db.fetch_all("SELECT id, user_id, full_name, employee_code, department, position, phone, created_by, created_at FROM staff ORDER BY id ASC")
    
    # Teammate subscription tables
    products = db.fetch_all("SELECT id, product_code, name, category, status FROM products ORDER BY id ASC")
    subscriptions = db.fetch_all("SELECT id, subscription_code, customer_id, product_id, total_price, status, start_date FROM subscriptions ORDER BY id ASC")

    return jsonify({
        "tables": {
            "Users": users,
            "Customers": customers,
            "Staff": staff,
            "Products": products,
            "Subscriptions": subscriptions
        }
    })


# -------------------------------------------------------------
# 4. Customer Dashboard & Activity
# -------------------------------------------------------------
@app.route("/api/customer/dashboard", methods=["GET"])
@token_required
def customer_dashboard():
    user_id = request.current_user["id"]
    customer = get_user_profile(user_id, "customer")

    if not customer:
        return jsonify({"error": "Customer record not found."}), 404

    # Fetch real subscriptions from teammates' subscriptions table!
    subs = db.fetch_all(
        """
        SELECT s.*, p.name as product_name, p.category, pl.name as plan_name, pl.price
        FROM subscriptions s
        JOIN products p ON s.product_id = p.id
        JOIN plans pl ON s.plan_id = pl.id
        WHERE s.customer_id = %s
        """,
        (customer.get("id"),)
    )

    activities = []
    if subs:
        for s in subs:
            activities.append({
                "id": f"SUB-{s['id']}",
                "title": f"Subscription: {s.get('product_name')}",
                "description": f"Plan: {s.get('plan_name')} · Cycle: {s.get('billing_cycle')}",
                "date": str(s.get("start_date")),
                "status": s.get("status", "Active"),
                "badge": "success"
            })
    else:
        activities = [
            {
                "id": "ACT-101",
                "title": "Account Setup Complete",
                "description": "Standard Customer Onboarding Profile initialized",
                "date": datetime.date.today().isoformat(),
                "status": "Completed",
                "badge": "success"
            },
            {
                "id": "ACT-102",
                "title": "Welcome Loyalty Bonus",
                "description": "+100 loyalty points awarded for joining BrightLoop",
                "date": datetime.date.today().isoformat(),
                "status": "+100 Pts",
                "badge": "info"
            }
        ]

    stats = {
        "loyaltyPoints": customer.get("loyalty_points") or 100,
        "membershipTier": customer.get("membership_tier") or "Standard",
        "activeOrders": len(subs) if subs else 1,
        "savedAddresses": 1 if customer.get("address") else 0
    }

    return jsonify({
        "customer": customer,
        "stats": stats,
        "activities": activities,
        "subscriptions": subs
    })


# -------------------------------------------------------------
# 5. Profile Routes
# -------------------------------------------------------------
@app.route("/api/profile", methods=["GET", "PUT"])
@token_required
def handle_profile():
    user = request.current_user
    if request.method == "GET":
        profile = get_user_profile(user["id"], user["role"])
        return jsonify({
            "user": user,
            "profile": profile
        })

    # PUT
    data = request.get_json() or {}
    role = user["role"]

    if role == "customer":
        full_name = data.get("full_name") or data.get("name", "")
        phone = data.get("phone", "")
        address = data.get("address", "")
        city = data.get("city", "")
        postal_code = data.get("postal_code", "")

        db.execute_query(
            """
            UPDATE customers
            SET name = %s, phone = %s, address = %s, city = %s, postal_code = %s
            WHERE user_id = %s OR email = %s
            """,
            (full_name, phone, address, city, postal_code, user["id"], user["email"])
        )
        updated = get_user_profile(user["id"], "customer")
        return jsonify({"message": "Profile updated successfully!", "profile": updated})

    elif role == "staff":
        full_name = data.get("full_name", "")
        phone = data.get("phone", "")
        department = data.get("department", "")
        position = data.get("position", "")

        db.execute_query(
            """
            UPDATE staff
            SET full_name = %s, phone = %s, department = %s, position = %s
            WHERE user_id = %s
            """,
            (full_name, phone, department, position, user["id"])
        )
        updated = get_user_profile(user["id"], "staff")
        return jsonify({"message": "Staff profile updated successfully!", "profile": updated})

    return jsonify({"message": "Profile updated.", "profile": {"full_name": "System Administrator"}})


@app.route("/api/profile/change-password", methods=["PUT"])
@token_required
def change_password():
    user = request.current_user
    data = request.get_json() or {}
    current_pwd = data.get("currentPassword", "")
    new_pwd = data.get("newPassword", "")

    if not current_pwd or not new_pwd:
        return jsonify({"error": "Current password and new password are required."}), 400

    if len(new_pwd) < 6:
        return jsonify({"error": "New password must be at least 6 characters long."}), 400

    full_user = db.fetch_one("SELECT password_hash FROM users WHERE id = %s", (user["id"],))
    if not check_password_hash(full_user["password_hash"], current_pwd):
        return jsonify({"error": "Current password is incorrect."}), 400

    new_hash = generate_password_hash(new_pwd)
    db.execute_query("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user["id"]))

    return jsonify({"message": "Password changed successfully!"})


if __name__ == "__main__":
    print("==================================================")
    print("🚀 BrightLoop Python Flask API Server running on port 5000")
    print("   Health Check: http://localhost:5000/api/health")
    print(f"   Database Engine: {db.engine.upper()}")
    print("==================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
