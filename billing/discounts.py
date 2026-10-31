"""
billing/discounts.py - Promotional Vouchers & Coupon Engine (Member 3 Deliverable)
Subscription Management System

Provides backend Data Access Object (DiscountManager), coupon validation engine,
and modern Tkinter GUI (DiscountView) for managing percentage and flat discount vouchers.
"""

import sys
import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class DiscountManager:
    """Backend Data Access Object and Calculation Engine for Promotional Vouchers."""

    @staticmethod
    def get_all_discounts(search_term=None, discount_type=None, status=None):
        """Fetch all coupons with optional search and filter criteria."""
        query = "SELECT * FROM discounts WHERE 1=1"
        params = []

        if search_term:
            query += " AND (code LIKE %s OR description LIKE %s)"
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw])

        if discount_type and discount_type != "All Types":
            query += " AND discount_type = %s"
            params.append(discount_type.lower())

        if status == "Active":
            query += " AND is_active = 1"
        elif status == "Inactive":
            query += " AND is_active = 0"

        query += " ORDER BY id DESC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_discount_by_id(discount_id):
        """Fetch coupon by primary key ID."""
        return db.fetch_one("SELECT * FROM discounts WHERE id = %s", (discount_id,))

    @staticmethod
    def get_discount_by_code(code):
        """Fetch coupon by unique promo code (case-insensitive)."""
        if not code:
            return None
        return db.fetch_one("SELECT * FROM discounts WHERE code = %s", (code.strip().upper(),))

    @staticmethod
    def add_discount(code, description, discount_type, value, min_order_amount=0.0,
                     valid_from=None, valid_until=None, usage_limit=100, is_active=1):
        """Create a new promotional voucher."""
        code = code.strip().upper()
        if not code:
            return False, "Coupon code is required."

        if discount_type not in ('percentage', 'fixed'):
            return False, "Discount type must be 'percentage' or 'fixed'."

        try:
            val = float(value)
            if val <= 0:
                return False, "Discount value must be greater than 0."
            if discount_type == 'percentage' and val > 100.0:
                return False, "Percentage discount cannot exceed 100%."
        except ValueError:
            return False, "Discount value must be a valid number."

        try:
            min_order = float(min_order_amount) if min_order_amount else 0.0
        except ValueError:
            return False, "Minimum order amount must be numeric."

        existing = DiscountManager.get_discount_by_code(code)
        if existing:
            return False, f"Coupon code '{code}' already exists."

        db.execute_query(
            """
            INSERT INTO discounts
            (code, description, discount_type, value, min_order_amount, valid_from, valid_until, usage_limit, times_used, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
            """,
            (code, description.strip() if description else "", discount_type, val, min_order,
             valid_from or None, valid_until or None, int(usage_limit), int(is_active))
        )
        return True, f"Coupon '{code}' created successfully."

    @staticmethod
    def update_discount(discount_id, code, description, discount_type, value, min_order_amount=0.0,
                        valid_from=None, valid_until=None, usage_limit=100, is_active=1):
        """Update an existing coupon."""
        code = code.strip().upper()
        if not code:
            return False, "Coupon code is required."

        try:
            val = float(value)
            if val <= 0:
                return False, "Discount value must be greater than 0."
            if discount_type == 'percentage' and val > 100.0:
                return False, "Percentage discount cannot exceed 100%."
        except ValueError:
            return False, "Discount value must be a valid number."

        existing = DiscountManager.get_discount_by_code(code)
        if existing and existing['id'] != int(discount_id):
            return False, f"Coupon code '{code}' already exists."

        db.execute_query(
            """
            UPDATE discounts
            SET code = %s, description = %s, discount_type = %s, value = %s, min_order_amount = %s,
                valid_from = %s, valid_until = %s, usage_limit = %s, is_active = %s
            WHERE id = %s
            """,
            (code, description.strip() if description else "", discount_type, val, float(min_order_amount or 0.0),
             valid_from or None, valid_until or None, int(usage_limit), int(is_active), int(discount_id))
        )
        return True, f"Coupon #{discount_id} updated successfully."

    @staticmethod
    def delete_discount(discount_id):
        """Safely delete or deactivate a coupon."""
        try:
            # Check if referenced by invoices
            inv_count = db.fetch_all("SELECT COUNT(*) as count FROM invoices WHERE discount_id = %s", (discount_id,))
            if inv_count and inv_count[0]['count'] > 0:
                db.execute_query("UPDATE discounts SET is_active = 0 WHERE id = %s", (discount_id,))
                return True, f"Coupon #{discount_id} is referenced in {inv_count[0]['count']} invoices. Safely deactivated."

            db.execute_query("DELETE FROM discounts WHERE id = %s", (discount_id,))
            return True, f"Coupon #{discount_id} deleted successfully."
        except Exception as e:
            return False, f"Error deleting coupon: {str(e)}"

    @staticmethod
    def validate_and_apply_discount(code: str, subtotal: float):
        """
        Validates coupon conditions against purchase amount.
        Returns: (is_valid: bool, discount_amount: float, message: str)
        """
        if not code or not code.strip():
            return False, 0.00, "No coupon code provided."

        clean_code = code.strip().upper()
        row = DiscountManager.get_discount_by_code(clean_code)

        if not row:
            return False, 0.00, f"Promo code '{clean_code}' is invalid."

        if not row.get('is_active', 1):
            return False, 0.00, f"Promo code '{clean_code}' is currently inactive."

        # Check Usage Limit
        usage_limit = row.get('usage_limit', 100) or 100
        times_used = row.get('times_used', 0) or 0
        if times_used >= usage_limit:
            return False, 0.00, f"Promo code '{clean_code}' has reached its maximum redemptions ({usage_limit})."

        # Check Date Range
        today = datetime.date.today()
        if row.get('valid_from'):
            try:
                vf = datetime.datetime.strptime(str(row['valid_from'])[:10], "%Y-%m-%d").date()
                if today < vf:
                    return False, 0.00, f"Promo code '{clean_code}' is not valid until {vf}."
            except Exception:
                pass

        if row.get('valid_until'):
            try:
                vu = datetime.datetime.strptime(str(row['valid_until'])[:10], "%Y-%m-%d").date()
                if today > vu:
                    return False, 0.00, f"Promo code '{clean_code}' expired on {vu}."
            except Exception:
                pass

        # Check Minimum Order
        min_order = float(row.get('min_order_amount', 0.0) or 0.0)
        if subtotal < min_order:
            return False, 0.00, f"Minimum order of ${min_order:.2f} required for coupon '{clean_code}'."

        # Compute Discount
        val = float(row['value'])
        disc_type = row.get('discount_type', 'percentage')

        if disc_type == 'percentage':
            discount_amount = round(subtotal * (val / 100.0), 2)
            msg = f"Applied {val:.1f}% discount (-${discount_amount:.2f})"
        else:
            discount_amount = round(min(subtotal, val), 2)
            msg = f"Applied flat ${val:.2f} discount (-${discount_amount:.2f})"

        return True, discount_amount, msg

    @staticmethod
    def increment_usage(discount_id):
        """Record a successful redemption."""
        db.execute_query("UPDATE discounts SET times_used = times_used + 1 WHERE id = %s", (discount_id,))


def validate_and_apply_discount(code: str, subtotal: float):
    """Module-level convenience wrapper for cross-module integration."""
    return DiscountManager.validate_and_apply_discount(code, subtotal)


class DiscountView(ttk.Frame):
    """Modern Tkinter GUI for Promo Codes and Coupon Management."""

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
            text="🎟️ Promotional Discounts & Vouchers",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Member 3 Deliverable — Manage coupon campaigns, discount rules, and redemption limits",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A"
        ).pack(anchor="w")

        btn_box = tk.Frame(header, bg="#0F172A")
        btn_box.pack(side=tk.RIGHT)

        add_btn = tk.Button(
            btn_box,
            text="+ Create Promo Code",
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

        tk.Label(filter_frame, text="Search Code / Name:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry = ttk.Entry(filter_frame, width=24, font=("Segoe UI", 9))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data())

        tk.Label(filter_frame, text="Type:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.type_combo = ttk.Combobox(filter_frame, values=["All Types", "percentage", "fixed"], state="readonly", width=12, font=("Segoe UI", 9))
        self.type_combo.set("All Types")
        self.type_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text="Status:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.status_combo = ttk.Combobox(filter_frame, values=["All Statuses", "Active", "Inactive"], state="readonly", width=12, font=("Segoe UI", 9))
        self.status_combo.set("All Statuses")
        self.status_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        clear_btn = tk.Button(filter_frame, text="Clear", font=("Segoe UI", 8), bg="#F1F5F9", fg="#475569", relief="groove", cursor="hand2", command=self._clear_filters)
        clear_btn.pack(side=tk.LEFT)

        # 3. Data Table
        table_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=15)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "code", "description", "type", "value", "min_order", "validity", "usage", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Promo Code")
        self.tree.heading("description", text="Campaign Description")
        self.tree.heading("type", text="Type")
        self.tree.heading("value", text="Discount Value")
        self.tree.heading("min_order", text="Min Spend")
        self.tree.heading("validity", text="Expires On")
        self.tree.heading("usage", text="Redemptions")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=45, anchor="center")
        self.tree.column("code", width=120, anchor="center")
        self.tree.column("description", width=220, anchor="w")
        self.tree.column("type", width=90, anchor="center")
        self.tree.column("value", width=100, anchor="center")
        self.tree.column("min_order", width=85, anchor="center")
        self.tree.column("validity", width=105, anchor="center")
        self.tree.column("usage", width=95, anchor="center")
        self.tree.column("status", width=85, anchor="center")

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

        self.count_lbl = tk.Label(ops_frame, text="Total Coupons: 0", font=("Segoe UI", 9, "italic"), bg="#F8FAFC", fg="#64748B")
        self.count_lbl.pack(side=tk.RIGHT)

        # 5. Interactive Coupon Validator Widget
        tester_card = tk.LabelFrame(self, text="🧪 Live Coupon Validation Sandbox", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", padx=15, pady=10)
        tester_card.pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(tester_card, text="Promo Code:", font=("Segoe UI", 9), bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
        self.test_code = ttk.Entry(tester_card, width=15, font=("Segoe UI", 9))
        self.test_code.insert(0, "WELCOME20")
        self.test_code.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(tester_card, text="Cart Subtotal ($):", font=("Segoe UI", 9), bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
        self.test_subtotal = ttk.Entry(tester_card, width=10, font=("Segoe UI", 9))
        self.test_subtotal.insert(0, "79.99")
        self.test_subtotal.pack(side=tk.LEFT, padx=(0, 15))

        validate_btn = tk.Button(tester_card, text="Verify Code", font=("Segoe UI", 9, "bold"), bg="#2563EB", fg="#FFFFFF", relief="flat", cursor="hand2", padx=10, pady=3, command=self._run_tester)
        validate_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.test_result_lbl = tk.Label(tester_card, text="Status: Ready to test voucher", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#10B981")
        self.test_result_lbl.pack(side=tk.LEFT)

    def _clear_filters(self):
        self.search_entry.delete(0, tk.END)
        self.type_combo.set("All Types")
        self.status_combo.set("All Statuses")
        self.load_data()

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        search = self.search_entry.get().strip()
        dtype = self.type_combo.get()
        status = self.status_combo.get()

        discounts = DiscountManager.get_all_discounts(search, dtype, status)
        for d in discounts:
            val_fmt = f"{float(d['value']):.1f}%" if d['discount_type'] == 'percentage' else f"${float(d['value']):.2f}"
            min_fmt = f"${float(d['min_order_amount']):.2f}"
            validity = str(d.get('valid_until', 'No Expiry'))[:10] if d.get('valid_until') else "Unlimited"
            usage = f"{d.get('times_used', 0)} / {d.get('usage_limit', 100)}"
            is_act = "Active" if d.get('is_active', 1) else "Inactive"

            self.tree.insert("", tk.END, values=(
                d['id'], d['code'], d['description'] or "-", d['discount_type'].capitalize(),
                val_fmt, min_fmt, validity, usage, is_act
            ))

        self.count_lbl.config(text=f"Total Vouchers: {len(discounts)}")

    def _run_tester(self):
        code = self.test_code.get().strip()
        try:
            amt = float(self.test_subtotal.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please provide a numeric cart subtotal.")
            return

        valid, discount_amt, msg = DiscountManager.validate_and_apply_discount(code, amt)
        final_amt = round(max(0.0, amt - discount_amt), 2)
        if valid:
            self.test_result_lbl.config(
                text=f"✅ {msg} | New Total: ${final_amt:.2f}",
                fg="#059669"
            )
        else:
            self.test_result_lbl.config(
                text=f"❌ {msg}",
                fg="#DC2626"
            )

    def _open_add_dialog(self):
        self._show_form_modal("Create Promotional Voucher", None)

    def _open_edit_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Select a coupon to edit.")
            return
        disc_id = self.tree.item(selected[0])['values'][0]
        data = DiscountManager.get_discount_by_id(disc_id)
        if data:
            self._show_form_modal("Edit Promotional Voucher", data)

    def _show_form_modal(self, title, disc_data):
        modal = tk.Toplevel(self)
        modal.title(title)
        modal.geometry("480x520")
        modal.resizable(False, False)
        modal.grab_set()

        frame = tk.Frame(modal, bg="#FFFFFF", padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=title, font=("Segoe UI", 12, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor="w", pady=(0, 15))

        tk.Label(frame, text="Coupon Code (e.g. FLASH30):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_code = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_code.pack(fill=tk.X, pady=(2, 8))

        tk.Label(frame, text="Campaign Description:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_desc = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_desc.pack(fill=tk.X, pady=(2, 8))

        tk.Label(frame, text="Discount Type:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        cmb_type = ttk.Combobox(frame, values=["percentage", "fixed"], state="readonly", font=("Segoe UI", 9))
        cmb_type.set("percentage")
        cmb_type.pack(fill=tk.X, pady=(2, 8))

        tk.Label(frame, text="Discount Value (% or $ amount):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_val = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_val.pack(fill=tk.X, pady=(2, 8))

        tk.Label(frame, text="Minimum Order Spend ($):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_min = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_min.insert(0, "0.00")
        ent_min.pack(fill=tk.X, pady=(2, 8))

        tk.Label(frame, text="Valid Until (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_until = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_until.insert(0, "2026-12-31")
        ent_until.pack(fill=tk.X, pady=(2, 8))

        tk.Label(frame, text="Maximum Redemption Usage Limit:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_limit = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_limit.insert(0, "100")
        ent_limit.pack(fill=tk.X, pady=(2, 12))

        var_act = tk.IntVar(value=1)
        chk_act = ttk.Checkbutton(frame, text="Promo code is active and claimable", variable=var_act)
        chk_act.pack(anchor="w", pady=(0, 15))

        if disc_data:
            ent_code.insert(0, disc_data.get('code', ''))
            ent_desc.insert(0, disc_data.get('description', ''))
            cmb_type.set(disc_data.get('discount_type', 'percentage'))
            ent_val.insert(0, str(disc_data.get('value', '')))
            ent_min.delete(0, tk.END)
            ent_min.insert(0, str(disc_data.get('min_order_amount', '0.00')))
            ent_until.delete(0, tk.END)
            if disc_data.get('valid_until'):
                ent_until.insert(0, str(disc_data.get('valid_until'))[:10])
            ent_limit.delete(0, tk.END)
            ent_limit.insert(0, str(disc_data.get('usage_limit', 100)))
            var_act.set(int(disc_data.get('is_active', 1)))

        def on_save():
            code = ent_code.get().strip()
            desc = ent_desc.get().strip()
            dtype = cmb_type.get()
            val = ent_val.get().strip()
            min_spend = ent_min.get().strip()
            until = ent_until.get().strip()
            limit = ent_limit.get().strip()
            active = var_act.get()

            if disc_data:
                ok, msg = DiscountManager.update_discount(
                    disc_data['id'], code, desc, dtype, val, min_spend,
                    None, until, limit, active
                )
            else:
                ok, msg = DiscountManager.add_discount(
                    code, desc, dtype, val, min_spend,
                    None, until, limit, active
                )

            if ok:
                messagebox.showinfo("Success", msg)
                modal.destroy()
                self.load_data()
            else:
                messagebox.showerror("Validation Error", msg)

        btn_box = tk.Frame(frame, bg="#FFFFFF")
        btn_box.pack(fill=tk.X, pady=(5, 0))

        save_btn = tk.Button(btn_box, text="Save Voucher", font=("Segoe UI", 9, "bold"), bg="#4F46E5", fg="#FFFFFF", relief="flat", cursor="hand2", padx=12, pady=6, command=on_save)
        save_btn.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_btn = tk.Button(btn_box, text="Cancel", font=("Segoe UI", 9), bg="#E2E8F0", fg="#334155", relief="flat", cursor="hand2", padx=12, pady=6, command=modal.destroy)
        cancel_btn.pack(side=tk.RIGHT)

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Select a coupon to delete.")
            return

        item = self.tree.item(selected[0])['values']
        disc_id = item[0]
        code = item[1]

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to remove coupon '{code}' (ID #{disc_id})?"):
            return

        ok, msg = DiscountManager.delete_discount(disc_id)
        if ok:
            messagebox.showinfo("Success", msg)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Discount Vouchers Manager — Member 3")
    root.geometry("1020x640")
    init_db()
    view = DiscountView(root)
    view.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
