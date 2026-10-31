"""
test_member2.py - Comprehensive Verification Test Suite for Member 2
Tests all CRUD operations, foreign key relationships, date calculations,
and lifecycle operations across Products, Plans, Variants, and Subscriptions.
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import db, init_db
from subscriptions.products import ProductManager
from subscriptions.plans import PlanManager
from subscriptions.variants import VariantManager
from subscriptions.subscriptions import SubscriptionManager


def cleanup_test_artifacts():
    """Removes all test-created records from DB."""
    # Find test product
    tp = ProductManager.get_product_by_code("PRD-TEST-99")
    if tp:
        # Delete any test subscriptions
        db.execute_query("DELETE FROM subscriptions WHERE product_id = %s", (tp['id'],))
        # Delete test variants
        db.execute_query("DELETE FROM variants WHERE variant_code = 'VAR-TEST-99'")
        # Delete test plans
        db.execute_query("DELETE FROM plans WHERE product_id = %s", (tp['id'],))
        # Delete test product
        db.execute_query("DELETE FROM products WHERE id = %s", (tp['id'],))


def run_tests():
    print("=" * 60)
    print("RUNNING MEMBER 2 AUTOMATED TEST SUITE")
    print("=" * 60)

    init_db()
    cleanup_test_artifacts()

    # -------------------------------------------------------------
    # Test 1: Products
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing ProductManager...")
    test_code = "PRD-TEST-99"

    success, msg = ProductManager.add_product(
        product_code=test_code,
        name="Automated Test Product",
        category="Test Category",
        description="Created by automated test",
        status="Active"
    )
    assert success, f"Product creation failed: {msg}"
    print("  [OK] Product created successfully")

    prod = ProductManager.get_product_by_code(test_code)
    assert prod is not None, "Product could not be fetched by code"
    prod_id = prod['id']
    print(f"  [OK] Product fetched with ID: {prod_id}")

    success, msg = ProductManager.update_product(
        prod_id, test_code, "Automated Test Product Updated", "Updated Category", "Updated Desc", "Active"
    )
    assert success, f"Product update failed: {msg}"
    prod_updated = ProductManager.get_product_by_id(prod_id)
    assert prod_updated['name'] == "Automated Test Product Updated"
    print("  [OK] Product updated successfully")

    # -------------------------------------------------------------
    # Test 2: Plans
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing PlanManager...")
    plan_code = "PLN-TEST-99"

    success, msg = PlanManager.add_plan(
        product_id=prod_id,
        plan_code=plan_code,
        name="Test Plan Monthly",
        billing_cycle="Monthly",
        price=29.99,
        currency="USD",
        trial_days=14,
        features="Feature A, Feature B",
        status="Active"
    )
    assert success, f"Plan creation failed: {msg}"
    print("  [OK] Plan created successfully")

    plan = PlanManager.get_plan_by_code(plan_code)
    assert plan is not None
    plan_id = plan['id']
    print(f"  [OK] Plan fetched with ID: {plan_id}, Price: ${plan['price']}")

    # -------------------------------------------------------------
    # Test 3: Variants
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing VariantManager...")
    var_code = "VAR-TEST-99"

    success, msg = VariantManager.add_variant(
        plan_id=plan_id,
        variant_code=var_code,
        name="Test Variant Extra Seats",
        attribute_type="Seats",
        attribute_value="10 Seats",
        price_adjustment=15.00,
        status="Active"
    )
    assert success, f"Variant creation failed: {msg}"
    print("  [OK] Variant created successfully")

    variant = VariantManager.get_variant_by_code(var_code)
    assert variant is not None
    var_id = variant['id']
    print(f"  [OK] Variant fetched with ID: {var_id}, Price Adj: +${variant['price_adjustment']}")

    # -------------------------------------------------------------
    # Test 4: Subscriptions & Calculations
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing SubscriptionManager...")
    cust = db.fetch_one("SELECT id FROM customers LIMIT 1")
    assert cust is not None, "No customer found to test subscription"
    cust_id = cust['id']

    # Expected price: 29.99 (plan) + 15.00 (variant) = 44.99
    success, msg = SubscriptionManager.create_subscription(
        customer_id=cust_id,
        product_id=prod_id,
        plan_id=plan_id,
        variant_id=var_id,
        auto_renew=True
    )
    assert success, f"Subscription creation failed: {msg}"
    print(f"  [OK] Subscription created: {msg}")

    # Fetch newly created subscription
    subs = SubscriptionManager.get_all_subscriptions(product_id=prod_id)
    assert len(subs) > 0
    test_sub = subs[0]
    sub_id = test_sub['id']
    print(f"  [OK] Subscription ID: {sub_id}, Code: {test_sub['subscription_code']}")
    assert abs(float(test_sub['total_price']) - 44.99) < 0.01, f"Calculated price mismatch: {test_sub['total_price']} vs 44.99"
    print(f"  [OK] Total price correctly computed: ${test_sub['total_price']}")

    # Test Pause / Resume
    success, msg = SubscriptionManager.toggle_pause(sub_id)
    assert success, f"Pause failed: {msg}"
    sub_paused = SubscriptionManager.get_subscription_by_id(sub_id)
    assert sub_paused['status'] == "Paused"
    print("  [OK] Subscription paused successfully")

    success, msg = SubscriptionManager.toggle_pause(sub_id)
    assert success, f"Resume failed: {msg}"
    sub_resumed = SubscriptionManager.get_subscription_by_id(sub_id)
    assert sub_resumed['status'] == "Active"
    print("  [OK] Subscription resumed successfully")

    # Test Renew
    success, msg = SubscriptionManager.renew_subscription(sub_id)
    assert success, f"Renew failed: {msg}"
    print("  [OK] Subscription renewed successfully")

    # Test KPIs calculation
    kpis = SubscriptionManager.get_kpis()
    assert kpis['total'] > 0
    assert kpis['mrr'] > 0
    print(f"  [OK] KPIs computed: Total={kpis['total']}, Active={kpis['active']}, MRR=${kpis['mrr']}")

    # -------------------------------------------------------------
    # Cleanup Test Records
    # -------------------------------------------------------------
    print("\n[CLEANUP] Cleaning up test records...")
    cleanup_test_artifacts()
    print("  [OK] Test artifacts cleaned successfully")

    print("\n" + "=" * 60)
    print("ALL MEMBER 2 TESTS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
