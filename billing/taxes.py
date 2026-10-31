"""
billing/taxes.py - Regional Tax Jurisdictions & Rates (Member 3 Deliverable)
Subscription Management System

Provides backend Data Access Object (TaxManager), calculation engine,
and modern Tkinter GUI (TaxView) for managing VAT, GST, and regional sales taxes.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class TaxManager:
    """Backend Data Access Object for Regional Taxes."""

    @staticmethod
    def get_all_taxes(search_term=None, status=None):
        """Fetch all tax jurisdictions with optional search and filter."""
        query = "SELECT * FROM taxes WHERE 1=1"
        params = []

        if search_term:
            query += " AND (tax_code LIKE %s OR region_name LIKE %s OR tax_name LIKE %s)"
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw])

        if status == "Active":
            query += " AND is_active = 1"
        elif status == "Inactive":
            query += " AND is_active = 0"

        query += " ORDER BY rate ASC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_tax_by_id(tax_id):
        """Fetch a single tax rule by primary key."""
        return db.fetch_one("SELECT * FROM taxes WHERE id = %s", (tax_id,))

    @staticmethod
    def get_tax_by_code(tax_code):
        """Fetch a single tax rule by unique tax code."""
        return db.fetch_one("SELECT * FROM taxes WHERE tax_code = %s", (tax_code.strip().upper(),))

    @staticmethod
    def add_tax(tax_code, region_name, tax_name, rate, is_active=1):
        """Create a new tax rule with validation."""
        code = tax_code.strip().upper()
        if not code or not region_name.strip() or not tax_name.strip():
            return False, "Tax Code, Region Name, and Tax Name are required."

        try:
            rate_val = float(rate)
            if rate_val < 0.0 or rate_val > 100.0:
                return False, "Tax rate must be between 0.0% and 100.0%."
        except ValueError:
            return False, "Rate must be a valid numeric percentage."

        existing = TaxManager.get_tax_by_code(code)
        if existing:
            return False, f"Tax code '{code}' already exists."

        db.execute_query(
            "INSERT INTO taxes (tax_code, region_name, tax_name, rate, is_active) VALUES (%s, %s, %s, %s, %s)",
            (code, region_name.strip(), tax_name.strip(), rate_val, int(is_active))
        )
        return True, f"Tax rule '{code}' created successfully."

    @staticmethod
    def update_tax(tax_id, tax_code, region_name, tax_name, rate, is_active=1):
        """Update an existing tax rule."""
        code = tax_code.strip().upper()
        if not code or not region_name.strip() or not tax_name.strip():
            return False, "Tax Code, Region Name, and Tax Name are required."

        try:
            rate_val = float(rate)
            if rate_val < 0.0 or rate_val > 100.0:
                return False, "Tax rate must be between 0.0% and 100.0%."
        except ValueError:
            return False, "Rate must be a valid numeric percentage."

        existing = TaxManager.get_tax_by_code(code)
        if existing and existing['id'] != int(tax_id):
            return False, f"Tax code '{code}' is already used by another rule."

        db.execute_query(
            "UPDATE taxes SET tax_code = %s, region_name = %s, tax_name = %s, rate = %s, is_active = %s WHERE id = %s",
            (code, region_name.strip(), tax_name.strip(), rate_val, int(is_active), int(tax_id))
        )
        return True, f"Tax rule #{tax_id} updated successfully."

    @staticmethod
    def delete_tax(tax_id):
        """Delete a tax rule if not tied to existing invoices."""
        try:
            # Check if referenced in invoices
            invoices = db.fetch_all("SELECT COUNT(*) as count FROM invoices WHERE tax_id = %s", (tax_id,))
            if invoices and invoices[0]['count'] > 0:
                # Deactivate instead of hard delete to preserve financial audit trail
                db.execute_query("UPDATE taxes SET is_active = 0 WHERE id = %s", (tax_id,))
                return True, f"Tax rule #{tax_id} is referenced in {invoices[0]['count']} invoices. Deactivated safely."

            db.execute_query("DELETE FROM taxes WHERE id = %s", (tax_id,))
            return True, f"Tax rule #{tax_id} permanently deleted."
        except Exception as e:
            return False, f"Error deleting tax rule: {str(e)}"

    @staticmethod
    def calculate_tax(subtotal: float, tax_id: int):
        """
        Computes tax amount for a given taxable subtotal.
        Returns: (tax_amount: float, tax_name: str, rate: float)
        """
        try:
            if not tax_id or subtotal <= 0:
                return 0.00, "None / Exempt", 0.00

            rule = TaxManager.get_tax_by_id(tax_id)
            if not rule or not rule.get('is_active', 1):
                return 0.00, "Exempt", 0.00

            rate = float(rule['rate'])
            tax_amount = round(subtotal * (rate / 100.0), 2)
            return tax_amount, rule['tax_name'], rate
        except Exception as ex:
            print("[TaxManager] Calculation error:", ex)
            return 0.00, "Error", 0.00


def calculate_tax(subtotal: float, tax_id: int):
    """Module-level convenience wrapper for cross-module integration."""
    return TaxManager.calculate_tax(subtotal, tax_id)


class TaxView(ttk.Frame):
    """Modern Tkinter GUI for Tax Management."""

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        # 1. Action Header
        header = tk.Frame(self, bg="#0F172A", padx=20, pady=16)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg="#0F172A")
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="🏛️ Regional Tax Jurisdictions & Rates",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Member 3 Deliverable — Manage VAT, GST, and regional checkout tax policies",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A"
        ).pack(anchor="w")

        btn_box = tk.Frame(header, bg="#0F172A")
        btn_box.pack(side=tk.RIGHT)

        add_btn = tk.Button(
            btn_box,
            text="+ Add Tax Jurisdiction",
            font=("Segoe UI", 9, "bold"),
            bg="#4F46E5",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._open_add_dialog
        )
        add_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = tk.Button(
            btn_box,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#F8FAFC",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.load_data
        )
        refresh_btn.pack(side=tk.LEFT)

        # 2. Filter Bar
        filter_frame = tk.Frame(self, bg="#FFFFFF", padx=20, pady=12, bd=1, relief="solid")
        filter_frame.pack(fill=tk.X)

        tk.Label(filter_frame, text="Search Jurisdiction / Code:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry = ttk.Entry(filter_frame, width=28, font=("Segoe UI", 9))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 20))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data())

        tk.Label(filter_frame, text="Status:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.status_combo = ttk.Combobox(filter_frame, values=["All Statuses", "Active", "Inactive"], state="readonly", width=14, font=("Segoe UI", 9))
        self.status_combo.set("All Statuses")
        self.status_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        clear_btn = tk.Button(
            filter_frame,
            text="Clear Filters",
            font=("Segoe UI", 8),
            bg="#F1F5F9",
            fg="#475569",
            relief="groove",
            cursor="hand2",
            command=self._clear_filters
        )
        clear_btn.pack(side=tk.LEFT)

        # 3. Main Data Table
        table_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=15)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "tax_code", "region_name", "tax_name", "rate", "status", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("tax_code", text="Tax Code")
        self.tree.heading("region_name", text="Jurisdiction / Country")
        self.tree.heading("tax_name", text="Tax Description")
        self.tree.heading("rate", text="Rate (%)")
        self.tree.heading("status", text="Active Status")
        self.tree.heading("created_at", text="Created On")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("tax_code", width=110, anchor="center")
        self.tree.column("region_name", width=220, anchor="w")
        self.tree.column("tax_name", width=180, anchor="w")
        self.tree.column("rate", width=90, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("created_at", width=130, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._open_edit_dialog())

        # 4. Table Operations Toolbar
        ops_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=8)
        ops_frame.pack(fill=tk.X)

        edit_btn = tk.Button(ops_frame, text="✏️ Edit Selected", font=("Segoe UI", 9), bg="#E2E8F0", fg="#1E293B", relief="flat", cursor="hand2", padx=10, pady=4, command=self._open_edit_dialog)
        edit_btn.pack(side=tk.LEFT, padx=(0, 6))

        del_btn = tk.Button(ops_frame, text="🗑️ Delete / Deactivate", font=("Segoe UI", 9), bg="#FEE2E2", fg="#991B1B", relief="flat", cursor="hand2", padx=10, pady=4, command=self._delete_selected)
        del_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.count_lbl = tk.Label(ops_frame, text="Total Rules: 0", font=("Segoe UI", 9, "italic"), bg="#F8FAFC", fg="#64748B")
        self.count_lbl.pack(side=tk.RIGHT)

        # 5. Interactive Live Tax Calculator Widget
        calc_card = tk.LabelFrame(self, text="🧮 Interactive Checkout Tax Calculator", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", padx=15, pady=10)
        calc_card.pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(calc_card, text="Subtotal ($):", font=("Segoe UI", 9), bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
        self.calc_subtotal = ttk.Entry(calc_card, width=12, font=("Segoe UI", 9))
        self.calc_subtotal.insert(0, "100.00")
        self.calc_subtotal.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(calc_card, text="Select Rule:", font=("Segoe UI", 9), bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
        self.calc_rule_combo = ttk.Combobox(calc_card, state="readonly", width=25, font=("Segoe UI", 9))
        self.calc_rule_combo.pack(side=tk.LEFT, padx=(0, 15))

        calc_btn = tk.Button(calc_card, text="Calculate Tax", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="#FFFFFF", relief="flat", cursor="hand2", padx=10, pady=3, command=self._run_calculator)
        calc_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.calc_result_lbl = tk.Label(calc_card, text="Result: Enter amount to compute", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#2563EB")
        self.calc_result_lbl.pack(side=tk.LEFT)

    def _clear_filters(self):
        self.search_entry.delete(0, tk.END)
        self.status_combo.set("All Statuses")
        self.load_data()

    def load_data(self):
        """Refresh treeview with filtered tax rules."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        search = self.search_entry.get().strip()
        status = self.status_combo.get()

        taxes = TaxManager.get_all_taxes(search, status)
        combo_values = []
        self.rule_map = {}

        for t in taxes:
            is_act = "Active" if t.get('is_active', 1) else "Inactive"
            created = str(t.get('created_at', ''))[:10]
            rate_fmt = f"{float(t['rate']):.2f}%"
            self.tree.insert("", tk.END, values=(t['id'], t['tax_code'], t['region_name'], t['tax_name'], rate_fmt, is_act, created))
            label = f"{t['tax_code']} - {t['region_name']} ({rate_fmt})"
            combo_values.append(label)
            self.rule_map[label] = t['id']

        self.count_lbl.config(text=f"Total Jurisdictions: {len(taxes)}")
        self.calc_rule_combo['values'] = combo_values
        if combo_values and not self.calc_rule_combo.get():
            self.calc_rule_combo.current(0)

    def _run_calculator(self):
        """Live tester execution."""
        try:
            amt = float(self.calc_subtotal.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid numeric subtotal.")
            return

        selected_label = self.calc_rule_combo.get()
        if not selected_label or selected_label not in self.rule_map:
            messagebox.showwarning("Select Rule", "Please pick an active tax rule.")
            return

        tax_id = self.rule_map[selected_label]
        tax_amt, name, rate = TaxManager.calculate_tax(amt, tax_id)
        total = round(amt + tax_amt, 2)
        self.calc_result_lbl.config(
            text=f"Tax: ${tax_amt:.2f} ({rate:.1f}%) | Total Payable: ${total:.2f}"
        )

    def _open_add_dialog(self):
        """Open popup for adding a new tax jurisdiction."""
        self._show_form_modal("Add Tax Jurisdiction", None)

    def _open_edit_dialog(self):
        """Open popup for modifying selected tax jurisdiction."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a tax rule from the table to edit.")
            return
        item = self.tree.item(selected[0])['values']
        tax_id = item[0]
        tax = TaxManager.get_tax_by_id(tax_id)
        if tax:
            self._show_form_modal("Edit Tax Jurisdiction", tax)

    def _show_form_modal(self, title, tax_data):
        modal = tk.Toplevel(self)
        modal.title(title)
        modal.geometry("450x420")
        modal.resizable(False, False)
        modal.grab_set()

        frame = tk.Frame(modal, bg="#FFFFFF", padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=title, font=("Segoe UI", 12, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor="w", pady=(0, 15))

        # Fields
        tk.Label(frame, text="Tax Code (e.g. TAX-US-CA):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_code = ttk.Entry(frame, width=35, font=("Segoe UI", 9))
        ent_code.pack(fill=tk.X, pady=(2, 10))

        tk.Label(frame, text="Jurisdiction / Region Name:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_region = ttk.Entry(frame, width=35, font=("Segoe UI", 9))
        ent_region.pack(fill=tk.X, pady=(2, 10))

        tk.Label(frame, text="Tax Name (e.g. State Sales Tax, VAT):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_name = ttk.Entry(frame, width=35, font=("Segoe UI", 9))
        ent_name.pack(fill=tk.X, pady=(2, 10))

        tk.Label(frame, text="Percentage Rate (%):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_rate = ttk.Entry(frame, width=35, font=("Segoe UI", 9))
        ent_rate.pack(fill=tk.X, pady=(2, 10))

        var_active = tk.IntVar(value=1)
        chk_active = ttk.Checkbutton(frame, text="Rule is active & enabled at checkout", variable=var_active)
        chk_active.pack(anchor="w", pady=(0, 20))

        if tax_data:
            ent_code.insert(0, tax_data.get('tax_code', ''))
            ent_region.insert(0, tax_data.get('region_name', ''))
            ent_name.insert(0, tax_data.get('tax_name', ''))
            ent_rate.insert(0, str(tax_data.get('rate', '0.00')))
            var_active.set(int(tax_data.get('is_active', 1)))

        def on_save():
            code = ent_code.get().strip()
            region = ent_region.get().strip()
            tname = ent_name.get().strip()
            rate_str = ent_rate.get().strip()
            active = var_active.get()

            if tax_data:
                ok, msg = TaxManager.update_tax(tax_data['id'], code, region, tname, rate_str, active)
            else:
                ok, msg = TaxManager.add_tax(code, region, tname, rate_str, active)

            if ok:
                messagebox.showinfo("Success", msg)
                modal.destroy()
                self.load_data()
            else:
                messagebox.showerror("Validation Error", msg)

        btn_box = tk.Frame(frame, bg="#FFFFFF")
        btn_box.pack(fill=tk.X, pady=(10, 0))

        save_btn = tk.Button(btn_box, text="Save Jurisdiction", font=("Segoe UI", 9, "bold"), bg="#4F46E5", fg="#FFFFFF", relief="flat", cursor="hand2", padx=12, pady=6, command=on_save)
        save_btn.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_btn = tk.Button(btn_box, text="Cancel", font=("Segoe UI", 9), bg="#E2E8F0", fg="#334155", relief="flat", cursor="hand2", padx=12, pady=6, command=modal.destroy)
        cancel_btn.pack(side=tk.RIGHT)

    def _delete_selected(self):
        """Handle deletion or deactivation of selected tax rule."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a tax rule to delete.")
            return

        item = self.tree.item(selected[0])['values']
        tax_id = item[0]
        code = item[1]

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to remove tax rule '{code}' (ID #{tax_id})?"):
            return

        ok, msg = TaxManager.delete_tax(tax_id)
        if ok:
            messagebox.showinfo("Success", msg)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Tax Jurisdictions Manager — Member 3")
    root.geometry("980x620")
    init_db()
    view = TaxView(root)
    view.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
