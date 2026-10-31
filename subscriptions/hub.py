"""
subscriptions/hub.py - Unified Subscription Management Hub (Member 2 Deliverable)
Subscription Management System

Combines all four sub-modules into a tabbed interface:
- Subscriptions Dashboard
- Product Catalog
- Subscription Plans
- Plan Variants & Add-ons
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

from database import init_db
from subscriptions.products import ProductView
from subscriptions.plans import PlanView
from subscriptions.variants import VariantView
from subscriptions.subscriptions import SubscriptionView


class SubscriptionHub(ttk.Frame):
    """Unified Tabbed Navigation Hub for Member 2's Subscription Management Module."""

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # 1. Top Global Navigation Header
        top_bar = tk.Frame(self, bg="#1E293B", height=58, padx=20, pady=12)
        top_bar.pack(fill=tk.X)

        title_lbl = tk.Label(
            top_bar,
            text="⚡ BrightLoop — Subscription Management Suite",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#1E293B"
        )
        title_lbl.pack(side=tk.LEFT)

        subtitle_lbl = tk.Label(
            top_bar,
            text="[ Member 2: Products • Plans • Variants • Subscriptions ]",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#1E293B"
        )
        subtitle_lbl.pack(side=tk.LEFT, padx=(12, 0))

        refresh_all_btn = tk.Button(
            top_bar,
            text="🔄 Refresh All",
            font=("Segoe UI", 9, "bold"),
            bg="#3B82F6",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.refresh_all
        )
        refresh_all_btn.pack(side=tk.RIGHT)

        # 2. Notebook (Tabbed Container)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Tab 1: Subscriptions
        self.sub_view = SubscriptionView(self.notebook)
        self.notebook.add(self.sub_view, text=" 📑 Subscriptions ")

        # Tab 2: Products
        self.prod_view = ProductView(self.notebook)
        self.notebook.add(self.prod_view, text=" 📦 Products ")

        # Tab 3: Plans
        self.plan_view = PlanView(self.notebook)
        self.notebook.add(self.plan_view, text=" 💳 Plans ")

        # Tab 4: Variants
        self.var_view = VariantView(self.notebook)
        self.notebook.add(self.var_view, text=" 🏷️ Variants ")

        # Re-sync data when switching tabs so modifications reflect immediately across tabs
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        selected_tab = self.notebook.select()
        tab_id = self.notebook.index(selected_tab)
        if tab_id == 0:
            self.sub_view.refresh()
        elif tab_id == 1:
            self.prod_view.refresh()
        elif tab_id == 2:
            self.plan_view.refresh()
        elif tab_id == 3:
            self.var_view.refresh()

    def refresh_all(self):
        """Refreshes all sub-views."""
        self.sub_view.refresh()
        self.prod_view.refresh()
        self.plan_view.refresh()
        self.var_view.refresh()
        messagebox.showinfo("Refreshed", "All subscription data and catalogs have been updated.", parent=self)


def launch():
    """Starts the standalone Subscription Hub."""
    init_db()
    root = tk.Tk()
    root.title("BrightLoop - Subscription Management Suite (Member 2)")
    root.geometry("1160x720")
    root.minsize(980, 600)

    # Apply modern styling
    style = ttk.Style(root)
    style.theme_use("clam")

    hub = SubscriptionHub(root)
    hub.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    launch()
