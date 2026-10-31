"""
billing/invoices.py - Invoicing Engine & Statement Management (Member 3 Deliverable)
Subscription Management System

Provides backend Data Access Object (InvoiceManager), invoice lifecycle transitions,
and modern Tkinter GUI (InvoiceView) with printable receipt viewer and text file export.
"""

import sys
import os
import random
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class InvoiceManager:
    """Backend Data Access Object for Invoices and Billing Statements."""

    VALID_STATUSES = ['Pending', 'Paid', 'Overdue', 'Cancelled']

    @staticmethod
    def generate_invoice_number():
        """Generates a professional unique invoice identifier."""
        year = datetime.date.today().year
        rand_num = random.randint(10000, 99999)
        candidate = f"INV-{year}-{rand_num}"
        # Ensure uniqueness
        while InvoiceManager.get_invoice_by_number(candidate):
            rand_num = random.randint(10000, 99999)
            candidate = f"INV-{year}-{rand_num}"
        return candidate

    @staticmethod
    def get_all_invoices(search_term=None, status=None, customer_id=None):
        """Fetch invoices with enriched customer and plan details."""
        query = """
            SELECT 
                i.*,
                c.name AS customer_name,
                c.email AS customer_email,
                c.company AS customer_company,
                s.subscription_code,
                d.code AS discount_code,
                t.tax_name,
                t.rate AS tax_rate
            FROM invoices i
            JOIN customers c ON i.customer_id = c.id
            LEFT JOIN subscriptions s ON i.subscription_id = s.id
            LEFT JOIN discounts d ON i.discount_id = d.id
            LEFT JOIN taxes t ON i.tax_id = t.id
            WHERE 1=1
        """
        params = []

        if search_term:
            query += " AND (i.invoice_number LIKE %s OR c.name LIKE %s OR c.email LIKE %s)"
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw])

        if status and status != "All Statuses":
            query += " AND i.status = %s"
            params.append(status)

        if customer_id:
            query += " AND i.customer_id = %s"
            params.append(customer_id)

        query += " ORDER BY i.id DESC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_invoice_by_id(invoice_id):
        """Fetch single invoice with full joined details."""
        query = """
            SELECT 
                i.*,
                c.name AS customer_name,
                c.email AS customer_email,
                c.phone AS customer_phone,
                c.company AS customer_company,
                c.address AS customer_address,
                c.city AS customer_city,
                c.postal_code AS customer_postal,
                s.subscription_code,
                s.billing_cycle,
                p.name AS product_name,
                pl.name AS plan_name,
                d.code AS discount_code,
                t.tax_name,
                t.rate AS tax_rate
            FROM invoices i
            JOIN customers c ON i.customer_id = c.id
            LEFT JOIN subscriptions s ON i.subscription_id = s.id
            LEFT JOIN products p ON s.product_id = p.id
            LEFT JOIN plans pl ON s.plan_id = pl.id
            LEFT JOIN discounts d ON i.discount_id = d.id
            LEFT JOIN taxes t ON i.tax_id = t.id
            WHERE i.id = %s
        """
        return db.fetch_one(query, (invoice_id,))

    @staticmethod
    def get_invoice_by_number(inv_number):
        """Fetch invoice by invoice number string."""
        if not inv_number:
            return None
        return db.fetch_one("SELECT * FROM invoices WHERE invoice_number = %s", (inv_number.strip().upper(),))

    @staticmethod
    def create_invoice(customer_id, subscription_id=None, subtotal=0.0,
                       discount_id=None, discount_amount=0.0,
                       tax_id=None, tax_amount=0.0, total_amount=0.0,
                       due_days=15, notes=None, status='Pending'):
        """Create a new itemized billing invoice."""
        today = datetime.date.today()
        due = today + datetime.timedelta(days=due_days)
        inv_num = InvoiceManager.generate_invoice_number()

        db.execute_query(
            """
            INSERT INTO invoices
            (invoice_number, subscription_id, customer_id, issue_date, due_date,
             subtotal, discount_id, discount_amount, tax_id, tax_amount, total_amount, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (inv_num, subscription_id, customer_id, today.strftime("%Y-%m-%d"), due.strftime("%Y-%m-%d"),
             float(subtotal), discount_id, float(discount_amount), tax_id, float(tax_amount), float(total_amount),
             status, notes or "Subscription billing statement")
        )
        return True, inv_num

    @staticmethod
    def update_invoice_status(invoice_id, new_status):
        """Update payment lifecycle state of invoice."""
        if new_status not in InvoiceManager.VALID_STATUSES:
            return False, f"Invalid status '{new_status}'."

        db.execute_query("UPDATE invoices SET status = %s WHERE id = %s", (new_status, invoice_id))
        return True, f"Invoice #{invoice_id} marked as '{new_status}'."

    @staticmethod
    def build_receipt_text(inv):
        """Formats an itemized text receipt."""
        lines = []
        lines.append("=" * 64)
        lines.append("          ⚡ BRIGHTLOOP SUBSCRIPTION SERVICES")
        lines.append("                OFFICIAL BILLING RECEIPT")
        lines.append("=" * 64)
        lines.append(f" Invoice Number : {inv.get('invoice_number', 'N/A')}")
        lines.append(f" Issue Date     : {str(inv.get('issue_date', ''))[:10]}")
        lines.append(f" Due Date       : {str(inv.get('due_date', ''))[:10]}")
        lines.append(f" Status         : {inv.get('status', 'Pending').upper()}")
        lines.append("-" * 64)
        lines.append(" BILLED TO:")
        lines.append(f" Customer Name  : {inv.get('customer_name', 'Valued Customer')}")
        lines.append(f" Email          : {inv.get('customer_email', 'N/A')}")
        if inv.get('customer_company'):
            lines.append(f" Company        : {inv.get('customer_company')}")
        if inv.get('customer_address'):
            lines.append(f" Address        : {inv.get('customer_address')}, {inv.get('customer_city', '')} {inv.get('customer_postal', '')}")
        lines.append("-" * 64)
        lines.append(" SUBSCRIPTION DETAILS:")
        sub_code = inv.get('subscription_code') or 'Direct Invoice'
        prod = inv.get('product_name') or 'Subscription Plan'
        plan = inv.get('plan_name') or 'Standard Tier'
        cycle = inv.get('billing_cycle') or 'Monthly'
        lines.append(f" Subscription   : {sub_code}")
        lines.append(f" Item / Plan    : {prod} — {plan} ({cycle})")
        lines.append("-" * 64)
        lines.append(" STATEMENT BREAKDOWN:")
        lines.append(f" Base Subtotal               : ${float(inv.get('subtotal', 0.0)):>10.2f}")
        
        disc_amt = float(inv.get('discount_amount', 0.0) or 0.0)
        disc_code = inv.get('discount_code') or 'Coupon'
        if disc_amt > 0:
            lines.append(f" Discount ({disc_code:<12})     : -${disc_amt:>9.2f}")
        else:
            lines.append(f" Discount                    :  ${0.0:>10.2f}")

        tax_amt = float(inv.get('tax_amount', 0.0) or 0.0)
        tax_desc = inv.get('tax_name') or 'Tax'
        if tax_amt > 0:
            lines.append(f" Tax ({tax_desc:<16})   : +${tax_amt:>9.2f}")
        else:
            lines.append(f" Tax                         :  ${0.0:>10.2f}")

        lines.append(" " + "-" * 62)
        total = float(inv.get('total_amount', 0.0))
        lines.append(f" TOTAL PAYABLE               : ${total:>10.2f}")
        lines.append("=" * 64)
        lines.append(" Notes: " + str(inv.get('notes', 'Thank you for your business!')))
        lines.append(" Questions? Contact billing-support@brightloop.io")
        lines.append("=" * 64)
        return "\n".join(lines)


class InvoiceView(ttk.Frame):
    """Modern Tkinter GUI for Invoice Statements & Receipt Viewer."""

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
            text="🧾 Invoices & Billing Statements",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Member 3 Deliverable — Track receivables, review itemized line items, and print receipts",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A"
        ).pack(anchor="w")

        btn_box = tk.Frame(header, bg="#0F172A")
        btn_box.pack(side=tk.RIGHT)

        view_btn = tk.Button(
            btn_box,
            text="📄 View & Print Invoice",
            font=("Segoe UI", 9, "bold"),
            bg="#4F46E5",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._view_selected_invoice
        )
        view_btn.pack(side=tk.LEFT, padx=5)

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

        tk.Label(filter_frame, text="Search Customer / Invoice #:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry = ttk.Entry(filter_frame, width=28, font=("Segoe UI", 9))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 20))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data())

        tk.Label(filter_frame, text="Status:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.status_combo = ttk.Combobox(filter_frame, values=["All Statuses", "Pending", "Paid", "Overdue", "Cancelled"], state="readonly", width=14, font=("Segoe UI", 9))
        self.status_combo.set("All Statuses")
        self.status_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        clear_btn = tk.Button(filter_frame, text="Clear", font=("Segoe UI", 8), bg="#F1F5F9", fg="#475569", relief="groove", cursor="hand2", command=self._clear_filters)
        clear_btn.pack(side=tk.LEFT)

        # 3. Main Data Table
        table_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=15)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "inv_num", "customer", "issue_date", "due_date", "subtotal", "discount", "tax", "total", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("inv_num", text="Invoice #")
        self.tree.heading("customer", text="Customer Name")
        self.tree.heading("issue_date", text="Issue Date")
        self.tree.heading("due_date", text="Due Date")
        self.tree.heading("subtotal", text="Subtotal ($)")
        self.tree.heading("discount", text="Discount ($)")
        self.tree.heading("tax", text="Tax ($)")
        self.tree.heading("total", text="Total ($)")
        self.tree.heading("status", text="Payment Status")

        self.tree.column("id", width=45, anchor="center")
        self.tree.column("inv_num", width=125, anchor="center")
        self.tree.column("customer", width=160, anchor="w")
        self.tree.column("issue_date", width=95, anchor="center")
        self.tree.column("due_date", width=95, anchor="center")
        self.tree.column("subtotal", width=90, anchor="e")
        self.tree.column("discount", width=90, anchor="e")
        self.tree.column("tax", width=80, anchor="e")
        self.tree.column("total", width=95, anchor="e")
        self.tree.column("status", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._view_selected_invoice())

        # 4. Status Transition Actions Toolbar
        ops_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=10)
        ops_frame.pack(fill=tk.X)

        tk.Label(ops_frame, text="Quick Status Actions:", font=("Segoe UI", 9, "bold"), bg="#F8FAFC", fg="#334155").pack(side=tk.LEFT, padx=(0, 8))

        btn_paid = tk.Button(ops_frame, text="✅ Mark Paid", font=("Segoe UI", 9), bg="#DCFCE7", fg="#166534", relief="flat", cursor="hand2", padx=8, pady=3, command=lambda: self._set_status("Paid"))
        btn_paid.pack(side=tk.LEFT, padx=(0, 5))

        btn_overdue = tk.Button(ops_frame, text="⚠️ Mark Overdue", font=("Segoe UI", 9), bg="#FEF3C7", fg="#92400E", relief="flat", cursor="hand2", padx=8, pady=3, command=lambda: self._set_status("Overdue"))
        btn_overdue.pack(side=tk.LEFT, padx=(0, 5))

        btn_cancel = tk.Button(ops_frame, text="❌ Mark Cancelled", font=("Segoe UI", 9), bg="#FEE2E2", fg="#991B1B", relief="flat", cursor="hand2", padx=8, pady=3, command=lambda: self._set_status("Cancelled"))
        btn_cancel.pack(side=tk.LEFT, padx=(0, 10))

        self.count_lbl = tk.Label(ops_frame, text="Total Invoices: 0", font=("Segoe UI", 9, "italic"), bg="#F8FAFC", fg="#64748B")
        self.count_lbl.pack(side=tk.RIGHT)

    def _clear_filters(self):
        self.search_entry.delete(0, tk.END)
        self.status_combo.set("All Statuses")
        self.load_data()

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        search = self.search_entry.get().strip()
        status = self.status_combo.get()

        invoices = InvoiceManager.get_all_invoices(search, status)
        for inv in invoices:
            sub_fmt = f"${float(inv.get('subtotal', 0.0)):.2f}"
            disc_fmt = f"-${float(inv.get('discount_amount', 0.0)):.2f}" if float(inv.get('discount_amount', 0.0)) > 0 else "$0.00"
            tax_fmt = f"+${float(inv.get('tax_amount', 0.0)):.2f}" if float(inv.get('tax_amount', 0.0)) > 0 else "$0.00"
            tot_fmt = f"${float(inv.get('total_amount', 0.0)):.2f}"

            self.tree.insert("", tk.END, values=(
                inv['id'], inv['invoice_number'], inv['customer_name'],
                str(inv['issue_date'])[:10], str(inv['due_date'])[:10],
                sub_fmt, disc_fmt, tax_fmt, tot_fmt, inv['status']
            ))

        self.count_lbl.config(text=f"Total Invoices: {len(invoices)}")

    def _set_status(self, new_status):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select an invoice from the table first.")
            return

        inv_id = self.tree.item(selected[0])['values'][0]
        ok, msg = InvoiceManager.update_invoice_status(inv_id, new_status)
        if ok:
            messagebox.showinfo("Status Updated", msg)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)

    def _view_selected_invoice(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select an invoice to view its itemized receipt.")
            return

        inv_id = self.tree.item(selected[0])['values'][0]
        inv = InvoiceManager.get_invoice_by_id(inv_id)
        if not inv:
            messagebox.showerror("Not Found", "Could not locate invoice details.")
            return

        self._show_receipt_modal(inv)

    def _show_receipt_modal(self, inv):
        modal = tk.Toplevel(self)
        modal.title(f"Receipt - {inv.get('invoice_number')}")
        modal.geometry("580x640")
        modal.grab_set()

        top_frame = tk.Frame(modal, bg="#0F172A", padx=15, pady=12)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text=f"Official Invoice: {inv.get('invoice_number')}", font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg="#0F172A").pack(side=tk.LEFT)

        status_color = "#10B981" if inv.get('status') == 'Paid' else "#F59E0B"
        badge = tk.Label(top_frame, text=f" [{inv.get('status', 'Pending').upper()}] ", font=("Segoe UI", 10, "bold"), fg=status_color, bg="#0F172A")
        badge.pack(side=tk.RIGHT)

        text_frame = tk.Frame(modal, bg="#FFFFFF", padx=15, pady=15)
        text_frame.pack(fill=tk.BOTH, expand=True)

        receipt_content = InvoiceManager.build_receipt_text(inv)

        txt_view = tk.Text(text_frame, font=("Courier New", 9), wrap="none", bg="#F8FAFC", fg="#0F172A", padx=10, pady=10)
        txt_view.insert("1.0", receipt_content)
        txt_view.configure(state="disabled")
        txt_view.pack(fill=tk.BOTH, expand=True)

        bottom_bar = tk.Frame(modal, bg="#F1F5F9", padx=15, pady=10)
        bottom_bar.pack(fill=tk.X)

        def export_txt():
            default_name = f"{inv.get('invoice_number')}_Receipt.txt"
            path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=default_name, filetypes=[("Text files", "*.txt")])
            if path:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(receipt_content)
                    messagebox.showinfo("Export Successful", f"Saved receipt statement to:\n{path}")
                except Exception as ex:
                    messagebox.showerror("Export Failed", str(ex))

        export_btn = tk.Button(bottom_bar, text="💾 Export to Text File (.txt)", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="#FFFFFF", relief="flat", cursor="hand2", padx=12, pady=5, command=export_txt)
        export_btn.pack(side=tk.LEFT)

        close_btn = tk.Button(bottom_bar, text="Close", font=("Segoe UI", 9), bg="#E2E8F0", fg="#334155", relief="flat", cursor="hand2", padx=12, pady=5, command=modal.destroy)
        close_btn.pack(side=tk.RIGHT)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Invoices & Billing Statements — Member 3")
    root.geometry("1060x640")
    init_db()
    view = InvoiceView(root)
    view.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
