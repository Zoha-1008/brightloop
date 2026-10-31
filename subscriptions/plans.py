"""
subscriptions/plans.py - Subscription Plan Management Module (Member 2 Deliverable)
Subscription Management System

Provides complete backend CRUD operations and a modern Tkinter GUI for managing subscription plans.
Integrates directly with Products and Variants.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class PlanManager:
    """Backend Data Access Object for Subscription Plans."""

    BILLING_CYCLES = ["Monthly", "Quarterly", "Semi-Annual", "Annual", "Lifetime"]

    @staticmethod
    def get_all_plans(product_id=None, search_term=None, cycle=None, status=None):
        """Fetch plans with product details and optional filtering."""
        query = """
            SELECT pl.*, pr.name AS product_name, pr.product_code
            FROM plans pl
            JOIN products pr ON pl.product_id = pr.id
            WHERE 1=1
        """
        params = []

        if product_id and product_id != "All Products":
            query += " AND pl.product_id = %s"
            params.append(product_id)

        if cycle and cycle != "All Cycles":
            query += " AND pl.billing_cycle = %s"
            params.append(cycle)

        if status and status != "All Statuses":
            query += " AND pl.status = %s"
            params.append(status)

        if search_term:
            query += " AND (pl.plan_code LIKE %s OR pl.name LIKE %s OR pr.name LIKE %s OR pl.features LIKE %s)"
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw, kw])

        query += " ORDER BY pr.name ASC, pl.price ASC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_plan_by_id(plan_id):
        """Fetch plan by ID including linked product details."""
        query = """
            SELECT pl.*, pr.name AS product_name, pr.product_code
            FROM plans pl
            JOIN products pr ON pl.product_id = pr.id
            WHERE pl.id = %s
        """
        return db.fetch_one(query, (plan_id,))

    @staticmethod
    def get_plan_by_code(plan_code):
        """Fetch plan by unique plan code."""
        return db.fetch_one("SELECT * FROM plans WHERE plan_code = %s", (plan_code,))

    @staticmethod
    def get_plans_for_product(product_id):
        """Retrieve active plans for a given product."""
        return db.fetch_all("SELECT * FROM plans WHERE product_id = %s AND status = 'Active' ORDER BY price ASC", (product_id,))

    @staticmethod
    def add_plan(product_id, plan_code, name, billing_cycle, price, currency='USD', trial_days=0, features='', status='Active'):
        """Create a new subscription plan."""
        plan_code = plan_code.strip().upper()
        name = name.strip()
        features = features.strip()

        if not product_id or not plan_code or not name:
            return False, "Product, Plan Code, and Plan Name are required."

        try:
            price_val = float(price)
            if price_val < 0:
                return False, "Price cannot be negative."
        except ValueError:
            return False, "Price must be a valid number (e.g., 19.99)."

        try:
            trial_val = int(trial_days) if trial_days else 0
            if trial_val < 0:
                return False, "Trial days cannot be negative."
        except ValueError:
            return False, "Trial days must be an integer."

        existing = PlanManager.get_plan_by_code(plan_code)
        if existing:
            return False, f"Plan code '{plan_code}' already exists."

        try:
            db.execute_query(
                """
                INSERT INTO plans (product_id, plan_code, name, billing_cycle, price, currency, trial_days, features, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (product_id, plan_code, name, billing_cycle, price_val, currency, trial_val, features, status)
            )
            return True, "Subscription plan created successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def update_plan(plan_id, product_id, plan_code, name, billing_cycle, price, currency='USD', trial_days=0, features='', status='Active'):
        """Update an existing plan."""
        plan_code = plan_code.strip().upper()
        name = name.strip()
        features = features.strip()

        if not product_id or not plan_code or not name:
            return False, "Product, Plan Code, and Plan Name are required."

        try:
            price_val = float(price)
            if price_val < 0:
                return False, "Price cannot be negative."
        except ValueError:
            return False, "Price must be a valid number."

        try:
            trial_val = int(trial_days) if trial_days else 0
            if trial_val < 0:
                return False, "Trial days cannot be negative."
        except ValueError:
            return False, "Trial days must be an integer."

        existing = PlanManager.get_plan_by_code(plan_code)
        if existing and existing['id'] != int(plan_id):
            return False, f"Plan code '{plan_code}' is already used by another plan."

        try:
            db.execute_query(
                """
                UPDATE plans
                SET product_id = %s, plan_code = %s, name = %s, billing_cycle = %s,
                    price = %s, currency = %s, trial_days = %s, features = %s, status = %s
                WHERE id = %s
                """,
                (product_id, plan_code, name, billing_cycle, price_val, currency, trial_val, features, status, plan_id)
            )
            return True, "Subscription plan updated successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete_plan(plan_id):
        """Delete plan if no customer subscriptions reference it."""
        try:
            subs = db.fetch_all("SELECT COUNT(*) as cnt FROM subscriptions WHERE plan_id = %s", (plan_id,))
            sub_count = subs[0]['cnt'] if subs else 0
            if sub_count > 0:
                return False, f"Cannot delete: Plan is active in {sub_count} customer subscriptions. You may set status to 'Inactive' instead."

            # Variants cascade delete through foreign key
            db.execute_query("DELETE FROM plans WHERE id = %s", (plan_id,))
            return True, "Plan and associated variants deleted successfully."
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    @staticmethod
    def get_stats():
        """Retrieve count of plans."""
        total = db.fetch_one("SELECT COUNT(*) as cnt FROM plans")['cnt']
        active = db.fetch_one("SELECT COUNT(*) as cnt FROM plans WHERE status = 'Active'")['cnt']
        return {'total': total, 'active': active}


class PlanFormDialog(tk.Toplevel):
    """Modal dialog to create or edit a subscription plan."""

    def __init__(self, parent, plan_id=None, preselected_product_id=None, on_success=None):
        super().__init__(parent)
        self.plan_id = plan_id
        self.preselected_product_id = preselected_product_id
        self.on_success = on_success
        self.is_edit = plan_id is not None

        self.title("Edit Subscription Plan" if self.is_edit else "Add New Subscription Plan")
        self.geometry("540x550")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._load_products()
        self._build_ui()
        if self.is_edit:
            self._load_data()

    def _load_products(self):
        self.products = db.fetch_all("SELECT id, product_code, name FROM products WHERE status = 'Active' ORDER BY name ASC")
        self.product_options = [f"{p['id']}: {p['name']} ({p['product_code']})" for p in self.products]
        self.product_id_map = {f"{p['id']}: {p['name']} ({p['product_code']})": p['id'] for p in self.products}

    def _build_ui(self):
        self.configure(bg="#F8F9FA")
        container = ttk.Frame(self, padding="24")
        container.pack(fill=tk.BOTH, expand=True)

        header_lbl = ttk.Label(
            container,
            text="✏️ Edit Plan" if self.is_edit else "💳 Define New Subscription Plan",
            font=("Segoe UI", 14, "bold")
        )
        header_lbl.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 16))

        # 1. Product Selector
        ttk.Label(container, text="Target Product *:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(container, textvariable=self.product_var, values=self.product_options, state="readonly", width=34)
        self.product_combo.grid(row=1, column=1, sticky=tk.W, pady=6)
        if self.product_options:
            if self.preselected_product_id:
                for opt, pid in self.product_id_map.items():
                    if pid == self.preselected_product_id:
                        self.product_var.set(opt)
                        break
            else:
                self.product_combo.current(0)

        # 2. Plan Code
        ttk.Label(container, text="Plan Code *:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(container, textvariable=self.code_var, width=36)
        self.code_entry.grid(row=2, column=1, sticky=tk.W, pady=6)

        # 3. Plan Name
        ttk.Label(container, text="Plan Name *:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=6)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(container, textvariable=self.name_var, width=36)
        self.name_entry.grid(row=3, column=1, sticky=tk.W, pady=6)

        # 4. Billing Cycle
        ttk.Label(container, text="Billing Cycle *:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky=tk.W, pady=6)
        self.cycle_var = tk.StringVar(value="Monthly")
        self.cycle_combo = ttk.Combobox(container, textvariable=self.cycle_var, values=PlanManager.BILLING_CYCLES, state="readonly", width=34)
        self.cycle_combo.grid(row=4, column=1, sticky=tk.W, pady=6)

        # 5. Price & Currency
        ttk.Label(container, text="Price & Currency *:", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky=tk.W, pady=6)
        price_frame = ttk.Frame(container)
        price_frame.grid(row=5, column=1, sticky=tk.W, pady=6)

        self.price_var = tk.StringVar(value="0.00")
        self.price_entry = ttk.Entry(price_frame, textvariable=self.price_var, width=16)
        self.price_entry.pack(side=tk.LEFT)

        self.currency_var = tk.StringVar(value="USD")
        self.currency_combo = ttk.Combobox(price_frame, textvariable=self.currency_var, values=["USD", "EUR", "GBP", "INR", "CAD"], width=8, state="readonly")
        self.currency_combo.pack(side=tk.LEFT, padx=(8, 0))

        # 6. Trial Period
        ttk.Label(container, text="Trial Days:", font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky=tk.W, pady=6)
        self.trial_var = tk.StringVar(value="0")
        self.trial_entry = ttk.Entry(container, textvariable=self.trial_var, width=16)
        self.trial_entry.grid(row=6, column=1, sticky=tk.W, pady=6)

        # 7. Status
        ttk.Label(container, text="Status:", font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky=tk.W, pady=6)
        self.status_var = tk.StringVar(value="Active")
        self.status_combo = ttk.Combobox(container, textvariable=self.status_var, values=["Active", "Inactive"], state="readonly", width=34)
        self.status_combo.grid(row=7, column=1, sticky=tk.W, pady=6)

        # 8. Features Description
        ttk.Label(container, text="Features / Perks:", font=("Segoe UI", 9, "bold")).grid(row=8, column=0, sticky=tk.NW, pady=6)
        self.features_text = tk.Text(container, width=36, height=4, font=("Segoe UI", 9))
        self.features_text.grid(row=8, column=1, sticky=tk.W, pady=6)

        # Action Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=9, column=0, columnspan=2, sticky=tk.E, pady=(18, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=6)

        save_btn = ttk.Button(btn_frame, text="Save Plan", command=self._save)
        save_btn.pack(side=tk.RIGHT, padx=6)

    def _load_data(self):
        plan = PlanManager.get_plan_by_id(self.plan_id)
        if plan:
            # Set product
            for opt, pid in self.product_id_map.items():
                if pid == plan['product_id']:
                    self.product_var.set(opt)
                    break
            self.code_var.set(plan['plan_code'])
            self.name_var.set(plan['name'])
            self.cycle_var.set(plan['billing_cycle'])
            self.price_var.set(f"{plan['price']:.2f}")
            self.currency_var.set(plan['currency'])
            self.trial_var.set(str(plan['trial_days']))
            self.status_var.set(plan['status'])
            self.features_text.delete("1.0", tk.END)
            self.features_text.insert("1.0", plan['features'] or "")

    def _save(self):
        selected_product = self.product_var.get()
        if not selected_product or selected_product not in self.product_id_map:
            messagebox.showerror("Error", "Please select a valid product.", parent=self)
            return

        product_id = self.product_id_map[selected_product]
        code = self.code_var.get()
        name = self.name_var.get()
        cycle = self.cycle_var.get()
        price = self.price_var.get()
        currency = self.currency_var.get()
        trial = self.trial_var.get()
        status = self.status_var.get()
        features = self.features_text.get("1.0", tk.END).strip()

        if self.is_edit:
            success, msg = PlanManager.update_plan(self.plan_id, product_id, code, name, cycle, price, currency, trial, features, status)
        else:
            success, msg = PlanManager.add_plan(product_id, code, name, cycle, price, currency, trial, features, status)

        if success:
            messagebox.showinfo("Success", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Validation Error", msg, parent=self)


class PlanView(ttk.Frame):
    """Main Plan Management View Component for Member 2."""

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
            text="💳 Subscription Plan Management",
            font=("Segoe UI", 16, "bold")
        )
        title_lbl.pack(side=tk.LEFT)

        self.stats_lbl = ttk.Label(
            header_frame,
            text="Total Plans: 0 | Active: 0",
            font=("Segoe UI", 10),
            foreground="#495057"
        )
        self.stats_lbl.pack(side=tk.RIGHT, pady=4)

        # 2. Filter Toolbar
        filter_frame = ttk.LabelFrame(self, text=" Filter & Search Plans ", padding="10")
        filter_frame.pack(fill=tk.X, padx=14, pady=6)

        # Product filter
        ttk.Label(filter_frame, text="Product:").pack(side=tk.LEFT, padx=(0, 4))
        self.product_filter_var = tk.StringVar(value="All Products")
        self.product_filter = ttk.Combobox(filter_frame, textvariable=self.product_filter_var, state="readonly", width=22)
        self.product_filter.pack(side=tk.LEFT, padx=4)
        self.product_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Billing cycle filter
        ttk.Label(filter_frame, text="Cycle:").pack(side=tk.LEFT, padx=(10, 4))
        self.cycle_filter_var = tk.StringVar(value="All Cycles")
        cycles = ["All Cycles"] + PlanManager.BILLING_CYCLES
        self.cycle_filter = ttk.Combobox(filter_frame, textvariable=self.cycle_filter_var, values=cycles, state="readonly", width=12)
        self.cycle_filter.pack(side=tk.LEFT, padx=4)
        self.cycle_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Status filter
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(10, 4))
        self.status_filter_var = tk.StringVar(value="All Statuses")
        self.status_filter = ttk.Combobox(filter_frame, textvariable=self.status_filter_var, values=["All Statuses", "Active", "Inactive"], state="readonly", width=12)
        self.status_filter.pack(side=tk.LEFT, padx=4)
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Search box
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(10, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=16)
        self.search_entry.pack(side=tk.LEFT, padx=4)
        self.search_entry.bind("<Return>", lambda e: self.refresh())

        search_btn = ttk.Button(filter_frame, text="🔍 Search", command=self.refresh)
        search_btn.pack(side=tk.LEFT, padx=6)

        reset_btn = ttk.Button(filter_frame, text="Reset", command=self._reset_filters)
        reset_btn.pack(side=tk.LEFT, padx=4)

        add_btn = ttk.Button(filter_frame, text="➕ Add Plan", command=self._open_add_dialog)
        add_btn.pack(side=tk.RIGHT, padx=4)

        # 3. Table (Treeview)
        table_frame = ttk.Frame(self, padding="14")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "code", "name", "product", "cycle", "price", "trial", "status", "features")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Plan Code")
        self.tree.heading("name", text="Plan Name")
        self.tree.heading("product", text="Product")
        self.tree.heading("cycle", text="Cycle")
        self.tree.heading("price", text="Price")
        self.tree.heading("trial", text="Trial Days")
        self.tree.heading("status", text="Status")
        self.tree.heading("features", text="Features & Perks")

        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("code", width=110, anchor=tk.W)
        self.tree.column("name", width=170, anchor=tk.W)
        self.tree.column("product", width=150, anchor=tk.W)
        self.tree.column("cycle", width=85, anchor=tk.CENTER)
        self.tree.column("price", width=80, anchor=tk.E)
        self.tree.column("trial", width=70, anchor=tk.CENTER)
        self.tree.column("status", width=75, anchor=tk.CENTER)
        self.tree.column("features", width=240, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._open_edit_dialog())

        # 4. Bottom Actions
        bottom_bar = ttk.Frame(self, padding="12")
        bottom_bar.pack(fill=tk.X)

        edit_btn = ttk.Button(bottom_bar, text="✏️ Edit Selected", command=self._open_edit_dialog)
        edit_btn.pack(side=tk.LEFT, padx=6)

        del_btn = ttk.Button(bottom_bar, text="🗑️ Delete Plan", command=self._delete_selected)
        del_btn.pack(side=tk.LEFT, padx=6)

        view_vars_btn = ttk.Button(bottom_bar, text="🏷️ View Plan Variants", command=self._view_variants)
        view_vars_btn.pack(side=tk.LEFT, padx=6)

        refresh_btn = ttk.Button(bottom_bar, text="🔄 Refresh", command=self.refresh)
        refresh_btn.pack(side=tk.RIGHT, padx=6)

    def _reset_filters(self):
        self.product_filter_var.set("All Products")
        self.cycle_filter_var.set("All Cycles")
        self.status_filter_var.set("All Statuses")
        self.search_var.set("")
        self.refresh()

    def refresh(self):
        """Update products dropdown and fetch plans."""
        products = db.fetch_all("SELECT id, name FROM products ORDER BY name ASC")
        product_options = ["All Products"] + [f"{p['id']}: {p['name']}" for p in products]
        self.product_filter_map = {f"{p['id']}: {p['name']}": p['id'] for p in products}
        self.product_filter['values'] = product_options

        sel_prod = self.product_filter_var.get()
        prod_id = self.product_filter_map.get(sel_prod, None)

        for item in self.tree.get_children():
            self.tree.delete(item)

        plans = PlanManager.get_all_plans(
            product_id=prod_id,
            search_term=self.search_var.get(),
            cycle=self.cycle_filter_var.get(),
            status=self.status_filter_var.get()
        )

        for pl in plans:
            self.tree.insert("", tk.END, values=(
                pl['id'],
                pl['plan_code'],
                pl['name'],
                f"{pl['product_name']} ({pl['product_code']})",
                pl['billing_cycle'],
                f"{pl['price']:.2f} {pl['currency']}",
                f"{pl['trial_days']} days" if pl['trial_days'] else "None",
                pl['status'],
                pl['features'] or ""
            ))

        stats = PlanManager.get_stats()
        self.stats_lbl.config(text=f"Total Plans: {stats['total']}  |  Active: {stats['active']}")

    def _get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a plan from the list.")
            return None
        return self.tree.item(selected[0])['values'][0]

    def _open_add_dialog(self):
        PlanFormDialog(self, on_success=self.refresh)

    def _open_edit_dialog(self):
        plan_id = self._get_selected_id()
        if plan_id:
            PlanFormDialog(self, plan_id=plan_id, on_success=self.refresh)

    def _delete_selected(self):
        plan_id = self._get_selected_id()
        if not plan_id:
            return

        plan = PlanManager.get_plan_by_id(plan_id)
        if not plan:
            return

        confirm = messagebox.askyesno(
            "Confirm Plan Deletion",
            f"Are you sure you want to delete plan '{plan['name']}' ({plan['plan_code']})?\n"
            f"Any associated variants will also be removed.",
            icon='warning'
        )
        if confirm:
            success, msg = PlanManager.delete_plan(plan_id)
            if success:
                messagebox.showinfo("Success", msg)
                self.refresh()
            else:
                messagebox.showerror("Error", msg)

    def _view_variants(self):
        plan_id = self._get_selected_id()
        if not plan_id:
            return

        plan = PlanManager.get_plan_by_id(plan_id)
        variants = db.fetch_all("SELECT variant_code, name, attribute_type, attribute_value, price_adjustment, status FROM variants WHERE plan_id = %s", (plan_id,))

        win = tk.Toplevel(self)
        win.title(f"Variants for {plan['name']}")
        win.geometry("560x320")
        win.transient(self)

        lbl = ttk.Label(win, text=f"Variants for: {plan['name']} ({plan['plan_code']})", font=("Segoe UI", 11, "bold"))
        lbl.pack(pady=10, padx=12, anchor=tk.W)

        if not variants:
            ttk.Label(win, text="No variants or add-ons attached to this plan.", font=("Segoe UI", 10, "italic")).pack(pady=30)
            return

        cols = ("code", "name", "attr_type", "attr_val", "price_adj", "status")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=8)
        tree.heading("code", text="Variant Code")
        tree.heading("name", text="Name")
        tree.heading("attr_type", text="Type")
        tree.heading("attr_val", text="Value")
        tree.heading("price_adj", text="Adj Price")
        tree.heading("status", text="Status")

        tree.column("code", width=100)
        tree.column("name", width=130)
        tree.column("attr_type", width=100)
        tree.column("attr_val", width=80)
        tree.column("price_adj", width=80, anchor=tk.E)
        tree.column("status", width=70, anchor=tk.CENTER)

        for v in variants:
            tree.insert("", tk.END, values=(
                v['variant_code'],
                v['name'],
                v['attribute_type'],
                v['attribute_value'],
                f"+{v['price_adjustment']:.2f}",
                v['status']
            ))
        tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("BrightLoop - Plan Management (Member 2)")
    root.geometry("960x580")
    style = ttk.Style(root)
    style.theme_use("clam")
    app = PlanView(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
