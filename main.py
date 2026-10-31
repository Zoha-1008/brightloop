"""
main.py - Main Application Launcher
Subscription Management System

Starts the system, initializes the database, and loads the active modules.
Integrates Member 2 (Subscriptions Suite) and Member 3 (Billing & Invoicing Suite).
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure current directory is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import db, init_db
from subscriptions.hub import SubscriptionHub
from billing.hub import BillingHub


class MainApplication(tk.Tk):
    """Central Root Application Window."""

    def __init__(self):
        super().__init__()
        self.title("BrightLoop — Subscription Management System")
        self.geometry("1240x780")
        self.minsize(1000, 650)

        # Style configuration
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.current_hub = None
        self._create_menu()
        self._load_active_module()

    def _create_menu(self):
        menubar = tk.Menu(self)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="🔄 Refresh System Data", command=self._refresh_current)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Modules Menu
        mod_menu = tk.Menu(menubar, tearoff=0)
        mod_menu.add_command(label="🔑 Authentication (Member 1)", command=lambda: self._placeholder_alert("Member 1: Auth"))
        mod_menu.add_command(label="⚡ Subscriptions Suite (Member 2)", command=self._load_subscriptions)
        mod_menu.add_command(label="💳 Billing & Invoices (Member 3 - Active)", command=self._load_billing)
        mod_menu.add_command(label="📊 Reports & Analytics (Member 4)", command=lambda: self._placeholder_alert("Member 4: Reports"))
        menubar.add_cascade(label="Modules", menu=mod_menu)

        # Database Menu
        db_menu = tk.Menu(menubar, tearoff=0)
        db_menu.add_command(label=f"Engine: {db.engine.upper()}", state="disabled")
        db_menu.add_command(label="Re-seed Sample Data", command=self._reseed_data)
        menubar.add_cascade(label="Database", menu=db_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About System", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _load_active_module(self):
        """Loads Member 3's Billing Hub as the default view."""
        self._switch_hub(BillingHub)

    def _switch_hub(self, hub_class):
        if self.current_hub:
            self.current_hub.destroy()
        self.current_hub = hub_class(self)
        self.current_hub.pack(fill=tk.BOTH, expand=True)

    def _load_subscriptions(self):
        self._switch_hub(SubscriptionHub)

    def _load_billing(self):
        self._switch_hub(BillingHub)

    def _refresh_current(self):
        if self.current_hub and hasattr(self.current_hub, 'refresh_all'):
            self.current_hub.refresh_all()

    def _reseed_data(self):
        confirm = messagebox.askyesno("Re-seed Data", "Do you want to re-check database tables and ensure sample records are loaded?")
        if confirm:
            init_db()
            self._refresh_current()
            messagebox.showinfo("Success", "Database tables verified and synchronized.")

    def _placeholder_alert(self, module_name):
        messagebox.showinfo(
            module_name,
            f"{module_name} is assigned to another team member.\n\n"
            f"Active modules:\n"
            f"• Member 2 (Subscriptions, Products, Plans, Variants)\n"
            f"• Member 3 (Billing, Invoices, Payments, Discounts, Taxes)"
        )

    def _show_about(self):
        messagebox.showinfo(
            "About BrightLoop",
            "BrightLoop Subscription Management System\n\n"
            "Member 2 Core Deliverables:\n"
            "• products.py - Product Catalog & Categories\n"
            "• plans.py - Subscription Tiers & Billing Cycles\n"
            "• variants.py - Custom Add-ons & Plan Options\n"
            "• subscriptions.py - Customer Subscription Lifecycle\n\n"
            "Member 3 Core Deliverables:\n"
            "• taxes.py - Regional Tax Rules & VAT/GST Engine\n"
            "• discounts.py - Promo Codes & Coupon Engine\n"
            "• invoices.py - Statement Lifecycle & Itemized Receipts\n"
            "• payments.py - Payment Gateways & Refund Management\n\n"
            f"Database Connected: {db.engine.upper()}"
        )


def main():
    print("[Main] Initializing Subscription Management System...")
    init_db()
    app = MainApplication()
    app.mainloop()


if __name__ == '__main__':
    main()
