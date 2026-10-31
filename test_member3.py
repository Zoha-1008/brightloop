"""
test_member3.py - Comprehensive Verification Test Suite for Member 3
Subscription Management System

Tests all CRUD operations, calculation engines, validity checks,
itemized statements, and payment reconciliation across Taxes, Discounts, Invoices, and Payments.
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import db, init_db
from billing.taxes import TaxManager
from billing.discounts import DiscountManager
from billing.invoices import InvoiceManager
from billing.payments import PaymentManager


def cleanup_test_artifacts():
    """Removes test artifacts from database to ensure pristine state."""
    # Find test customer or invoices
    tpays = db.fetch_all("SELECT id FROM payments WHERE notes LIKE '%TEST_SUITE%'")
    for p in tpays:
        db.execute_query("DELETE FROM payments WHERE id = %s", (p['id'],))

    tinvs = db.fetch_all("SELECT id FROM invoices WHERE notes LIKE '%TEST_SUITE%'")
    for inv in tinvs:
        db.execute_query("DELETE FROM invoices WHERE id = %s", (inv['id'],))

    db.execute_query("DELETE FROM discounts WHERE code IN ('TESTPERC20', 'TESTFIXED15', 'TESTEXP50', 'TESTMIN50')")
    db.execute_query("DELETE FROM taxes WHERE tax_code IN ('TAX-TEST-10', 'TAX-TEST-UPDATE')")


def run_tests():
    print("=" * 64)
    print("⚡ RUNNING MEMBER 3 (BILLING & PAYMENTS) AUTOMATED TEST SUITE")
    print("=" * 64)

    init_db()
    cleanup_test_artifacts()

    # Get a customer ID from database
    cust = db.fetch_one("SELECT id FROM customers LIMIT 1")
    assert cust is not None, "A valid customer record is required to run tests."
    cust_id = cust['id']

    # -------------------------------------------------------------
    # Test 1: Tax Jurisdictions & Rates
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing TaxManager DAO & Calculation Engine...")
    t_code = "TAX-TEST-10"

    success, msg = TaxManager.add_tax(
        tax_code=t_code,
        region_name="Test Jurisdiction Alpha",
        tax_name="Alpha Value Added Tax",
        rate=10.0,
        is_active=1
    )
    assert success, f"Failed to create tax rule: {msg}"
    print("  [OK] Tax rule created successfully")

    tax_row = TaxManager.get_tax_by_code(t_code)
    assert tax_row is not None, "Tax rule could not be fetched by code"
    assert float(tax_row['rate']) == 10.0
    tax_id = tax_row['id']
    print(f"  [OK] Tax rule fetched by code (ID: {tax_id}, Rate: {tax_row['rate']}%)")

    # Test Calculation: 10% on $250.00 => $25.00
    tax_amt, name, rate = TaxManager.calculate_tax(250.00, tax_id)
    assert tax_amt == 25.00, f"Expected tax amount $25.00, got {tax_amt}"
    assert rate == 10.0
    print(f"  [OK] Tax calculation verified: 10% on $250.00 = ${tax_amt:.2f}")

    # Test Update
    success, msg = TaxManager.update_tax(
        tax_id, "TAX-TEST-UPDATE", "Updated Jurisdiction", "Updated Tax", 12.5, 1
    )
    assert success, f"Tax update failed: {msg}"
    updated_tax = TaxManager.get_tax_by_id(tax_id)
    assert updated_tax['tax_code'] == "TAX-TEST-UPDATE"
    assert float(updated_tax['rate']) == 12.5
    print("  [OK] Tax rule update verified")

    # -------------------------------------------------------------
    # Test 2: Promotional Discounts & Coupon Engine
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing DiscountManager & Validation Sandbox...")
    
    # 2a. Percentage discount
    success, msg = DiscountManager.add_discount(
        code="TESTPERC20",
        description="20% Off Test Coupon",
        discount_type="percentage",
        value=20.0,
        min_order_amount=0.0,
        valid_until="2030-12-31",
        usage_limit=10,
        is_active=1
    )
    assert success, f"Coupon creation failed: {msg}"
    print("  [OK] Percentage coupon created ('TESTPERC20')")

    # 2b. Fixed discount with min order
    success, msg = DiscountManager.add_discount(
        code="TESTFIXED15",
        description="$15 Off on $50+ spend",
        discount_type="fixed",
        value=15.0,
        min_order_amount=50.0,
        valid_until="2030-12-31",
        usage_limit=10,
        is_active=1
    )
    assert success, f"Fixed coupon creation failed: {msg}"
    print("  [OK] Fixed coupon created ('TESTFIXED15')")

    # 2c. Expired discount
    success, msg = DiscountManager.add_discount(
        code="TESTEXP50",
        description="Expired 50% Voucher",
        discount_type="percentage",
        value=50.0,
        min_order_amount=0.0,
        valid_until="2020-01-01",
        usage_limit=10,
        is_active=1
    )
    assert success, f"Expired coupon creation failed: {msg}"
    print("  [OK] Expired coupon created for negative testing ('TESTEXP50')")

    # Test 20% on $100 -> $20.00
    valid, disc_amt, msg = DiscountManager.validate_and_apply_discount("TESTPERC20", 100.0)
    assert valid is True, f"Expected valid coupon: {msg}"
    assert disc_amt == 20.0, f"Expected discount $20.00, got {disc_amt}"
    print(f"  [OK] Percentage validation passed: 20% on $100.00 = -${disc_amt:.2f}")

    # Test fixed $15 on $80 -> $15.00
    valid, disc_amt, msg = DiscountManager.validate_and_apply_discount("TESTFIXED15", 80.0)
    assert valid is True, f"Expected valid coupon: {msg}"
    assert disc_amt == 15.0, f"Expected discount $15.00, got {disc_amt}"
    print(f"  [OK] Fixed validation passed: $15.00 off on $80.00 = -${disc_amt:.2f}")

    # Test min order violation ($30 < $50 threshold)
    valid, disc_amt, msg = DiscountManager.validate_and_apply_discount("TESTFIXED15", 30.0)
    assert valid is False, "Coupon should fail when below minimum spend"
    print(f"  [OK] Minimum spend rejection verified: '{msg}'")

    # Test expired coupon rejection
    valid, disc_amt, msg = DiscountManager.validate_and_apply_discount("TESTEXP50", 100.0)
    assert valid is False, "Expired coupon should be rejected"
    print(f"  [OK] Expiration rejection verified: '{msg}'")

    # -------------------------------------------------------------
    # Test 3: Invoicing Lifecycle & Itemized Statements
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing InvoiceManager & Printable Receipts...")
    
    disc_row = DiscountManager.get_discount_by_code("TESTPERC20")
    disc_id = disc_row['id']

    subtotal = 100.00
    discount_amount = 20.00
    taxable = subtotal - discount_amount
    tax_amount = round(taxable * 0.10, 2)  # 10% on $80 = $8.00
    total_amount = taxable + tax_amount     # $88.00

    success, inv_num = InvoiceManager.create_invoice(
        customer_id=cust_id,
        subscription_id=None,
        subtotal=subtotal,
        discount_id=disc_id,
        discount_amount=discount_amount,
        tax_id=tax_id,
        tax_amount=tax_amount,
        total_amount=total_amount,
        due_days=14,
        notes="TEST_SUITE invoice creation",
        status="Pending"
    )
    assert success, f"Invoice creation failed"
    print(f"  [OK] Invoice created successfully: {inv_num}")

    inv_record = InvoiceManager.get_invoice_by_number(inv_num)
    assert inv_record is not None, "Invoice record not found"
    assert inv_record['status'] == "Pending"
    assert float(inv_record['total_amount']) == 88.00
    inv_id = inv_record['id']
    print(f"  [OK] Invoice fetched and totals verified: ${inv_record['total_amount']:.2f}")

    # Status Transition
    success, msg = InvoiceManager.update_invoice_status(inv_id, "Paid")
    assert success
    inv_updated = InvoiceManager.get_invoice_by_id(inv_id)
    assert inv_updated['status'] == "Paid"
    print("  [OK] Invoice status transition verified (Pending -> Paid)")

    # Formatted ASCII receipt generation
    receipt_txt = InvoiceManager.build_receipt_text(inv_updated)
    assert "BRIGHTLOOP SUBSCRIPTION SERVICES" in receipt_txt
    assert inv_num in receipt_txt
    assert "$     88.00" in receipt_txt or "88.00" in receipt_txt
    print("  [OK] Formatted ASCII receipt generated and validated")

    # -------------------------------------------------------------
    # Test 4: Payment Gateways & Refund Processing
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing PaymentManager & Multi-Channel Gateways...")

    # Record payment for invoice
    success, txn_id, msg = PaymentManager.record_payment(
        invoice_id=inv_id,
        customer_id=cust_id,
        payment_method="Credit Card",
        amount=88.00,
        notes="TEST_SUITE payment capture"
    )
    assert success, f"Payment capture failed: {msg}"
    assert txn_id.startswith("TXN-CC-")
    print(f"  [OK] Payment recorded with gateway reference: {txn_id}")

    pay_record = db.fetch_one("SELECT * FROM payments WHERE transaction_id = %s", (txn_id,))
    assert pay_record is not None
    assert pay_record['status'] == "Success"
    pay_id = pay_record['id']

    # Process Customer Refund
    success, msg = PaymentManager.process_refund(pay_id, "Automated test suite refund")
    assert success, f"Refund failed: {msg}"
    pay_refunded = PaymentManager.get_payment_by_id(pay_id)
    assert pay_refunded['status'] == "Refunded"
    print(f"  [OK] Refund processed successfully: Status is '{pay_refunded['status']}'")

    # Financial Summary
    summary = PaymentManager.get_financial_summary()
    assert summary['total_txns'] > 0
    print(f"  [OK] Financial summary calculated: Net Volume = ${summary['net_volume']:.2f} across {summary['total_txns']} transactions")

    # Cleanup
    cleanup_test_artifacts()
    print("\n" + "=" * 64)
    print("🎉 ALL MEMBER 3 TEST SUITE ASSERTIONS PASSED (100% SUCCESS)!")
    print("=" * 64)


if __name__ == '__main__':
    run_tests()
