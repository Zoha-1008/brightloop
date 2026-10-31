"""
subscriptions/subscriptions.py - Customer Subscription Lifecycle Management Module (Member 2 Deliverable)
Subscription Management System

Provides complete backend subscription lifecycle management (create, upgrade, pause, resume,
renew, cancel) and a feature-rich Tkinter GUI with KPI metric cards.
"""

import sys
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class SubscriptionManager:
    """Backend Data Access & Business Logic for Subscriptions."""

    VALID_STATUSES = ["Active", "Trial", "Paused", "Cancelled", "Expired"]

    @staticmethod
    def _compute_cycle_delta(cycle_name):
        """Returns timedelta for a given billing cycle name."""
        cycle_name = (cycle_name or "Monthly").lower()
        if "month" in cycle_name:
            return timedelta(days=30)
        elif "quarter" in cycle_name:
            return timedelta(days=90)
        elif "semi" in cycle_name or "half" in cycle_name:
            return timedelta(days=180)
        elif "year" in cycle_name or "annual" in cycle_name:
            return timedelta(days=365)
        elif "life" in cycle_name:
            return timedelta(days=36500)
        return timedelta(days=30)

    @staticmethod
    def generate_code():
        """Generates a random unique subscription code like SUB-2026-8492."""
        year = datetime.now().year
        rand_num = random.randint(1000, 9999)
        code = f"SUB-{year}-{rand_num}"
        while db.fetch_one("SELECT id FROM subscriptions WHERE subscription_code = %s", (code,)):
            rand_num = random.randint(1000, 9999)
            code = f"SUB-{year}-{rand_num}"
        return code

    @staticmethod
    def get_all_subscriptions(status=None, product_id=None, search_term=None, customer_id=None):
        """Fetch all subscriptions with full joins for customer, product, plan, variant."""
        query = """
            SELECT
                s.id, s.subscription_code, s.start_date, s.end_date, s.next_billing_date,
                s.billing_cycle, s.total_price, s.status, s.auto_renew, s.created_at,
                c.id AS customer_id, c.name AS customer_name, c.email AS customer_email, c.company,
                p.id AS product_id, p.name AS product_name, p.product_code,
                pl.id AS plan_id, pl.name AS plan_name, pl.plan_code, pl.price AS base_price, pl.currency,
                v.id AS variant_id, v.name AS variant_name, v.variant_code, v.price_adjustment
            FROM subscriptions s
            JOIN customers c ON s.customer_id = c.id
            JOIN products p ON s.product_id = p.id
            JOIN plans pl ON s.plan_id = pl.id
            LEFT JOIN variants v ON s.variant_id = v.id
            WHERE 1=1
        """
        params = []

        if status and status != "All Statuses":
            query += " AND s.status = %s"
            params.append(status)

        if product_id and product_id != "All Products":
            query += " AND s.product_id = %s"
            params.append(product_id)

        if customer_id:
            query += " AND s.customer_id = %s"
            params.append(customer_id)

        if search_term:
            query += """ AND (
                s.subscription_code LIKE %s OR c.name LIKE %s OR
                c.email LIKE %s OR p.name LIKE %s OR pl.name LIKE %s
            )"""
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw, kw, kw])

        query += " ORDER BY s.id DESC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_subscription_by_id(subscription_id):
        """Fetch subscription details by ID."""
        query = """
            SELECT
                s.*,
                c.name AS customer_name, c.email AS customer_email, c.company,
                p.name AS product_name, p.product_code,
                pl.name AS plan_name, pl.plan_code, pl.price AS base_price, pl.currency,
                v.name AS variant_name, v.variant_code, v.price_adjustment
            FROM subscriptions s
            JOIN customers c ON s.customer_id = c.id
            JOIN products p ON s.product_id = p.id
            JOIN plans pl ON s.plan_id = pl.id
            LEFT JOIN variants v ON s.variant_id = v.id
            WHERE s.id = %s
        """
        return db.fetch_one(query, (subscription_id,))

    @staticmethod
    def create_subscription(customer_id, product_id, plan_id, variant_id=None, start_date=None, auto_renew=True):
        """Creates a subscription, computing billing cycle dates and pricing."""
        plan = db.fetch_one("SELECT * FROM plans WHERE id = %s", (plan_id,))
        if not plan:
            return False, "Selected plan not found."

        base_price = float(plan['price'])
        price_adj = 0.0

        if variant_id:
            variant = db.fetch_one("SELECT * FROM variants WHERE id = %s", (variant_id,))
            if variant:
                price_adj = float(variant['price_adjustment'])

        total_price = max(0.0, round(base_price + price_adj, 2))

        # Date calculations
        if not start_date:
            start_dt = date.today()
        elif isinstance(start_date, str):
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return False, "Invalid start date format. Use YYYY-MM-DD."
        else:
            start_dt = start_date

        cycle_delta = SubscriptionManager._compute_cycle_delta(plan['billing_cycle'])
        end_dt = start_dt + cycle_delta
        next_billing_dt = end_dt

        # Trial detection
        status = "Trial" if plan['trial_days'] and plan['trial_days'] > 0 else "Active"
        code = SubscriptionManager.generate_code()
        auto_renew_flag = 1 if auto_renew else 0

        try:
            db.execute_query(
                """
                INSERT INTO subscriptions
                (subscription_code, customer_id, product_id, plan_id, variant_id,
                 start_date, end_date, next_billing_date, billing_cycle, total_price, status, auto_renew)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (code, customer_id, product_id, plan_id, variant_id if variant_id else None,
                 str(start_dt), str(end_dt), str(next_billing_dt), plan['billing_cycle'], total_price, status, auto_renew_flag)
            )
            return True, f"Subscription {code} created successfully."
        except Exception as e:
            return False, f"Failed to create subscription: {str(e)}"

    @staticmethod
    def update_status(subscription_id, new_status):
        """Update subscription status (Active, Paused, Cancelled, Expired)."""
        if new_status not in SubscriptionManager.VALID_STATUSES:
            return False, f"Invalid status: {new_status}"

        try:
            db.execute_query(
                "UPDATE subscriptions SET status = %s WHERE id = %s",
                (new_status, subscription_id)
            )
            return True, f"Subscription status updated to {new_status}."
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def toggle_pause(subscription_id):
        """Pause an active subscription or resume a paused one."""
        sub = SubscriptionManager.get_subscription_by_id(subscription_id)
        if not sub:
            return False, "Subscription not found."

        if sub['status'] in ("Active", "Trial"):
            return SubscriptionManager.update_status(subscription_id, "Paused")
        elif sub['status'] == "Paused":
            return SubscriptionManager.update_status(subscription_id, "Active")
        else:
            return False, f"Cannot pause/resume a subscription with status '{sub['status']}'."

    @staticmethod
    def renew_subscription(subscription_id):
        """Renew subscription for another cycle and advance dates."""
        sub = SubscriptionManager.get_subscription_by_id(subscription_id)
        if not sub:
            return False, "Subscription not found."

        cycle_delta = SubscriptionManager._compute_cycle_delta(sub['billing_cycle'])

        try:
            curr_end = datetime.strptime(str(sub['end_date'])[:10], "%Y-%m-%d").date()
        except Exception:
            curr_end = date.today()

        new_end = max(curr_end, date.today()) + cycle_delta
        new_next_billing = new_end

        try:
            db.execute_query(
                """
                UPDATE subscriptions
                SET end_date = %s, next_billing_date = %s, status = 'Active'
                WHERE id = %s
                """,
                (str(new_end), str(new_next_billing), subscription_id)
            )
            return True, f"Subscription renewed until {new_end}."
        except Exception as e:
            return False, f"Failed to renew: {str(e)}"

    @staticmethod
    def change_plan(subscription_id, new_plan_id, new_variant_id=None):
        """Upgrade or switch plan for an existing subscription."""
        plan = db.fetch_one("SELECT * FROM plans WHERE id = %s", (new_plan_id,))
        if not plan:
            return False, "Target plan not found."

        base_price = float(plan['price'])
        price_adj = 0.0

        if new_variant_id:
            v = db.fetch_one("SELECT * FROM variants WHERE id = %s", (new_variant_id,))
            if v:
                price_adj = float(v['price_adjustment'])

        total_price = max(0.0, round(base_price + price_adj, 2))
        cycle_delta = SubscriptionManager._compute_cycle_delta(plan['billing_cycle'])
        new_next_billing = date.today() + cycle_delta

        try:
            db.execute_query(
                """
                UPDATE subscriptions
                SET product_id = %s, plan_id = %s, variant_id = %s,
                    billing_cycle = %s, total_price = %s, next_billing_date = %s
                WHERE id = %s
                """,
                (plan['product_id'], new_plan_id, new_variant_id if new_variant_id else None,
                 plan['billing_cycle'], total_price, str(new_next_billing), subscription_id)
            )
            return True, f"Subscription upgraded to '{plan['name']}' at ${total_price:.2f}/{plan['billing_cycle']}."
        except Exception as e:
            return False, f"Upgrade failed: {str(e)}"

    @staticmethod
    def delete_subscription(subscription_id):
        """Remove a subscription record."""
        try:
            db.execute_query("DELETE FROM subscriptions WHERE id = %s", (subscription_id,))
            return True, "Subscription record deleted."
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    @staticmethod
    def get_kpis():
        """Compute key metrics for top summary cards."""
        all_subs = db.fetch_all("SELECT status, billing_cycle, total_price FROM subscriptions")
        total = len(all_subs)
        active = sum(1 for s in all_subs if s['status'] == "Active")
        trial = sum(1 for s in all_subs if s['status'] == "Trial")
        paused = sum(1 for s in all_subs if s['status'] == "Paused")
        cancelled = sum(1 for s in all_subs if s['status'] == "Cancelled")

        # Estimated MRR (Monthly Recurring Revenue)
        mrr = 0.0
        for s in all_subs:
            if s['status'] in ("Active", "Trial"):
                price = float(s['total_price'])
                cycle = (s['billing_cycle'] or "Monthly").lower()
                if "annual" in cycle or "year" in cycle:
                    mrr += price / 12.0
                elif "quarter" in cycle:
                    mrr += price / 3.0
                elif "semi" in cycle:
                    mrr += price / 6.0
                else:
                    mrr += price

        return {
            'total': total,
            'active': active,
            'trial': trial,
            'paused': paused,
            'cancelled': cancelled,
            'mrr': round(mrr, 2)
        }


class SubscriptionWizard(tk.Toplevel):
    """Interactive modal wizard to create new customer subscriptions."""

    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.on_success = on_success
        self.title("New Customer Subscription Wizard")
        self.geometry("620x640")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._load_datasets()
        self._build_ui()
        self._on_product_change()

    def _load_datasets(self):
        self.customers = db.fetch_all("SELECT id, name, email, company FROM customers ORDER BY name ASC")
        self.cust_options = [f"{c['id']}: {c['name']} ({c['email']})" for c in self.customers]
        self.cust_map = {f"{c['id']}: {c['name']} ({c['email']})": c['id'] for c in self.customers}

        self.products = db.fetch_all("SELECT id, name, product_code FROM products WHERE status = 'Active' ORDER BY name ASC")
        self.prod_options = [f"{p['id']}: {p['name']} ({p['product_code']})" for p in self.products]
        self.prod_map = {f"{p['id']}: {p['name']} ({p['product_code']})": p['id'] for p in self.products}

    def _build_ui(self):
        self.configure(bg="#F8F9FA")
        container = ttk.Frame(self, padding="24")
        container.pack(fill=tk.BOTH, expand=True)

        header_lbl = ttk.Label(
            container,
            text="🌟 Create Customer Subscription",
            font=("Segoe UI", 14, "bold")
        )
        header_lbl.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 14))

        # 1. Select Customer
        ttk.Label(container, text="1. Select Customer *:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.cust_var = tk.StringVar()
        self.cust_combo = ttk.Combobox(container, textvariable=self.cust_var, values=self.cust_options, state="readonly", width=42)
        self.cust_combo.grid(row=1, column=1, sticky=tk.W, pady=6)
        if self.cust_options:
            self.cust_combo.current(0)

        # 2. Select Product
        ttk.Label(container, text="2. Select Product *:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.prod_var = tk.StringVar()
        self.prod_combo = ttk.Combobox(container, textvariable=self.prod_var, values=self.prod_options, state="readonly", width=42)
        self.prod_combo.grid(row=2, column=1, sticky=tk.W, pady=6)
        self.prod_combo.bind("<<ComboboxSelected>>", lambda e: self._on_product_change())
        if self.prod_options:
            self.prod_combo.current(0)

        # 3. Select Plan
        ttk.Label(container, text="3. Select Plan *:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=6)
        self.plan_var = tk.StringVar()
        self.plan_combo = ttk.Combobox(container, textvariable=self.plan_var, state="readonly", width=42)
        self.plan_combo.grid(row=3, column=1, sticky=tk.W, pady=6)
        self.plan_combo.bind("<<ComboboxSelected>>", lambda e: self._on_plan_change())

        # 4. Select Variant (Optional Add-on)
        ttk.Label(container, text="4. Variant / Add-on:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky=tk.W, pady=6)
        self.var_var = tk.StringVar()
        self.var_combo = ttk.Combobox(container, textvariable=self.var_var, state="readonly", width=42)
        self.var_combo.grid(row=4, column=1, sticky=tk.W, pady=6)
        self.var_combo.bind("<<ComboboxSelected>>", lambda e: self._update_pricing_summary())

        # 5. Start Date
        ttk.Label(container, text="5. Start Date:", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky=tk.W, pady=6)
        self.start_date_var = tk.StringVar(value=str(date.today()))
        self.start_date_entry = ttk.Entry(container, textvariable=self.start_date_var, width=20)
        self.start_date_entry.grid(row=5, column=1, sticky=tk.W, pady=6)

        # 6. Auto-Renew Checkbox
        self.auto_renew_var = tk.BooleanVar(value=True)
        self.auto_renew_chk = ttk.Checkbutton(container, text="Enable Automatic Recurring Billing (Auto-Renew)", variable=self.auto_renew_var)
        self.auto_renew_chk.grid(row=6, column=1, sticky=tk.W, pady=6)

        # 7. Pricing & Billing Summary Card
        self.summary_box = ttk.LabelFrame(container, text=" Order Summary & Pricing Details ", padding="14")
        self.summary_box.grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=(12, 10))

        self.summary_lbl = ttk.Label(self.summary_box, text="Calculating...", font=("Segoe UI", 9))
        self.summary_lbl.pack(anchor=tk.W)

        # Action Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=8, column=0, columnspan=2, sticky=tk.E, pady=(14, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=6)

        confirm_btn = ttk.Button(btn_frame, text="Confirm & Activate", command=self._submit)
        confirm_btn.pack(side=tk.RIGHT, padx=6)

    def _on_product_change(self):
        sel_prod = self.prod_var.get()
        if not sel_prod or sel_prod not in self.prod_map:
            return
        prod_id = self.prod_map[sel_prod]
        plans = db.fetch_all("SELECT id, name, plan_code, price, currency, billing_cycle, trial_days FROM plans WHERE product_id = %s AND status = 'Active'", (prod_id,))

        self.plan_options = [f"{p['id']}: {p['name']} (${p['price']:.2f}/{p['billing_cycle']})" for p in plans]
        self.plan_map = {f"{p['id']}: {p['name']} (${p['price']:.2f}/{p['billing_cycle']})": p for p in plans}
        self.plan_combo['values'] = self.plan_options

        if self.plan_options:
            self.plan_combo.current(0)
            self._on_plan_change()
        else:
            self.plan_var.set("")
            self.var_combo['values'] = []
            self.var_var.set("")
            self.summary_lbl.config(text="⚠️ No active plans found for this product.")

    def _on_plan_change(self):
        sel_plan = self.plan_var.get()
        if not sel_plan or sel_plan not in self.plan_map:
            return
        plan = self.plan_map[sel_plan]
        variants = db.fetch_all("SELECT id, name, variant_code, price_adjustment FROM variants WHERE plan_id = %s AND status = 'Active'", (plan['id'],))

        self.var_options = ["(None - Standard Base Tier)"] + [f"{v['id']}: {v['name']} (+${v['price_adjustment']:.2f})" for v in variants]
        self.var_map = {f"{v['id']}: {v['name']} (+${v['price_adjustment']:.2f})": v for v in variants}
        self.var_combo['values'] = self.var_options
        self.var_combo.current(0)

        self._update_pricing_summary()

    def _update_pricing_summary(self):
        sel_plan = self.plan_var.get()
        if not sel_plan or sel_plan not in self.plan_map:
            return
        plan = self.plan_map[sel_plan]
        base_price = float(plan['price'])

        sel_var = self.var_var.get()
        price_adj = 0.0
        var_name = "None"
        if sel_var and sel_var in self.var_map:
            v = self.var_map[sel_var]
            price_adj = float(v['price_adjustment'])
            var_name = v['name']

        total = base_price + price_adj
        trial_info = f"🎁 {plan['trial_days']} Days Free Trial Included!" if plan['trial_days'] > 0 else "Immediate billing (No trial)"

        summary_text = (
            f"• Base Plan: {plan['name']} (${base_price:.2f} / {plan['billing_cycle']})\n"
            f"• Variant / Add-on: {var_name} (+${price_adj:.2f})\n"
            f"• Total Effective Charge: ${total:.2f} per {plan['billing_cycle']}\n"
            f"• Billing Interval: {plan['billing_cycle']}\n"
            f"• Status on activation: {trial_info}"
        )
        self.summary_lbl.config(text=summary_text)

    def _submit(self):
        sel_cust = self.cust_var.get()
        sel_prod = self.prod_var.get()
        sel_plan = self.plan_var.get()

        if not sel_cust or not sel_prod or not sel_plan:
            messagebox.showerror("Error", "Customer, Product, and Plan are required.", parent=self)
            return

        cust_id = self.cust_map[sel_cust]
        prod_id = self.prod_map[sel_prod]
        plan_id = self.plan_map[sel_plan]['id']

        sel_var = self.var_var.get()
        variant_id = self.var_map[sel_var]['id'] if sel_var in self.var_map else None

        start_date = self.start_date_var.get().strip()
        auto_renew = self.auto_renew_var.get()

        success, msg = SubscriptionManager.create_subscription(
            cust_id, prod_id, plan_id, variant_id, start_date, auto_renew
        )

        if success:
            messagebox.showinfo("Success", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)


class ChangePlanDialog(tk.Toplevel):
    """Modal dialog to upgrade or downgrade subscription plan."""

    def __init__(self, parent, subscription_id, on_success=None):
        super().__init__(parent)
        self.subscription_id = subscription_id
        self.on_success = on_success

        self.title("Upgrade / Switch Subscription Plan")
        self.geometry("520x460")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.sub = SubscriptionManager.get_subscription_by_id(subscription_id)
        self._build_ui()

    def _build_ui(self):
        self.configure(bg="#F8F9FA")
        container = ttk.Frame(self, padding="24")
        container.pack(fill=tk.BOTH, expand=True)

        header_lbl = ttk.Label(
            container,
            text=f"🔄 Upgrade / Switch Plan: {self.sub['subscription_code']}",
            font=("Segoe UI", 13, "bold")
        )
        header_lbl.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 12))

        # Current details
        curr_text = f"Customer: {self.sub['customer_name']} | Current: {self.sub['plan_name']} (${self.sub['total_price']:.2f})"
        ttk.Label(container, text=curr_text, font=("Segoe UI", 9, "italic"), foreground="#495057").grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 14))

        # Available plans for this product
        plans = db.fetch_all("SELECT id, name, price, billing_cycle FROM plans WHERE product_id = %s AND status = 'Active'", (self.sub['product_id'],))
        self.plan_options = [f"{p['id']}: {p['name']} (${p['price']:.2f} / {p['billing_cycle']})" for p in plans]
        self.plan_map = {f"{p['id']}: {p['name']} (${p['price']:.2f} / {p['billing_cycle']})": p['id'] for p in plans}

        ttk.Label(container, text="New Plan *:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=8)
        self.plan_var = tk.StringVar()
        self.plan_combo = ttk.Combobox(container, textvariable=self.plan_var, values=self.plan_options, state="readonly", width=36)
        self.plan_combo.grid(row=2, column=1, sticky=tk.W, pady=8)
        self.plan_combo.bind("<<ComboboxSelected>>", lambda e: self._on_plan_select())
        if self.plan_options:
            self.plan_combo.current(0)

        # Variants for new plan
        ttk.Label(container, text="Variant / Tier:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=8)
        self.var_var = tk.StringVar()
        self.var_combo = ttk.Combobox(container, textvariable=self.var_var, state="readonly", width=36)
        self.var_combo.grid(row=3, column=1, sticky=tk.W, pady=8)

        self._on_plan_select()

        # Action Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky=tk.E, pady=(24, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=6)

        save_btn = ttk.Button(btn_frame, text="Apply Plan Change", command=self._save)
        save_btn.pack(side=tk.RIGHT, padx=6)

    def _on_plan_select(self):
        sel_plan = self.plan_var.get()
        if not sel_plan or sel_plan not in self.plan_map:
            return
        plan_id = self.plan_map[sel_plan]
        variants = db.fetch_all("SELECT id, name, price_adjustment FROM variants WHERE plan_id = %s AND status = 'Active'", (plan_id,))

        self.var_options = ["(None)"] + [f"{v['id']}: {v['name']} (+${v['price_adjustment']:.2f})" for v in variants]
        self.var_map = {f"{v['id']}: {v['name']} (+${v['price_adjustment']:.2f})": v['id'] for v in variants}
        self.var_combo['values'] = self.var_options
        self.var_combo.current(0)

    def _save(self):
        sel_plan = self.plan_var.get()
        if not sel_plan or sel_plan not in self.plan_map:
            messagebox.showerror("Error", "Please select a plan.", parent=self)
            return

        new_plan_id = self.plan_map[sel_plan]
        sel_var = self.var_var.get()
        new_variant_id = self.var_map.get(sel_var, None)

        success, msg = SubscriptionManager.change_plan(self.subscription_id, new_plan_id, new_variant_id)
        if success:
            messagebox.showinfo("Success", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)


class SubscriptionView(ttk.Frame):
    """Main Subscription Management View Component for Member 2."""

    def __init__(self, parent):
        super().__init__(parent)
        self.product_filter_map = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        # 1. Header Frame
        header_frame = ttk.Frame(self, padding="14")
        header_frame.pack(fill=tk.X)

        title_lbl = ttk.Label(
            header_frame,
            text="📑 Customer Subscriptions Dashboard",
            font=("Segoe UI", 16, "bold")
        )
        title_lbl.pack(side=tk.LEFT)

        # 2. KPI Cards Frame
        kpi_frame = ttk.Frame(self, padding=(14, 0, 14, 8))
        kpi_frame.pack(fill=tk.X)

        self.card_total = self._create_kpi_card(kpi_frame, "Total Subscriptions", "0", "#0D6EFD")
        self.card_active = self._create_kpi_card(kpi_frame, "Active Subscribers", "0", "#198754")
        self.card_trial = self._create_kpi_card(kpi_frame, "In Trial", "0", "#0DCAF0")
        self.card_paused = self._create_kpi_card(kpi_frame, "Paused", "0", "#FFC107")
        self.card_mrr = self._create_kpi_card(kpi_frame, "Estimated MRR", "$0.00", "#6F42C1")

        # 3. Filter Toolbar
        filter_frame = ttk.LabelFrame(self, text=" Search & Filter Subscriptions ", padding="10")
        filter_frame.pack(fill=tk.X, padx=14, pady=6)

        # Status filter
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 4))
        self.status_filter_var = tk.StringVar(value="All Statuses")
        statuses = ["All Statuses"] + SubscriptionManager.VALID_STATUSES
        self.status_filter = ttk.Combobox(filter_frame, textvariable=self.status_filter_var, values=statuses, state="readonly", width=12)
        self.status_filter.pack(side=tk.LEFT, padx=4)
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Product filter
        ttk.Label(filter_frame, text="Product:").pack(side=tk.LEFT, padx=(10, 4))
        self.product_filter_var = tk.StringVar(value="All Products")
        self.product_filter = ttk.Combobox(filter_frame, textvariable=self.product_filter_var, state="readonly", width=20)
        self.product_filter.pack(side=tk.LEFT, padx=4)
        self.product_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Search keyword
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(10, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=16)
        self.search_entry.pack(side=tk.LEFT, padx=4)
        self.search_entry.bind("<Return>", lambda e: self.refresh())

        search_btn = ttk.Button(filter_frame, text="🔍 Search", command=self.refresh)
        search_btn.pack(side=tk.LEFT, padx=6)

        reset_btn = ttk.Button(filter_frame, text="Reset", command=self._reset_filters)
        reset_btn.pack(side=tk.LEFT, padx=4)

        new_sub_btn = ttk.Button(filter_frame, text="➕ New Subscription", command=self._open_new_wizard)
        new_sub_btn.pack(side=tk.RIGHT, padx=4)

        # 4. Subscriptions Treeview Table
        table_frame = ttk.Frame(self, padding="14")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "code", "customer", "product", "plan", "variant", "price", "cycle", "next_billing", "status", "auto_renew")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Sub Code")
        self.tree.heading("customer", text="Customer")
        self.tree.heading("product", text="Product")
        self.tree.heading("plan", text="Plan")
        self.tree.heading("variant", text="Variant / Tier")
        self.tree.heading("price", text="Price")
        self.tree.heading("cycle", text="Cycle")
        self.tree.heading("next_billing", text="Next Billing")
        self.tree.heading("status", text="Status")
        self.tree.heading("auto_renew", text="Auto-Renew")

        self.tree.column("id", width=35, anchor=tk.CENTER)
        self.tree.column("code", width=105, anchor=tk.W)
        self.tree.column("customer", width=140, anchor=tk.W)
        self.tree.column("product", width=120, anchor=tk.W)
        self.tree.column("plan", width=150, anchor=tk.W)
        self.tree.column("variant", width=120, anchor=tk.W)
        self.tree.column("price", width=75, anchor=tk.E)
        self.tree.column("cycle", width=80, anchor=tk.CENTER)
        self.tree.column("next_billing", width=95, anchor=tk.CENTER)
        self.tree.column("status", width=80, anchor=tk.CENTER)
        self.tree.column("auto_renew", width=85, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 5. Bottom Action Bar
        bottom_bar = ttk.Frame(self, padding="12")
        bottom_bar.pack(fill=tk.X)

        pause_btn = ttk.Button(bottom_bar, text="⏸️ Pause / Resume", command=self._toggle_pause)
        pause_btn.pack(side=tk.LEFT, padx=6)

        change_btn = ttk.Button(bottom_bar, text="🔄 Upgrade / Switch Plan", command=self._open_change_plan)
        change_btn.pack(side=tk.LEFT, padx=6)

        renew_btn = ttk.Button(bottom_bar, text="🔁 Renew Now", command=self._renew_selected)
        renew_btn.pack(side=tk.LEFT, padx=6)

        cancel_btn = ttk.Button(bottom_bar, text="❌ Cancel Sub", command=self._cancel_selected)
        cancel_btn.pack(side=tk.LEFT, padx=6)

        del_btn = ttk.Button(bottom_bar, text="🗑️ Delete", command=self._delete_selected)
        del_btn.pack(side=tk.LEFT, padx=6)

        refresh_btn = ttk.Button(bottom_bar, text="🔄 Refresh", command=self.refresh)
        refresh_btn.pack(side=tk.RIGHT, padx=6)

    def _create_kpi_card(self, parent, title, initial_value, border_color):
        card = tk.Frame(parent, bg="#FFFFFF", highlightbackground=border_color, highlightthickness=2, padx=12, pady=8)
        card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        t_lbl = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#6C757D", bg="#FFFFFF")
        t_lbl.pack(anchor=tk.W)

        v_lbl = tk.Label(card, text=initial_value, font=("Segoe UI", 14, "bold"), fg="#212529", bg="#FFFFFF")
        v_lbl.pack(anchor=tk.W)

        return v_lbl

    def _reset_filters(self):
        self.status_filter_var.set("All Statuses")
        self.product_filter_var.set("All Products")
        self.search_var.set("")
        self.refresh()

    def refresh(self):
        """Update product dropdown, reload subscription list and KPI cards."""
        products = db.fetch_all("SELECT id, name FROM products ORDER BY name ASC")
        product_options = ["All Products"] + [f"{p['id']}: {p['name']}" for p in products]
        self.product_filter_map = {f"{p['id']}: {p['name']}": p['id'] for p in products}
        self.product_filter['values'] = product_options

        sel_prod = self.product_filter_var.get()
        prod_id = self.product_filter_map.get(sel_prod, None)

        for item in self.tree.get_children():
            self.tree.delete(item)

        subs = SubscriptionManager.get_all_subscriptions(
            status=self.status_filter_var.get(),
            product_id=prod_id,
            search_term=self.search_var.get()
        )

        for s in subs:
            var_text = s['variant_name'] if s['variant_name'] else "Standard"
            auto_text = "Yes" if s['auto_renew'] else "No"
            self.tree.insert("", tk.END, values=(
                s['id'],
                s['subscription_code'],
                s['customer_name'],
                s['product_name'],
                s['plan_name'],
                var_text,
                f"${s['total_price']:.2f}",
                s['billing_cycle'],
                str(s['next_billing_date'])[:10],
                s['status'],
                auto_text
            ))

        # Update KPIs
        kpis = SubscriptionManager.get_kpis()
        self.card_total.config(text=str(kpis['total']))
        self.card_active.config(text=str(kpis['active']))
        self.card_trial.config(text=str(kpis['trial']))
        self.card_paused.config(text=str(kpis['paused']))
        self.card_mrr.config(text=f"${kpis['mrr']:,.2f}")

    def _get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a subscription from the table.")
            return None
        return self.tree.item(selected[0])['values'][0]

    def _open_new_wizard(self):
        SubscriptionWizard(self, on_success=self.refresh)

    def _open_change_plan(self):
        sub_id = self._get_selected_id()
        if sub_id:
            ChangePlanDialog(self, subscription_id=sub_id, on_success=self.refresh)

    def _toggle_pause(self):
        sub_id = self._get_selected_id()
        if not sub_id:
            return
        success, msg = SubscriptionManager.toggle_pause(sub_id)
        if success:
            messagebox.showinfo("Status Updated", msg)
            self.refresh()
        else:
            messagebox.showerror("Error", msg)

    def _renew_selected(self):
        sub_id = self._get_selected_id()
        if not sub_id:
            return
        confirm = messagebox.askyesno("Renew Subscription", "Do you want to renew this subscription for another billing cycle?")
        if confirm:
            success, msg = SubscriptionManager.renew_subscription(sub_id)
            if success:
                messagebox.showinfo("Renewed", msg)
                self.refresh()
            else:
                messagebox.showerror("Error", msg)

    def _cancel_selected(self):
        sub_id = self._get_selected_id()
        if not sub_id:
            return
        confirm = messagebox.askyesno("Cancel Subscription", "Are you sure you want to cancel this customer subscription?", icon='warning')
        if confirm:
            success, msg = SubscriptionManager.update_status(sub_id, "Cancelled")
            if success:
                messagebox.showinfo("Cancelled", msg)
                self.refresh()
            else:
                messagebox.showerror("Error", msg)

    def _delete_selected(self):
        sub_id = self._get_selected_id()
        if not sub_id:
            return
        confirm = messagebox.askyesno("Delete Subscription", "Permanently delete this subscription record?", icon='warning')
        if confirm:
            success, msg = SubscriptionManager.delete_subscription(sub_id)
            if success:
                messagebox.showinfo("Deleted", msg)
                self.refresh()
            else:
                messagebox.showerror("Error", msg)


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("BrightLoop - Subscriptions Management (Member 2)")
    root.geometry("1100x680")
    style = ttk.Style(root)
    style.theme_use("clam")
    app = SubscriptionView(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
