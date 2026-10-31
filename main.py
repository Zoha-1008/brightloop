"""
main.py - Main Application Launcher
Subscription Management System

Starts the system, initializes the database, and loads the active modules.
Currently launches Member 2's Subscription Management Suite by default.
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


class MainApplication(tk.Tk):
    """Central Root Application Window."""

    def __init__(self):
        super().__init__()
        self.title("BrightLoop — Subscription Management System")
        self.geometry("1200x750")
        self.minsize(1000, 650)

        # Style configuration
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

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
        mod_menu.add_command(label="⚡ Subscriptions Suite (Member 2 - Active)", command=self._load_subscriptions)
        mod_menu.add_command(label="💳 Billing & Invoices (Member 3)", command=lambda: self._placeholder_alert("Member 3: Billing"))
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
        self.hub = SubscriptionHub(self)
        self.hub.pack(fill=tk.BOTH, expand=True)

    def _load_subscriptions(self):
        if hasattr(self, 'hub'):
            self.hub.refresh_all()

    def _refresh_current(self):
        if hasattr(self, 'hub'):
            self.hub.refresh_all()

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
            f"Currently active module: Member 2 (Subscriptions, Products, Plans, Variants)."
        )

    def _show_about(self):
        messagebox.showinfo(
            "About BrightLoop",
            "BrightLoop Subscription Management System\n\n"
            "Member 2 Core Deliverables:\n"
            "• products.py - Product Catalog & Categories\n"
            "• plans.py - Subscription Tiers & Billing Cycles\n"
            "• variants.py - Custom Add-ons & Plan Options\n"
            "• subscriptions.py - Customer Subscription Lifecycle & MRR Tracking\n\n"
            f"Database Connected: {db.engine.upper()}"
        )


def main():
    print("[Main] Initializing Subscription Management System...")
    init_db()
    app = MainApplication()
    app.mainloop()


if __name__ == "__main__":
    main()
