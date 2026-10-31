"""
subscriptions/products.py - Product Management Module (Member 2 Deliverable)
Subscription Management System

Provides complete backend CRUD operations and a modern Tkinter GUI for managing products.
Can be integrated as a ttk.Frame or run standalone.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure database module is accessible regardless of execution path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class ProductManager:
    """Backend Data Access Object for Products."""

    @staticmethod
    def get_all_products(search_term=None, category=None, status=None):
        """Fetch products with optional keyword and filter conditions."""
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if search_term:
            query += " AND (product_code LIKE %s OR name LIKE %s OR description LIKE %s)"
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw])

        if category and category != "All Categories":
            query += " AND category = %s"
            params.append(category)

        if status and status != "All Statuses":
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY id DESC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_product_by_id(product_id):
        """Fetch a single product by its primary key ID."""
        return db.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))

    @staticmethod
    def get_product_by_code(product_code):
        """Fetch a product by unique product code."""
        return db.fetch_one("SELECT * FROM products WHERE product_code = %s", (product_code,))

    @staticmethod
    def add_product(product_code, name, category, description, status='Active'):
        """Create a new product. Returns (success: bool, message: str)."""
        product_code = product_code.strip().upper()
        name = name.strip()
        category = category.strip()
        description = description.strip()

        if not product_code or not name or not category:
            return False, "Product Code, Name, and Category are required."

        existing = ProductManager.get_product_by_code(product_code)
        if existing:
            return False, f"Product code '{product_code}' already exists."

        try:
            db.execute_query(
                "INSERT INTO products (product_code, name, category, description, status) VALUES (%s, %s, %s, %s, %s)",
                (product_code, name, category, description, status)
            )
            return True, "Product added successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def update_product(product_id, product_code, name, category, description, status):
        """Update an existing product. Returns (success: bool, message: str)."""
        product_code = product_code.strip().upper()
        name = name.strip()
        category = category.strip()
        description = description.strip()

        if not product_code or not name or not category:
            return False, "Product Code, Name, and Category are required."

        existing = ProductManager.get_product_by_code(product_code)
        if existing and existing['id'] != int(product_id):
            return False, f"Product code '{product_code}' is already used by another product."

        try:
            db.execute_query(
                """
                UPDATE products
                SET product_code = %s, name = %s, category = %s, description = %s, status = %s
                WHERE id = %s
                """,
                (product_code, name, category, description, status, product_id)
            )
            return True, "Product updated successfully."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete_product(product_id):
        """Delete a product after checking for foreign key dependencies."""
        try:
            # Check for linked plans
            plans = db.fetch_all("SELECT COUNT(*) as cnt FROM plans WHERE product_id = %s", (product_id,))
            plan_count = plans[0]['cnt'] if plans else 0

            # Check for linked subscriptions
            subs = db.fetch_all("SELECT COUNT(*) as cnt FROM subscriptions WHERE product_id = %s", (product_id,))
            sub_count = subs[0]['cnt'] if subs else 0

            if sub_count > 0:
                return False, f"Cannot delete: Product is referenced by {sub_count} active/past customer subscriptions. Consider archiving it instead."

            db.execute_query("DELETE FROM products WHERE id = %s", (product_id,))
            return True, f"Product deleted successfully (and {plan_count} linked plans removed)."
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    @staticmethod
    def get_categories():
        """Retrieve distinct product categories."""
        rows = db.fetch_all("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category ASC")
        return [r['category'] for r in rows]

    @staticmethod
    def get_stats():
        """Retrieve summary statistics."""
        total = db.fetch_one("SELECT COUNT(*) as cnt FROM products")['cnt']
        active = db.fetch_one("SELECT COUNT(*) as cnt FROM products WHERE status = 'Active'")['cnt']
        inactive = total - active
        return {'total': total, 'active': active, 'inactive': inactive}


class ProductFormDialog(tk.Toplevel):
    """Modal dialog for creating and editing products."""

    def __init__(self, parent, product_id=None, on_success=None):
        super().__init__(parent)
        self.product_id = product_id
        self.on_success = on_success
        self.is_edit = product_id is not None

        self.title("Edit Product" if self.is_edit else "Add New Product")
        self.geometry("520x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        if self.is_edit:
            self._load_data()

    def _build_ui(self):
        self.configure(bg="#F8F9FA")
        container = ttk.Frame(self, padding="24")
        container.pack(fill=tk.BOTH, expand=True)

        header_lbl = ttk.Label(
            container,
            text="✏️ Edit Product Details" if self.is_edit else "📦 Register New Product",
            font=("Segoe UI", 14, "bold")
        )
        header_lbl.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 18))

        # Product Code
        ttk.Label(container, text="Product Code *:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(container, textvariable=self.code_var, width=32)
        self.code_entry.grid(row=1, column=1, sticky=tk.W, pady=6)
        ttk.Label(container, text="(e.g. PRD-CLOUD, PRD-STREAM)", font=("Segoe UI", 8), foreground="#6C757D").grid(row=2, column=1, sticky=tk.W)

        # Name
        ttk.Label(container, text="Product Name *:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=6)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(container, textvariable=self.name_var, width=32)
        self.name_entry.grid(row=3, column=1, sticky=tk.W, pady=6)

        # Category
        ttk.Label(container, text="Category *:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky=tk.W, pady=6)
        self.cat_var = tk.StringVar()
        existing_cats = ProductManager.get_categories()
        default_cats = list(set(["Cloud Storage", "Digital Media", "SaaS Business", "Cybersecurity", "Productivity"] + existing_cats))
        self.cat_combo = ttk.Combobox(container, textvariable=self.cat_var, values=default_cats, width=30)
        self.cat_combo.grid(row=4, column=1, sticky=tk.W, pady=6)

        # Status
        ttk.Label(container, text="Status:", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky=tk.W, pady=6)
        self.status_var = tk.StringVar(value="Active")
        self.status_combo = ttk.Combobox(container, textvariable=self.status_var, values=["Active", "Inactive", "Archived"], state="readonly", width=30)
        self.status_combo.grid(row=5, column=1, sticky=tk.W, pady=6)

        # Description
        ttk.Label(container, text="Description:", font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky=tk.NW, pady=6)
        self.desc_text = tk.Text(container, width=32, height=4, font=("Segoe UI", 9))
        self.desc_text.grid(row=6, column=1, sticky=tk.W, pady=6)

        # Action Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=7, column=0, columnspan=2, sticky=tk.E, pady=(20, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=6)

        save_btn = ttk.Button(btn_frame, text="Save Product", command=self._save)
        save_btn.pack(side=tk.RIGHT, padx=6)

    def _load_data(self):
        prod = ProductManager.get_product_by_id(self.product_id)
        if prod:
            self.code_var.set(prod['product_code'])
            self.name_var.set(prod['name'])
            self.cat_var.set(prod['category'])
            self.status_var.set(prod['status'])
            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert("1.0", prod['description'] or "")

    def _save(self):
        code = self.code_var.get()
        name = self.name_var.get()
        cat = self.cat_var.get()
        status = self.status_var.get()
        desc = self.desc_text.get("1.0", tk.END).strip()

        if self.is_edit:
            success, msg = ProductManager.update_product(self.product_id, code, name, cat, desc, status)
        else:
            success, msg = ProductManager.add_product(code, name, cat, desc, status)

        if success:
            messagebox.showinfo("Success", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Validation Error", msg, parent=self)


class ProductView(ttk.Frame):
    """Main Product Management View Component for Member 2."""

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        # 1. Header & Summary Banner
        header_frame = ttk.Frame(self, padding="14")
        header_frame.pack(fill=tk.X)

        title_lbl = ttk.Label(
            header_frame,
            text="📦 Product Catalog Management",
            font=("Segoe UI", 16, "bold")
        )
        title_lbl.pack(side=tk.LEFT)

        self.stats_lbl = ttk.Label(
            header_frame,
            text="Total: 0 | Active: 0 | Inactive: 0",
            font=("Segoe UI", 10),
            foreground="#495057"
        )
        self.stats_lbl.pack(side=tk.RIGHT, pady=4)

        # 2. Filter & Search Toolbar
        filter_frame = ttk.LabelFrame(self, text=" Search & Filters ", padding="10")
        filter_frame.pack(fill=tk.X, padx=14, pady=6)

        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=22)
        self.search_entry.pack(side=tk.LEFT, padx=6)
        self.search_entry.bind("<Return>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=(12, 4))
        self.cat_filter_var = tk.StringVar(value="All Categories")
        self.cat_filter = ttk.Combobox(filter_frame, textvariable=self.cat_filter_var, state="readonly", width=18)
        self.cat_filter.pack(side=tk.LEFT, padx=6)
        self.cat_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(12, 4))
        self.status_filter_var = tk.StringVar(value="All Statuses")
        self.status_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.status_filter_var,
            values=["All Statuses", "Active", "Inactive", "Archived"],
            state="readonly",
            width=14
        )
        self.status_filter.pack(side=tk.LEFT, padx=6)
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        search_btn = ttk.Button(filter_frame, text="🔍 Search", command=self.refresh)
        search_btn.pack(side=tk.LEFT, padx=8)

        reset_btn = ttk.Button(filter_frame, text="Reset", command=self._reset_filters)
        reset_btn.pack(side=tk.LEFT, padx=4)

        # Action Buttons on Right
        add_btn = ttk.Button(filter_frame, text="➕ Add Product", command=self._open_add_dialog)
        add_btn.pack(side=tk.RIGHT, padx=4)

        # 3. Product Table (Treeview)
        table_frame = ttk.Frame(self, padding="14")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "code", "name", "category", "description", "status", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Product Code")
        self.tree.heading("name", text="Product Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("description", text="Description")
        self.tree.heading("status", text="Status")
        self.tree.heading("created_at", text="Created On")

        self.tree.column("id", width=45, anchor=tk.CENTER)
        self.tree.column("code", width=110, anchor=tk.W)
        self.tree.column("name", width=180, anchor=tk.W)
        self.tree.column("category", width=130, anchor=tk.W)
        self.tree.column("description", width=280, anchor=tk.W)
        self.tree.column("status", width=85, anchor=tk.CENTER)
        self.tree.column("created_at", width=130, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._open_edit_dialog())

        # 4. Bottom Action Bar
        bottom_bar = ttk.Frame(self, padding="12")
        bottom_bar.pack(fill=tk.X)

        edit_btn = ttk.Button(bottom_bar, text="✏️ Edit Selected", command=self._open_edit_dialog)
        edit_btn.pack(side=tk.LEFT, padx=6)

        del_btn = ttk.Button(bottom_bar, text="🗑️ Delete Product", command=self._delete_selected)
        del_btn.pack(side=tk.LEFT, padx=6)

        view_plans_btn = ttk.Button(bottom_bar, text="📋 View Associated Plans", command=self._view_linked_plans)
        view_plans_btn.pack(side=tk.LEFT, padx=6)

        refresh_btn = ttk.Button(bottom_bar, text="🔄 Refresh", command=self.refresh)
        refresh_btn.pack(side=tk.RIGHT, padx=6)

    def _reset_filters(self):
        self.search_var.set("")
        self.cat_filter_var.set("All Categories")
        self.status_filter_var.set("All Statuses")
        self.refresh()

    def refresh(self):
        """Reload products into Treeview and refresh category dropdowns."""
        # Update categories filter
        cats = ["All Categories"] + ProductManager.get_categories()
        self.cat_filter['values'] = cats

        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        products = ProductManager.get_all_products(
            search_term=self.search_var.get(),
            category=self.cat_filter_var.get(),
            status=self.status_filter_var.get()
        )

        for p in products:
            created = str(p['created_at'])[:10] if p.get('created_at') else ""
            self.tree.insert("", tk.END, values=(
                p['id'],
                p['product_code'],
                p['name'],
                p['category'],
                p['description'] or "",
                p['status'],
                created
            ))

        # Update stats
        stats = ProductManager.get_stats()
        self.stats_lbl.config(
            text=f"Total: {stats['total']}  |  Active: {stats['active']}  |  Inactive: {stats['inactive']}"
        )

    def _get_selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a product from the list first.")
            return None
        return self.tree.item(selected[0])['values'][0]

    def _open_add_dialog(self):
        ProductFormDialog(self, on_success=self.refresh)

    def _open_edit_dialog(self):
        prod_id = self._get_selected_id()
        if prod_id:
            ProductFormDialog(self, product_id=prod_id, on_success=self.refresh)

    def _delete_selected(self):
        prod_id = self._get_selected_id()
        if not prod_id:
            return

        prod = ProductManager.get_product_by_id(prod_id)
        if not prod:
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete product '{prod['name']}' ({prod['product_code']})?\n"
            f"This will also delete its linked plans if no customer subscriptions reference it.",
            icon='warning'
        )
        if confirm:
            success, msg = ProductManager.delete_product(prod_id)
            if success:
                messagebox.showinfo("Success", msg)
                self.refresh()
            else:
                messagebox.showerror("Error", msg)

    def _view_linked_plans(self):
        prod_id = self._get_selected_id()
        if not prod_id:
            return

        prod = ProductManager.get_product_by_id(prod_id)
        plans = db.fetch_all("SELECT plan_code, name, billing_cycle, price, currency, status FROM plans WHERE product_id = %s", (prod_id,))

        info_win = tk.Toplevel(self)
        info_win.title(f"Plans for {prod['name']}")
        info_win.geometry("540x320")
        info_win.transient(self)

        lbl = ttk.Label(info_win, text=f"Plans linked to: {prod['name']} ({prod['product_code']})", font=("Segoe UI", 11, "bold"))
        lbl.pack(pady=10, padx=12, anchor=tk.W)

        if not plans:
            ttk.Label(info_win, text="No plans configured for this product yet.", font=("Segoe UI", 10, "italic")).pack(pady=30)
            return

        cols = ("code", "name", "cycle", "price", "status")
        tree = ttk.Treeview(info_win, columns=cols, show="headings", height=8)
        tree.heading("code", text="Plan Code")
        tree.heading("name", text="Plan Name")
        tree.heading("cycle", text="Cycle")
        tree.heading("price", text="Price")
        tree.heading("status", text="Status")

        tree.column("code", width=110)
        tree.column("name", width=160)
        tree.column("cycle", width=80, anchor=tk.CENTER)
        tree.column("price", width=70, anchor=tk.E)
        tree.column("status", width=70, anchor=tk.CENTER)

        for pl in plans:
            tree.insert("", tk.END, values=(
                pl['plan_code'],
                pl['name'],
                pl['billing_cycle'],
                f"{pl['price']:.2f} {pl['currency']}",
                pl['status']
            ))
        tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("BrightLoop - Product Catalog (Member 2)")
    root.geometry("900x560")
    style = ttk.Style(root)
    style.theme_use("clam")
    app = ProductView(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
