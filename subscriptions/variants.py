"""
subscriptions/variants.py - Plan Variant & Add-on Management Module (Member 2 Deliverable)
Subscription Management System

Provides complete backend CRUD operations and a modern Tkinter GUI for managing plan variants.
Allows customizing plan options, add-ons, tiers, and price adjustments.
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


class VariantManager:
    """Backend Data Access Object for Plan Variants & Add-ons."""

    COMMON_ATTRIBUTE_TYPES = [
        "Storage Capacity",
        "User Seats",
        "Audio/Video Quality",
        "Bandwidth Limit",
        "Support Tier",
        "API Request Limit",
        "Device Limit"
    ]

    @staticmethod
    def get_all_variants(plan_id=None, search_term=None, attr_type=None, status=None):
        """Fetch variants with joined plan and product details."""
        query = """
            SELECT v.*, pl.name AS plan_name, pl.plan_code, pl.price AS base_price,
                   pr.name AS product_name, pr.product_code
            FROM variants v
            JOIN plans pl ON v.plan_id = pl.id
            JOIN products pr ON pl.product_id = pr.id
            WHERE 1=1
        """
        params = []

        if plan_id and plan_id != "All Plans":
            query += " AND v.plan_id = %s"
            params.append(plan_id)

        if attr_type and attr_type != "All Types":
            query += " AND v.attribute_type = %s"
            params.append(attr_type)

        if status and status != "All Statuses":
            query += " AND v.status = %s"
            params.append(status)

        if search_term:
            query += """ AND (
                v.variant_code LIKE %s OR v.name LIKE %s OR
                v.attribute_value LIKE %s OR pl.name LIKE %s OR pr.name LIKE %s
            )"""
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw, kw, kw])

        query += " ORDER BY pr.name ASC, pl.name ASC, v.price_adjustment ASC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_variant_by_id(variant_id):
        """Fetch a single variant with joined plan and product info."""
        query = """
            SELECT v.*, pl.name AS plan_name, pl.plan_code, pl.price AS base_price,
                   pr.name AS product_name, pr.product_code
            FROM variants v
            JOIN plans pl ON v.plan_id = pl.id
            JOIN products pr ON pl.product_id = pr.id
            WHERE v.id = %s
        """
        return db.fetch_one(query, (variant_id,))

    @staticmethod
    def get_variant_by_code(variant_code):
        """Fetch variant by code."""
        return db.fetch_one("SELECT * FROM variants WHERE variant_code = %s", (variant_code,))

    @staticmethod
    def get_variants_for_plan(plan_id):
        """Fetch active variants belonging to a specific plan."""
        return db.fetch_all("SELECT * FROM variants WHERE plan_id = %s AND status = 'Active' ORDER BY price_adjustment ASC", (plan_id,))

    @staticmethod
    def add_variant(plan_id, variant_code, name, attribute_type, attribute_value, price_adjustment=0.0, status='Active'):
        """Create a new plan variant."""
        variant_code = variant_code.strip().upper()
        name = name.strip()
        attribute_type = attribute_type.strip()
        attribute_value = attribute_value.strip()

        if not plan_id or not variant_code or not name or not attribute_type or not attribute_value:
            return False, "Plan, Variant Code, Name, Attribute Type, and Value are required."

        try:
            adj = float(price_adjustment)
        except ValueError:
            return False, "Price adjustment must be a valid number (e.g. 5.00 or 0.00)."

        existing = VariantManager.get_variant_by_code(variant_code)
        if existing:
            return False, f"Variant code '{variant_code}' already exists."

        try:
            db.execute_query(
                """
                INSERT INTO variants (plan_id, variant_code, name, attribute_type, attribute_value, price_adjustment, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (plan_id, variant_code, name, attribute_type, attribute_value, adj, status)
            )
            return True, "Variant created successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def update_variant(variant_id, plan_id, variant_code, name, attribute_type, attribute_value, price_adjustment=0.0, status='Active'):
        """Update an existing variant."""
        variant_code = variant_code.strip().upper()
        name = name.strip()
        attribute_type = attribute_type.strip()
        attribute_value = attribute_value.strip()

        if not plan_id or not variant_code or not name or not attribute_type or not attribute_value:
            return False, "Plan, Variant Code, Name, Attribute Type, and Value are required."

        try:
            adj = float(price_adjustment)
        except ValueError:
            return False, "Price adjustment must be a valid number."

        existing = VariantManager.get_variant_by_code(variant_code)
        if existing and existing['id'] != int(variant_id):
            return False, f"Variant code '{variant_code}' is already used by another variant."

        try:
            db.execute_query(
                """
                UPDATE variants
                SET plan_id = %s, variant_code = %s, name = %s, attribute_type = %s,
                    attribute_value = %s, price_adjustment = %s, status = %s
                WHERE id = %s
                """,
                (plan_id, variant_code, name, attribute_type, attribute_value, adj, status, variant_id)
            )
            return True, "Variant updated successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete_variant(variant_id):
        """Delete variant if not actively used in subscriptions."""
        try:
            subs = db.fetch_all("SELECT COUNT(*) as cnt FROM subscriptions WHERE variant_id = %s", (variant_id,))
            sub_count = subs[0]['cnt'] if subs else 0
            if sub_count > 0:
                return False, f"Cannot delete: Variant is assigned to {sub_count} active/past customer subscriptions. Set status to 'Inactive' instead."

            db.execute_query("DELETE FROM variants WHERE id = %s", (variant_id,))
            return True, "Variant deleted successfully."
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    @staticmethod
    def get_stats():
        """Retrieve total and active variant count."""
        total = db.fetch_one("SELECT COUNT(*) as cnt FROM variants")['cnt']
        active = db.fetch_one("SELECT COUNT(*) as cnt FROM variants WHERE status = 'Active'")['cnt']
        return {'total': total, 'active': active}


class VariantFormDialog(tk.Toplevel):
    """Modal dialog to create or edit plan variants."""

    def __init__(self, parent, variant_id=None, preselected_plan_id=None, on_success=None):
        super().__init__(parent)
        self.variant_id = variant_id
        self.preselected_plan_id = preselected_plan_id
        self.on_success = on_success
        self.is_edit = variant_id is not None

        self.title("Edit Variant" if self.is_edit else "Add New Plan Variant")
        self.geometry("520x510")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._load_plans()
        self._build_ui()
        if self.is_edit:
            self._load_data()

    def _load_plans(self):
        plans = db.fetch_all("""
            SELECT pl.id, pl.plan_code, pl.name AS plan_name, pr.name AS product_name
            FROM plans pl
            JOIN products pr ON pl.product_id = pr.id
            WHERE pl.status = 'Active'
            ORDER BY pr.name ASC, pl.name ASC
        """)
        self.plan_options = [f"{p['id']}: [{p['product_name']}] {p['plan_name']} ({p['plan_code']})" for p in plans]
        self.plan_id_map = {f"{p['id']}: [{p['product_name']}] {p['plan_name']} ({p['plan_code']})": p['id'] for p in plans}

    def _build_ui(self):
        self.configure(bg="#F8F9FA")
        container = ttk.Frame(self, padding="24")
        container.pack(fill=tk.BOTH, expand=True)

        header_lbl = ttk.Label(
            container,
            text="✏️ Edit Variant" if self.is_edit else "🏷️ Add Plan Variant / Option",
            font=("Segoe UI", 14, "bold")
        )
        header_lbl.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 16))

        # 1. Target Plan
        ttk.Label(container, text="Target Plan *:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.plan_var = tk.StringVar()
        self.plan_combo = ttk.Combobox(container, textvariable=self.plan_var, values=self.plan_options, state="readonly", width=34)
        self.plan_combo.grid(row=1, column=1, sticky=tk.W, pady=6)
        if self.plan_options:
            if self.preselected_plan_id:
                for opt, pid in self.plan_id_map.items():
                    if pid == self.preselected_plan_id:
                        self.plan_var.set(opt)
                        break
            else:
                self.plan_combo.current(0)

        # 2. Variant Code
        ttk.Label(container, text="Variant Code *:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(container, textvariable=self.code_var, width=36)
        self.code_entry.grid(row=2, column=1, sticky=tk.W, pady=6)

        # 3. Variant Name
        ttk.Label(container, text="Variant Name *:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=6)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(container, textvariable=self.name_var, width=36)
        self.name_entry.grid(row=3, column=1, sticky=tk.W, pady=6)

        # 4. Attribute Type
        ttk.Label(container, text="Attribute Type *:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky=tk.W, pady=6)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(container, textvariable=self.type_var, values=VariantManager.COMMON_ATTRIBUTE_TYPES, width=34)
        self.type_combo.grid(row=4, column=1, sticky=tk.W, pady=6)

        # 5. Attribute Value
        ttk.Label(container, text="Attribute Value *:", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky=tk.W, pady=6)
        self.val_var = tk.StringVar()
        self.val_entry = ttk.Entry(container, textvariable=self.val_var, width=36)
        self.val_entry.grid(row=5, column=1, sticky=tk.W, pady=6)
        ttk.Label(container, text="(e.g. '1TB', '5 Seats', '4K UHD')", font=("Segoe UI", 8), foreground="#6C757D").grid(row=6, column=1, sticky=tk.W)

        # 6. Price Adjustment
        ttk.Label(container, text="Price Adjustment ($):", font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky=tk.W, pady=6)
        self.adj_var = tk.StringVar(value="0.00")
        self.adj_entry = ttk.Entry(container, textvariable=self.adj_var, width=20)
        self.adj_entry.grid(row=7, column=1, sticky=tk.W, pady=6)
        ttk.Label(container, text="(Amount added to base plan price. Set 0 for default tier)", font=("Segoe UI", 8), foreground="#6C757D").grid(row=8, column=1, sticky=tk.W)

        # 7. Status
        ttk.Label(container, text="Status:", font=("Segoe UI", 9, "bold")).grid(row=9, column=0, sticky=tk.W, pady=6)
        self.status_var = tk.StringVar(value="Active")
        self.status_combo = ttk.Combobox(container, textvariable=self.status_var, values=["Active", "Inactive"], state="readonly", width=34)
        self.status_combo.grid(row=9, column=1, sticky=tk.W, pady=6)

        # Action Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=10, column=0, columnspan=2, sticky=tk.E, pady=(20, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=6)

        save_btn = ttk.Button(btn_frame, text="Save Variant", command=self._save)
        save_btn.pack(side=tk.RIGHT, padx=6)

    def _load_data(self):
        v = VariantManager.get_variant_by_id(self.variant_id)
        if v:
            for opt, pid in self.plan_id_map.items():
                if pid == v['plan_id']:
                    self.plan_var.set(opt)
                    break
            self.code_var.set(v['variant_code'])
            self.name_var.set(v['name'])
            self.type_var.set(v['attribute_type'])
            self.val_var.set(v['attribute_value'])
            self.adj_var.set(f"{v['price_adjustment']:.2f}")
            self.status_var.set(v['status'])

    def _save(self):
        selected_plan = self.plan_var.get()
        if not selected_plan or selected_plan not in self.plan_id_map:
            messagebox.showerror("Error", "Please select a valid plan.", parent=self)
            return

        plan_id = self.plan_id_map[selected_plan]
        code = self.code_var.get()
        name = self.name_var.get()
        attr_type = self.type_var.get()
        attr_val = self.val_var.get()
        adj = self.adj_var.get()
        status = self.status_var.get()

        if self.is_edit:
            success, msg = VariantManager.update_variant(self.variant_id, plan_id, code, name, attr_type, attr_val, adj, status)
        else:
            success, msg = VariantManager.add_variant(plan_id, code, name, attr_type, attr_val, adj, status)

        if success:
            messagebox.showinfo("Success", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Validation Error", msg, parent=self)


class VariantView(ttk.Frame):
    """Main Variant & Add-on Management View Component for Member 2."""

    def __init__(self, parent):
        super().__init__(parent)
        self.plan_filter_map = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        # 1. Header Frame
        header_frame = ttk.Frame(self, padding="14")
        header_frame.pack(fill=tk.X)

        title_lbl = ttk.Label(
            header_frame,
            text="🏷️ Plan Variants & Tier Add-ons",
            font=("Segoe UI", 16, "bold")
        )
        title_lbl.pack(side=tk.LEFT)

        self.stats_lbl = ttk.Label(
            header_frame,
            text="Total Variants: 0 | Active: 0",
            font=("Segoe UI", 10),
            foreground="#495057"
        )
        self.stats_lbl.pack(side=tk.RIGHT, pady=4)

        # 2. Filter Toolbar
        filter_frame = ttk.LabelFrame(self, text=" Filter & Search Variants ", padding="10")
        filter_frame.pack(fill=tk.X, padx=14, pady=6)

        # Plan filter
        ttk.Label(filter_frame, text="Plan:").pack(side=tk.LEFT, padx=(0, 4))
        self.plan_filter_var = tk.StringVar(value="All Plans")
        self.plan_filter = ttk.Combobox(filter_frame, textvariable=self.plan_filter_var, state="readonly", width=22)
        self.plan_filter.pack(side=tk.LEFT, padx=4)
        self.plan_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Type filter
        ttk.Label(filter_frame, text="Attribute:").pack(side=tk.LEFT, padx=(10, 4))
        self.type_filter_var = tk.StringVar(value="All Types")
        self.type_filter = ttk.Combobox(filter_frame, textvariable=self.type_filter_var, state="readonly", width=14)
        self.type_filter.pack(side=tk.LEFT, padx=4)
        self.type_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Status filter
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(10, 4))
        self.status_filter_var = tk.StringVar(value="All Statuses")
        self.status_filter = ttk.Combobox(filter_frame, textvariable=self.status_filter_var, values=["All Statuses", "Active", "Inactive"], state="readonly", width=12)
        self.status_filter.pack(side=tk.LEFT, padx=4)
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Search box
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(10, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=14)
        self.search_entry.pack(side=tk.LEFT, padx=4)
        self.search_entry.bind("<Return>", lambda e: self.refresh())

        search_btn = ttk.Button(filter_frame, text="🔍 Search", command=self.refresh)
        search_btn.pack(side=tk.LEFT, padx=6)

        reset_btn = ttk.Button(filter_frame, text="Reset", command=self._reset_filters)
        reset_btn.pack(side=tk.LEFT, padx=4)

        add_btn = ttk.Button(filter_frame, text="➕ Add Variant", command=self._open_add_dialog)
        add_btn.pack(side=tk.RIGHT, padx=4)

        # 3. Table (Treeview)
        table_frame = ttk.Frame(self, padding="14")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "code", "name", "plan", "product", "attr_type", "attr_val", "price_adj", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Variant Code")
        self.tree.heading("name", text="Variant Name")
        self.tree.heading("plan", text="Parent Plan")
        self.tree.heading("product", text="Product")
        self.tree.heading("attr_type", text="Attribute Type")
        self.tree.heading("attr_val", text="Value")
        self.tree.heading("price_adj", text="Price Adj ($)")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("code", width=110, anchor=tk.W)
        self.tree.column("name", width=170, anchor=tk.W)
        self.tree.column("plan", width=170, anchor=tk.W)
        self.tree.column("product", width=140, anchor=tk.W)
        self.tree.column("attr_type", width=130, anchor=tk.W)
        self.tree.column("attr_val", width=100, anchor=tk.CENTER)
        self.tree.column("price_adj", width=90, anchor=tk.E)
        self.tree.column("status", width=75, anchor=tk.CENTER)

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

        del_btn = ttk.Button(bottom_bar, text="🗑️ Delete Variant", command=self._delete_selected)
        del_btn.pack(side=tk.LEFT, padx=6)

        refresh_btn = ttk.Button(bottom_bar, text="🔄 Refresh", command=self.refresh)
        refresh_btn.pack(side=tk.RIGHT, padx=6)

    def _reset_filters(self):
        self.plan_filter_var.set("All Plans")
        self.type_filter_var.set("All Types")
        self.status_filter_var.set("All Statuses")
        self.search_var.set("")
        self.refresh()

    def refresh(self):
        """Update plans & attribute types dropdowns and fetch variants."""
        plans = db.fetch_all("SELECT id, name, plan_code FROM plans ORDER BY name ASC")
        plan_options = ["All Plans"] + [f"{p['id']}: {p['name']} ({p['plan_code']})" for p in plans]
        self.plan_filter_map = {f"{p['id']}: {p['name']} ({p['plan_code']})": p['id'] for p in plans}
        self.plan_filter['values'] = plan_options

        # Attribute types
        attr_rows = db.fetch_all("SELECT DISTINCT attribute_type FROM variants WHERE attribute_type IS NOT NULL")
        attr_types = ["All Types"] + sorted(list(set([r['attribute_type'] for r in attr_rows] + VariantManager.COMMON_ATTRIBUTE_TYPES)))
        self.type_filter['values'] = attr_types

        sel_plan = self.plan_filter_var.get()
        plan_id = self.plan_filter_map.get(sel_plan, None)

        for item in self.tree.get_children():
            self.tree.delete(item)

        variants = VariantManager.get_all_variants(
            plan_id=plan_id,
            search_term=self.search_var.get(),
            attr_type=self.type_filter_var.get(),
            status=self.status_filter_var.get()
        )

        for v in variants:
            adj_str = f"+${v['price_adjustment']:.2f}" if v['price_adjustment'] >= 0 else f"-${abs(v['price_adjustment']):.2f}"
            self.tree.insert("", tk.END, values=(
                v['id'],
                v['variant_code'],
                v['name'],
                v['plan_name'],
                v['product_name'],
                v['attribute_type'],
                v['attribute_value'],
                adj_str,
                v['status']
            ))

        stats = VariantManager.get_stats()
        self.stats_lbl.config(text=f"Total Variants: {stats['total']}  |  Active: {stats['active']}")

    def _get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a variant from the list.")
            return None
        return self.tree.item(selected[0])['values'][0]

    def _open_add_dialog(self):
        VariantFormDialog(self, on_success=self.refresh)

    def _open_edit_dialog(self):
        var_id = self._get_selected_id()
        if var_id:
            VariantFormDialog(self, variant_id=var_id, on_success=self.refresh)

    def _delete_selected(self):
        var_id = self._get_selected_id()
        if not var_id:
            return

        v = VariantManager.get_variant_by_id(var_id)
        if not v:
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete variant '{v['name']}' ({v['variant_code']})?",
            icon='warning'
        )
        if confirm:
            success, msg = VariantManager.delete_variant(var_id)
            if success:
                messagebox.showinfo("Success", msg)
                self.refresh()
            else:
                messagebox.showerror("Error", msg)


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("BrightLoop - Variant Management (Member 2)")
    root.geometry("980x580")
    style = ttk.Style(root)
    style.theme_use("clam")
    app = VariantView(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
