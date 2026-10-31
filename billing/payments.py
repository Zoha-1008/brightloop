"""
billing/payments.py - Payment Gateway & Transaction Reconciliation (Member 3 Deliverable)
Subscription Management System

Provides backend Data Access Object (PaymentManager), multi-channel transaction recording,
settlement processing, and modern Tkinter GUI (PaymentView) with refund handling.
"""

import sys
import os
import random
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import db, init_db


class PaymentManager:
    """Backend Data Access Object for Payment Gateways and Transactions."""

    GATEWAYS = ['Credit Card', 'PayPal', 'Bank Transfer', 'UPI']
    STATUSES = ['Success', 'Failed', 'Refunded']

    @staticmethod
    def generate_transaction_id(method='Credit Card'):
        """Generates a unique tracking transaction ID based on gateway method."""
        prefix_map = {
            'Credit Card': 'CC',
            'PayPal': 'PP',
            'Bank Transfer': 'BT',
            'UPI': 'UPI'
        }
        prefix = prefix_map.get(method, 'TXN')
        rand_code = random.randint(1000000, 9999999)
        return f"TXN-{prefix}-{rand_code}"

    @staticmethod
    def get_all_payments(search_term=None, method=None, status=None):
        """Fetch transactions joined with invoice and customer records."""
        query = """
            SELECT 
                p.*,
                i.invoice_number,
                i.total_amount AS invoice_total,
                c.name AS customer_name,
                c.email AS customer_email
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN customers c ON p.customer_id = c.id
            WHERE 1=1
        """
        params = []

        if search_term:
            query += " AND (p.transaction_id LIKE %s OR i.invoice_number LIKE %s OR c.name LIKE %s)"
            kw = f"%{search_term.strip()}%"
            params.extend([kw, kw, kw])

        if method and method != "All Methods":
            query += " AND p.payment_method = %s"
            params.append(method)

        if status and status != "All Statuses":
            query += " AND p.status = %s"
            params.append(status)

        query += " ORDER BY p.id DESC"
        return db.fetch_all(query, params)

    @staticmethod
    def get_payment_by_id(payment_id):
        """Fetch transaction by ID."""
        return db.fetch_one("SELECT * FROM payments WHERE id = %s", (payment_id,))

    @staticmethod
    def record_payment(invoice_id, customer_id, payment_method, amount, notes=None):
        """
        Captures and settles payment for an invoice.
        Also automatically marks the corresponding invoice as 'Paid' and increments coupon redemptions.
        """
        if payment_method not in PaymentManager.GATEWAYS:
            return False, None, f"Unsupported payment gateway: '{payment_method}'."

        try:
            amt = float(amount)
            if amt <= 0:
                return False, None, "Payment amount must be greater than zero."
        except ValueError:
            return False, None, "Invalid numeric amount."

        txn_id = PaymentManager.generate_transaction_id(payment_method)

        # 1. Insert Payment
        db.execute_query(
            """
            INSERT INTO payments (transaction_id, invoice_id, customer_id, payment_method, amount, status, notes)
            VALUES (%s, %s, %s, %s, %s, 'Success', %s)
            """,
            (txn_id, invoice_id, customer_id, payment_method, amt, notes or f"{payment_method} settlement")
        )

        # 2. Mark Invoice as Paid
        db.execute_query("UPDATE invoices SET status = 'Paid' WHERE id = %s", (invoice_id,))

        # 3. Increment discount usage if invoice had one
        inv = db.fetch_one("SELECT discount_id FROM invoices WHERE id = %s", (invoice_id,))
        if inv and inv.get('discount_id'):
            db.execute_query("UPDATE discounts SET times_used = times_used + 1 WHERE id = %s", (inv['discount_id'],))

        return True, txn_id, f"Payment {txn_id} recorded and invoice settled successfully."

    @staticmethod
    def process_refund(payment_id, reason="Customer requested refund"):
        """Refunds a transaction and updates records."""
        pay = PaymentManager.get_payment_by_id(payment_id)
        if not pay:
            return False, "Transaction not found."

        if pay.get('status') == 'Refunded':
            return False, "This transaction has already been refunded."

        # Mark payment refunded
        db.execute_query(
            "UPDATE payments SET status = 'Refunded', notes = %s WHERE id = %s",
            (f"Refunded: {reason}", payment_id)
        )

        # Reopen or note invoice
        db.execute_query(
            "UPDATE invoices SET notes = 'Transaction refunded by billing team' WHERE id = %s",
            (pay['invoice_id'],)
        )

        return True, f"Transaction #{payment_id} (${float(pay['amount']):.2f}) successfully refunded."

    @staticmethod
    def get_financial_summary():
        """Computes settled revenue and refund volume."""
        all_pays = db.fetch_all("SELECT amount, status FROM payments")
        settled = sum(float(p['amount']) for p in all_pays if p.get('status') == 'Success')
        refunded = sum(float(p['amount']) for p in all_pays if p.get('status') == 'Refunded')
        return {
            'settled_volume': settled,
            'refund_volume': refunded,
            'net_volume': settled - refunded,
            'total_txns': len(all_pays)
        }


class PaymentView(ttk.Frame):
    """Modern Tkinter GUI for Payment Gateway Transactions."""

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
            text="💳 Payment Gateways & Transaction Logs",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Member 3 Deliverable — Settle customer invoices, capture gateway payments, and issue refunds",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A"
        ).pack(anchor="w")

        btn_box = tk.Frame(header, bg="#0F172A")
        btn_box.pack(side=tk.RIGHT)

        pay_btn = tk.Button(
            btn_box,
            text="+ Process New Payment",
            font=("Segoe UI", 9, "bold"),
            bg="#4F46E5",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._open_process_dialog
        )
        pay_btn.pack(side=tk.LEFT, padx=5)

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

        # 2. KPI Summary Bar
        kpi_frame = tk.Frame(self, bg="#1E293B", padx=20, pady=10)
        kpi_frame.pack(fill=tk.X)

        self.lbl_settled = tk.Label(kpi_frame, text="Settled: $0.00", font=("Segoe UI", 10, "bold"), fg="#10B981", bg="#1E293B")
        self.lbl_settled.pack(side=tk.LEFT, padx=(0, 25))

        self.lbl_refunded = tk.Label(kpi_frame, text="Refunded: $0.00", font=("Segoe UI", 10, "bold"), fg="#EF4444", bg="#1E293B")
        self.lbl_refunded.pack(side=tk.LEFT, padx=(0, 25))

        self.lbl_net = tk.Label(kpi_frame, text="Net Revenue: $0.00", font=("Segoe UI", 10, "bold"), fg="#38BDF8", bg="#1E293B")
        self.lbl_net.pack(side=tk.LEFT, padx=(0, 25))

        self.lbl_txns = tk.Label(kpi_frame, text="Transactions: 0", font=("Segoe UI", 10), fg="#94A3B8", bg="#1E293B")
        self.lbl_txns.pack(side=tk.RIGHT)

        # 3. Filter Bar
        filter_frame = tk.Frame(self, bg="#FFFFFF", padx=20, pady=12, bd=1, relief="solid")
        filter_frame.pack(fill=tk.X)

        tk.Label(filter_frame, text="Search Txn # / Invoice / Customer:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry = ttk.Entry(filter_frame, width=24, font=("Segoe UI", 9))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data())

        tk.Label(filter_frame, text="Gateway:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.method_combo = ttk.Combobox(filter_frame, values=["All Methods", "Credit Card", "PayPal", "Bank Transfer", "UPI"], state="readonly", width=14, font=("Segoe UI", 9))
        self.method_combo.set("All Methods")
        self.method_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.method_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        tk.Label(filter_frame, text="Status:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#334155").pack(side=tk.LEFT, padx=(0, 6))
        self.status_combo = ttk.Combobox(filter_frame, values=["All Statuses", "Success", "Failed", "Refunded"], state="readonly", width=12, font=("Segoe UI", 9))
        self.status_combo.set("All Statuses")
        self.status_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        clear_btn = tk.Button(filter_frame, text="Clear", font=("Segoe UI", 8), bg="#F1F5F9", fg="#475569", relief="groove", cursor="hand2", command=self._clear_filters)
        clear_btn.pack(side=tk.LEFT)

        # 4. Main Data Table
        table_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=15)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "txn_id", "inv_num", "customer", "method", "amount", "status", "notes", "paid_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("txn_id", text="Transaction Reference")
        self.tree.heading("inv_num", text="Invoice #")
        self.tree.heading("customer", text="Customer")
        self.tree.heading("method", text="Payment Gateway")
        self.tree.heading("amount", text="Amount ($)")
        self.tree.heading("status", text="Status")
        self.tree.heading("notes", text="Gateway Settlement Notes")
        self.tree.heading("paid_at", text="Processed At")

        self.tree.column("id", width=45, anchor="center")
        self.tree.column("txn_id", width=150, anchor="center")
        self.tree.column("inv_num", width=120, anchor="center")
        self.tree.column("customer", width=150, anchor="w")
        self.tree.column("method", width=110, anchor="center")
        self.tree.column("amount", width=95, anchor="e")
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("notes", width=180, anchor="w")
        self.tree.column("paid_at", width=130, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 5. Operations Toolbar
        ops_frame = tk.Frame(self, bg="#F8FAFC", padx=20, pady=10)
        ops_frame.pack(fill=tk.X)

        refund_btn = tk.Button(
            ops_frame,
            text="↩️ Issue Customer Refund",
            font=("Segoe UI", 9, "bold"),
            bg="#FEE2E2",
            fg="#991B1B",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=4,
            command=self._handle_refund
        )
        refund_btn.pack(side=tk.LEFT)

    def _clear_filters(self):
        self.search_entry.delete(0, tk.END)
        self.method_combo.set("All Methods")
        self.status_combo.set("All Statuses")
        self.load_data()

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        search = self.search_entry.get().strip()
        method = self.method_combo.get()
        status = self.status_combo.get()

        payments = PaymentManager.get_all_payments(search, method, status)
        for p in payments:
            amt_fmt = f"${float(p.get('amount', 0.0)):.2f}"
            time_fmt = str(p.get('paid_at', ''))[:16]

            self.tree.insert("", tk.END, values=(
                p['id'], p['transaction_id'], p['invoice_number'],
                p['customer_name'], p['payment_method'], amt_fmt,
                p['status'], p.get('notes', '-') or "-", time_fmt
            ))

        # Update KPIs
        stats = PaymentManager.get_financial_summary()
        self.lbl_settled.config(text=f"Settled: ${stats['settled_volume']:.2f}")
        self.lbl_refunded.config(text=f"Refunded: ${stats['refund_volume']:.2f}")
        self.lbl_net.config(text=f"Net Revenue: ${stats['net_volume']:.2f}")
        self.lbl_txns.config(text=f"Total Transactions: {stats['total_txns']}")

    def _open_process_dialog(self):
        """Dialog to settle an existing pending invoice."""
        pending_invoices = db.fetch_all("""
            SELECT i.id, i.invoice_number, i.total_amount, i.customer_id, c.name as customer_name
            FROM invoices i
            JOIN customers c ON i.customer_id = c.id
            WHERE i.status != 'Paid'
            ORDER BY i.id DESC
        """)

        if not pending_invoices:
            messagebox.showinfo("All Settled", "There are no pending or unpaid invoices at this time.")
            return

        modal = tk.Toplevel(self)
        modal.title("Process & Settle Invoice Payment")
        modal.geometry("450x380")
        modal.resizable(False, False)
        modal.grab_set()

        frame = tk.Frame(modal, bg="#FFFFFF", padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Capture Customer Payment", font=("Segoe UI", 12, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor="w", pady=(0, 15))

        inv_map = {}
        inv_labels = []
        for inv in pending_invoices:
            lbl = f"{inv['invoice_number']} — {inv['customer_name']} (${float(inv['total_amount']):.2f})"
            inv_labels.append(lbl)
            inv_map[lbl] = inv

        tk.Label(frame, text="Select Unpaid Invoice:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        cmb_inv = ttk.Combobox(frame, values=inv_labels, state="readonly", font=("Segoe UI", 9))
        cmb_inv.current(0)
        cmb_inv.pack(fill=tk.X, pady=(2, 10))

        tk.Label(frame, text="Payment Gateway / Channel:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        cmb_gate = ttk.Combobox(frame, values=PaymentManager.GATEWAYS, state="readonly", font=("Segoe UI", 9))
        cmb_gate.current(0)
        cmb_gate.pack(fill=tk.X, pady=(2, 10))

        tk.Label(frame, text="Settlement Amount ($):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_amt = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_amt.pack(fill=tk.X, pady=(2, 10))

        def update_amt(e=None):
            sel = cmb_inv.get()
            if sel in inv_map:
                ent_amt.delete(0, tk.END)
                ent_amt.insert(0, f"{float(inv_map[sel]['total_amount']):.2f}")

        cmb_inv.bind("<<ComboboxSelected>>", update_amt)
        update_amt()

        tk.Label(frame, text="Transaction Note / Receipt Reference:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(anchor="w")
        ent_note = ttk.Entry(frame, font=("Segoe UI", 9))
        ent_note.insert(0, "Settled via terminal capture")
        ent_note.pack(fill=tk.X, pady=(2, 15))

        def on_capture():
            sel = cmb_inv.get()
            if sel not in inv_map:
                return
            inv_obj = inv_map[sel]
            gateway = cmb_gate.get()
            amt = ent_amt.get().strip()
            note = ent_note.get().strip()

            ok, txn_id, msg = PaymentManager.record_payment(
                inv_obj['id'], inv_obj['customer_id'], gateway, amt, note
            )
            if ok:
                messagebox.showinfo("Payment Successful", f"Transaction Reference: {txn_id}\n\n{msg}")
                modal.destroy()
                self.load_data()
            else:
                messagebox.showerror("Transaction Failed", msg)

        btn_box = tk.Frame(frame, bg="#FFFFFF")
        btn_box.pack(fill=tk.X, pady=(10, 0))

        confirm_btn = tk.Button(btn_box, text="Capture & Settle", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="#FFFFFF", relief="flat", cursor="hand2", padx=12, pady=6, command=on_capture)
        confirm_btn.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_btn = tk.Button(btn_box, text="Cancel", font=("Segoe UI", 9), bg="#E2E8F0", fg="#334155", relief="flat", cursor="hand2", padx=12, pady=6, command=modal.destroy)
        cancel_btn.pack(side=tk.RIGHT)

    def _handle_refund(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a transaction to refund.")
            return

        item = self.tree.item(selected[0])['values']
        pay_id = item[0]
        txn_ref = item[1]
        amt = item[5]
        status = item[6]

        if status == 'Refunded':
            messagebox.showwarning("Already Refunded", f"Transaction {txn_ref} is already marked as Refunded.")
            return

        if not messagebox.askyesno("Confirm Customer Refund", f"Are you sure you want to refund {amt} for transaction {txn_ref}?"):
            return

        ok, msg = PaymentManager.process_refund(pay_id, "Customer requested chargeback/refund")
        if ok:
            messagebox.showinfo("Refund Processed", msg)
            self.load_data()
        else:
            messagebox.showerror("Refund Failed", msg)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Payments & Gateway Manager — Member 3")
    root.geometry("1060x640")
    init_db()
    view = PaymentView(root)
    view.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
