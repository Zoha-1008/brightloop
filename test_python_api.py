import json
from app import app, db

def run_tests():
    client = app.test_client()
    passed = 0
    failed = 0

    def assert_test(cond, title):
        nonlocal passed, failed
        if cond:
            print(f"  ✓ PASS: {title}")
            passed += 1
        else:
            print(f"  ✗ FAIL: {title}")
            failed += 1

    print("\n================ TESTING PYTHON FLASK BACKEND ================")

    # 1. Health check
    res = client.get("/api/health")
    data = res.get_json()
    assert_test(res.status_code == 200 and data.get("status") == "ok", "GET /api/health responding ok")

    # 2. Customer login
    res = client.post("/api/auth/login", json={
        "email": "customer@brightloop.com",
        "password": "CustomerPassword123!"
    })
    data = res.get_json()
    assert_test(res.status_code == 200 and data.get("user", {}).get("role") == "customer", "Customer Login returns role=customer")
    customer_token = data.get("token")

    # 3. Admin login
    res = client.post("/api/auth/login", json={
        "email": "admin@brightloop.com",
        "password": "AdminPassword123!"
    })
    data = res.get_json()
    assert_test(res.status_code == 200 and data.get("user", {}).get("role") == "admin", "Admin Login returns role=admin")
    admin_token = data.get("token")

    # 4. Customer self-registration
    new_email = f"py_customer_{random_suffix()}@brightloop.io"
    res = client.post("/api/auth/register", json={
        "full_name": "Python Customer",
        "email": new_email,
        "password": "CustomerPassword123!",
        "phone": "+1 555 777 8888",
        "address": "456 Python Ave",
        "city": "Seattle",
        "postal_code": "98101"
    })
    data = res.get_json()
    assert_test(res.status_code == 201 and data.get("user", {}).get("role") == "customer", "Customer Registration succeeds")
    new_cust_token = data.get("token")

    # 5. Staff registration restriction: Customer attempts staff registration -> Must be 403 Forbidden!
    res = client.post("/api/admin/register-staff", 
        json={
            "full_name": "Unauthorized Staff",
            "email": "unauth@brightloop.com",
            "password": "Password123!",
            "department": "Engineering",
            "position": "Analyst"
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert_test(res.status_code == 403, "Staff registration restricted from regular customers (403 Forbidden)")

    # 6. Staff registration by Admin (Admin only)
    staff_email = f"py_staff_{random_suffix()}@brightloop.com"
    res = client.post("/api/admin/register-staff", 
        json={
            "full_name": "Elena Rostova",
            "email": staff_email,
            "password": "StaffPassword123!",
            "department": "Operations & Systems",
            "position": "Infrastructure Engineer",
            "phone": "+1 555 333 4444"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = res.get_json()
    assert_test(res.status_code == 201 and data.get("staff", {}).get("email") == staff_email, "Admin registers staff successfully (Admin only)")

    # 7. Forgot Password
    res = client.post("/api/auth/forgot-password", json={"email": new_email})
    data = res.get_json()
    code = data.get("resetCode")
    assert_test(res.status_code == 200 and code is not None, "Forgot password generates 6-digit OTP code")

    # 8. Reset Password
    res = client.post("/api/auth/reset-password", json={
        "email": new_email,
        "resetCode": code,
        "newPassword": "UpdatedPassword123!"
    })
    assert_test(res.status_code == 200, "Reset password succeeds with valid OTP code")

    # 9. Login with new password
    res = client.post("/api/auth/login", json={
        "email": new_email,
        "password": "UpdatedPassword123!"
    })
    assert_test(res.status_code == 200, "Login succeeds with updated password")

    # 10. Customer Dashboard
    res = client.get("/api/customer/dashboard", headers={"Authorization": f"Bearer {new_cust_token}"})
    data = res.get_json()
    assert_test(res.status_code == 200 and "customer" in data and "stats" in data, "Customer Dashboard returns personal stats & activities")

    # 11. Profile Update
    res = client.put("/api/profile", 
        json={
            "full_name": "Python Customer Renamed",
            "phone": "+1 555 000 9999",
            "city": "Portland"
        },
        headers={"Authorization": f"Bearer {new_cust_token}"}
    )
    assert_test(res.status_code == 200, "Profile updates successfully")

    # 12. Admin Tables Inspector (Users, Customers, Staff + Teammate Tables)
    res = client.get("/api/admin/tables", headers={"Authorization": f"Bearer {admin_token}"})
    data = res.get_json()
    tables = data.get("tables", {})
    assert_test(
        res.status_code == 200 and
        len(tables.get("Users", [])) > 0 and
        len(tables.get("Customers", [])) > 0 and
        len(tables.get("Staff", [])) > 0 and
        len(tables.get("Products", [])) > 0,
        "Admin Tables Inspector queries Users, Customers, Staff, and Teammate Products"
    )

    print("\n================ TEST SUMMARY ================")
    print(f"  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("==============================================\n")

    return failed == 0

def random_suffix():
    import random
    return str(random.randint(1000, 9999))

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
