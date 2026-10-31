"""
billing/hub.py - Unified Billing, Invoicing & Tax Hub (Member 3 Deliverable)
Subscription Management System

Combines all four Member 3 sub-modules into a modern tabbed interface:
- Invoices & Statements
- Payment Gateways & Refunds
- Promotional Discounts & Coupons
- Tax Jurisdictions & Rates
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from database import init_db
from billing.taxes import TaxView
from billing.discounts import DiscountView
from billing.invoices import InvoiceView
from billing.payments import PaymentView


class BillingHub(ttk.Frame):
    """Unified Tabbed Navigation Hub for Member 3's Billing & Invoicing Suite."""

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # 1. Top Global Navigation Header
        top_bar = tk.Frame(self, bg="#0F172A", height=58, padx=20, pady=12)
        top_bar.pack(fill=tk.X)

        title_lbl = tk.Label(
            top_bar,
            text="💳 BrightLoop — Billing, Invoicing & Payments Suite",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        title_lbl.pack(side=tk.LEFT)

        subtitle_lbl = tk.Label(
            top_bar,
            text="[ Member 3: Invoices • Payments • Discounts • Taxes ]",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        subtitle_lbl.pack(side=tk.LEFT, padx=(12, 0))

        refresh_all_btn = tk.Button(
            top_bar,
            text="🔄 Refresh All Billing Data",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=5,
            command=self.refresh_all
        )
        refresh_all_btn.pack(side=tk.RIGHT)

        # 2. Tabbed Notebook Interface
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        # Tab 1: Invoices
        self.invoice_view = InvoiceView(self.notebook)
        self.notebook.add(self.invoice_view, text="  🧾 Invoices & Statements  ")

        # Tab 2: Payments
        self.payment_view = PaymentView(self.notebook)
        self.notebook.add(self.payment_view, text="  💳 Payment Gateway & Refunds  ")

        # Tab 3: Discounts
        self.discount_view = DiscountView(self.notebook)
        self.notebook.add(self.discount_view, text="  🎟️ Discounts & Promo Codes  ")

        # Tab 4: Taxes
        self.tax_view = TaxView(self.notebook)
        self.notebook.add(self.tax_view, text="  🏛️ Tax Jurisdictions & Rates  ")

        # Refresh on tab change
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        """Automatically synchronizes data when switching tabs."""
        selected_tab = self.notebook.select()
        widget = self.nametowidget(selected_tab)
        if hasattr(widget, 'load_data'):
            widget.load_data()

    def refresh_all(self):
        """Forces all Member 3 views to reload live records."""
        try:
            self.invoice_view.load_data()
            self.payment_view.load_data()
            self.discount_view.load_data()
            self.tax_view.load_data()
            messagebox.showinfo("Billing Hub", "All billing, payment, coupon, and tax records reloaded successfully.")
        except Exception as ex:
            messagebox.showerror("Refresh Error", f"Error refreshing billing views: {ex}")


if __name__ == '__main__':
    root = tk.Tk()
    root.title("BrightLoop Billing Suite — Member 3 Hub")
    root.geometry("1180x750")
    root.minsize(980, 620)
    init_db()
    hub = BillingHub(root)
    hub.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
