"""
reports/reports.py - Comprehensive Tabular Report Generator & Exporter
Brightloop Software - Subscription Management System (Member 4)

Key Capabilities:
- 5 Specialized Business Reports:
  1. Financial & Revenue Report
  2. Subscription Lifecycle Report
  3. Overdue Debt & Aging Report
  4. Payment Collections & Audit Report
  5. Product & Plan Performance Report
- Interactive Data Table with dynamic live search, status filtering, and sorting
- Multi-format Export:
  - 📄 Professional PDF with ReportLab (Branded header, table formatting, page numbers)
  - 📊 Excel Spreadsheet with openpyxl/pandas (Styling, auto column width, totals)
  - 📝 CSV for universal data interchange
- High performance sub-second query execution (< 2.0s SLA)
"""

import sys
import os
import csv
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Ensure root directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database

# PDF generation with ReportLab
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Excel export with openpyxl
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic 'Page X of Y' numbering on PDFs."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(792 - 36, 20, page_text)
        self.drawString(36, 20, "Brightloop Software • Confidential Financial Report")
        self.restoreState()


class ReportsFrame(ttk.Frame):
    """Interactive report browser with multi-criteria filtering and exports."""

    REPORT_TYPES = {
        "Revenue & Financial Report": "revenue",
        "Subscription Lifecycle Report": "subscriptions",
        "Overdue Debt & Aging Report": "overdue",
        "Payment Collections Report": "payments",
        "Product & Plan Performance": "performance"
    }

    def __init__(self, parent, db_path=None):
        super().__init__(parent)
        self.db_path = db_path
        self.current_rows = []
        self.current_headers = []
        self.current_raw_data = []

        self.pack(fill=tk.BOTH, expand=True)
        self._setup_ui()
        self.load_report_data()

    def get_connection(self):
        return database.get_connection(self.db_path)

    def _setup_ui(self):
        # 1. Header Banner
        header = tk.Frame(self, bg="#1e1e2d", height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title_frame = tk.Frame(header, bg="#1e1e2d")
        title_frame.pack(side=tk.LEFT, padx=20, pady=12)

        tk.Label(
            title_frame,
            text="📑 Brightloop Report Center",
            font=("Segoe UI", 16, "bold"),
            fg="#ffffff",
            bg="#1e1e2d"
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="Generate, audit, and export multi-format financial and subscription reports",
            font=("Segoe UI", 9),
            fg="#a1a5b7",
            bg="#1e1e2d"
        ).pack(anchor="w")

        # 2. Controls Toolbar
        ctrl_panel = tk.Frame(self, bg="#f3f4f6", padx=15, pady=12)
        ctrl_panel.pack(fill=tk.X)

        # Report selector
        tk.Label(ctrl_panel, text="Report Type:", font=("Segoe UI", 9, "bold"), bg="#f3f4f6").pack(side=tk.LEFT, padx=(0, 4))
        self.report_type_var = tk.StringVar(value="Revenue & Financial Report")
        rep_cb = ttk.Combobox(
            ctrl_panel,
            textvariable=self.report_type_var,
            values=list(self.REPORT_TYPES.keys()),
            state="readonly",
            width=28
        )
        rep_cb.pack(side=tk.LEFT, padx=(0, 15))
        rep_cb.bind("<<ComboboxSelected>>", lambda e: self.load_report_data())

        # Status filter
        tk.Label(ctrl_panel, text="Status:", font=("Segoe UI", 9, "bold"), bg="#f3f4f6").pack(side=tk.LEFT, padx=(0, 4))
        self.status_var = tk.StringVar(value="All")
        self.status_cb = ttk.Combobox(
            ctrl_panel,
            textvariable=self.status_var,
            values=["All"],
            state="readonly",
            width=14
        )
        self.status_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self.filter_rows())

        # Search bar
        tk.Label(ctrl_panel, text="Search:", font=("Segoe UI", 9, "bold"), bg="#f3f4f6").pack(side=tk.LEFT, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_rows())
        search_entry = ttk.Entry(ctrl_panel, textvariable=self.search_var, width=18)
        search_entry.pack(side=tk.LEFT, padx=(0, 15))

        # Action & Export Buttons
        ttk.Button(ctrl_panel, text="🔄 Reload", command=self.load_report_data).pack(side=tk.LEFT, padx=3)

        export_group = tk.Frame(ctrl_panel, bg="#f3f4f6")
        export_group.pack(side=tk.RIGHT)

        ttk.Button(export_group, text="📄 Export PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=3)
        ttk.Button(export_group, text="📊 Export Excel", command=self.export_excel).pack(side=tk.LEFT, padx=3)
        ttk.Button(export_group, text="📝 Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=3)

        # 3. Main Data Table
        table_frame = ttk.Frame(self, padding="15 10 15 5")
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, show="headings", selectmode="browse")
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Tag colors
        self.tree.tag_configure("Paid", background="#ecfdf5")
        self.tree.tag_configure("Active", background="#f0fdf4")
        self.tree.tag_configure("Overdue", background="#fef2f2")
        self.tree.tag_configure("Closed", background="#f1f5f9")
        self.tree.tag_configure("Paused", background="#fffbeb")

        # 4. Footer Status Bar
        self.footer = tk.Frame(self, bg="#e2e8f0", height=32, padx=15)
        self.footer.pack(fill=tk.X, side=tk.BOTTOM)
        self.footer.pack_propagate(False)

        self.footer_status = tk.Label(
            self.footer,
            text="Ready",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#334155"
        )
        self.footer_status.pack(side=tk.LEFT)

        self.sla_lbl = tk.Label(
            self.footer,
            text="⚡ SLA: < 2.0s",
            font=("Segoe UI", 9, "bold"),
            bg="#e2e8f0",
            fg="#059669"
        )
        self.sla_lbl.pack(side=tk.RIGHT)

    def load_report_data(self):
        """Fetches data from SQLite database according to selected report type."""
        start_time = time.perf_counter()
        report_key = self.REPORT_TYPES[self.report_type_var.get()]
        conn = self.get_connection()
        cur = conn.cursor()

        if report_key == "revenue":
            self.current_headers = [
                ("Invoice #", 110, "center"),
                ("Customer / Company", 190, "w"),
                ("Invoice Date", 100, "center"),
                ("Due Date", 100, "center"),
                ("Subtotal ($)", 100, "e"),
                ("Tax ($)", 85, "e"),
                ("Discount ($)", 85, "e"),
                ("Total ($)", 105, "e"),
                ("Paid ($)", 105, "e"),
                ("Status", 95, "center")
            ]
            cur.execute("""
            SELECT
                i.invoice_number,
                COALESCE(c.company, c.name, u.email, 'Valued Customer') as customer,
                i.invoice_date,
                i.due_date,
                i.subtotal,
                i.tax_amount,
                i.discount_amount,
                i.total_amount,
                i.amount_paid,
                i.status
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id LEFT JOIN users u ON c.user_id = u.id OR i.customer_id = u.id
            ORDER BY i.invoice_date DESC;
            """)
            status_options = ["All", "Paid", "Confirmed", "Overdue", "Draft"]

        elif report_key == "subscriptions":
            self.current_headers = [
                ("Subscription #", 120, "center"),
                ("Customer", 180, "w"),
                ("Plan Name", 140, "w"),
                ("Billing Cycle", 100, "center"),
                ("Start Date", 100, "center"),
                ("Expiry Date", 100, "center"),
                ("Total Amount ($)", 120, "e"),
                ("Status", 100, "center")
            ]
            cur.execute("""
            SELECT
                COALESCE(s.subscription_code, 'SUB-' || s.id) as subscription_number,
                COALESCE(c.company, c.name, u.email, 'Valued Customer') as customer,
                p.name as plan_name,
                COALESCE(p.billing_cycle, 'Monthly') as billing_cycle,
                s.start_date,
                s.expiry_date,
                COALESCE(s.total_price, 0.0) as total_amount,
                s.status
            FROM subscriptions s
            LEFT JOIN customers c ON s.customer_id = c.id LEFT JOIN users u ON c.user_id = u.id OR s.customer_id = u.id
            JOIN plans p ON s.plan_id = p.id
            ORDER BY s.id DESC;
            """)
            status_options = ["All", "Active", "Paused", "Confirmed", "Quotation", "Draft", "Closed"]

        elif report_key == "overdue":
            self.current_headers = [
                ("Invoice #", 110, "center"),
                ("Customer", 180, "w"),
                ("Email", 180, "w"),
                ("Due Date", 100, "center"),
                ("Days Overdue", 100, "center"),
                ("Aging Bracket", 120, "center"),
                ("Balance Due ($)", 120, "e")
            ]
            cur.execute("""
            SELECT
                i.invoice_number,
                COALESCE(c.company, c.name, u.email, 'Valued Customer') as customer,
                u.email,
                i.due_date,
                CAST(julianday('now') - julianday(i.due_date) AS INTEGER) as days_overdue,
                CASE
                    WHEN (julianday('now') - julianday(i.due_date)) <= 30 THEN '1-30 Days'
                    WHEN (julianday('now') - julianday(i.due_date)) <= 60 THEN '31-60 Days'
                    WHEN (julianday('now') - julianday(i.due_date)) <= 90 THEN '61-90 Days'
                    ELSE '90+ Days (Severe)'
                END as bracket,
                (i.total_amount - i.amount_paid) as balance_due
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id LEFT JOIN users u ON c.user_id = u.id OR i.customer_id = u.id
            WHERE i.status = 'Overdue' AND (i.total_amount - i.amount_paid) > 0
            ORDER BY days_overdue DESC;
            """)
            status_options = ["All", "1-30 Days", "31-60 Days", "61-90 Days", "90+ Days (Severe)"]

        elif report_key == "payments":
            self.current_headers = [
                ("Txn ID", 80, "center"),
                ("Payment Ref", 140, "center"),
                ("Invoice #", 110, "center"),
                ("Customer", 180, "w"),
                ("Payment Date", 105, "center"),
                ("Method", 120, "center"),
                ("Amount Paid ($)", 120, "e"),
                ("Notes", 180, "w")
            ]
            cur.execute("""
            SELECT
                p.id,
                p.transaction_ref,
                i.invoice_number,
                COALESCE(c.company, c.name, u.email, 'Valued Customer') as customer,
                p.payment_date,
                p.payment_method,
                p.amount,
                p.notes
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            LEFT JOIN customers c ON p.customer_id = c.id LEFT JOIN users u ON c.user_id = u.id OR p.customer_id = u.id
            ORDER BY p.payment_date DESC;
            """)
            status_options = ["All", "Credit Card", "Bank Transfer", "Stripe", "PayPal", "Wire"]

        else:  # performance
            self.current_headers = [
                ("Product / Plan", 180, "w"),
                ("Category", 110, "center"),
                ("Sales Price ($)", 110, "e"),
                ("Active Subscribers", 130, "center"),
                ("Estimated MRR ($)", 130, "e"),
                ("Total Revenue ($)", 130, "e")
            ]
            cur.execute("""
            SELECT
                p.name,
                COALESCE(p.category, 'Software') as type,
                COALESCE(p.price, 0.0) as sales_price,
                COUNT(sl.id) as subscriber_count,
                COALESCE(SUM(sl.unit_price), 0.0) as estimated_mrr,
                COALESCE(SUM(il.line_total), 0.0) as total_rev
            FROM products p
            LEFT JOIN subscription_lines sl ON p.id = sl.product_id
            LEFT JOIN invoice_lines il ON p.id = il.product_id
            GROUP BY p.id, p.name, COALESCE(p.category, 'Software') as type, p.sales_price
            ORDER BY total_rev DESC;
            """)
            status_options = ["All", "Software", "Add-on", "Service"]

        raw_rows = cur.fetchall()
        conn.close()

        # Update columns in Treeview
        self.tree["columns"] = [h[0] for h in self.current_headers]
        for col_name, width, align in self.current_headers:
            self.tree.heading(col_name, text=col_name, command=lambda c=col_name: self.sort_column(c, False))
            self.tree.column(col_name, width=width, anchor=align)

        # Store raw data
        self.current_raw_data = [list(r) for r in raw_rows]

        # Update status options dropdown
        self.status_cb['values'] = status_options
        self.status_var.set("All")

        self.filter_rows()

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.sla_lbl.config(
            text=f"⚡ Query Latency: {elapsed_ms:.1f} ms (< 2.0s SLA)",
            fg="#059669" if elapsed_ms < 2000 else "#dc2626"
        )

    def filter_rows(self):
        """Applies status and search query filters live to the data table."""
        search_term = self.search_var.get().strip().lower()
        selected_status = self.status_var.get()

        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.current_rows = []
        total_amount_sum = 0.0

        for row in self.current_raw_data:
            # Check status match
            if selected_status != "All":
                row_str_full = " ".join(str(val) for val in row)
                if selected_status not in row_str_full:
                    continue

            # Check search match
            if search_term:
                match = any(search_term in str(val).lower() for val in row)
                if not match:
                    continue

            # Format values for display (e.g. currency formatting)
            formatted_vals = []
            tag = ""
            for i, val in enumerate(row):
                header_name = self.current_headers[i][0]
                if isinstance(val, (int, float)) and ("($)" in header_name or "Amount" in header_name or "Subtotal" in header_name or "Total" in header_name or "Paid" in header_name or "MRR" in header_name or "Tax" in header_name or "Discount" in header_name):
                    formatted_vals.append(f"${float(val):,.2f}")
                    if "Total ($)" in header_name or "Amount Paid ($)" in header_name or "Balance Due ($)" in header_name:
                        total_amount_sum += float(val)
                elif header_name == "Status" or header_name == "Aging Bracket":
                    formatted_vals.append(str(val))
                    tag = str(val)
                else:
                    formatted_vals.append(str(val) if val is not None else "")

            self.tree.insert("", tk.END, values=formatted_vals, tags=(tag,))
            self.current_rows.append(row)

        self.footer_status.config(
            text=f"Showing {len(self.current_rows)} of {len(self.current_raw_data)} records • Filtered Value Sum: ${total_amount_sum:,.2f}"
        )

    def sort_column(self, col_name, reverse):
        """Sorts table contents when clicking header."""
        col_idx = [h[0] for h in self.current_headers].index(col_name)
        try:
            self.current_raw_data.sort(key=lambda x: (x[col_idx] is None, x[col_idx]), reverse=reverse)
        except Exception:
            self.current_raw_data.sort(key=lambda x: str(x[col_idx]), reverse=reverse)

        self.tree.heading(col_name, command=lambda: self.sort_column(col_name, not reverse))
        self.filter_rows()

    def export_csv(self):
        """Exports the current filtered table view to CSV."""
        if not self.current_rows:
            messagebox.showwarning("Export Warning", "No data available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"Brightloop_{self.REPORT_TYPES[self.report_type_var.get()]}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = [h[0] for h in self.current_headers]
                writer.writerow(headers)
                writer.writerows(self.current_rows)

            messagebox.showinfo("Export Successful", f"✅ CSV report saved successfully:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save CSV file:\n{str(e)}")

    def export_excel(self):
        """Exports the current data to an Excel (.xlsx) file with professional formatting."""
        if not self.current_rows:
            messagebox.showwarning("Export Warning", "No data available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=f"Brightloop_{self.REPORT_TYPES[self.report_type_var.get()]}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = self.report_type_var.get()[:31]  # Excel tab name limit 31 chars

            # Header title block
            ws.merge_cells("A1:G1")
            ws["A1"] = f"Brightloop Software — {self.report_type_var.get()}"
            ws["A1"].font = Font(name="Segoe UI", size=14, bold=True, color="1E293B")

            ws["A2"] = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Filter: {self.status_var.get()}"
            ws["A2"].font = Font(name="Segoe UI", size=9, italic=True, color="64748B")

            # Column headers
            headers = [h[0] for h in self.current_headers]
            header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

            for col_num, h_text in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col_num, value=h_text)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Data rows
            thin_border = Border(
                left=Side(style='thin', color='E2E8F0'),
                right=Side(style='thin', color='E2E8F0'),
                top=Side(style='thin', color='E2E8F0'),
                bottom=Side(style='thin', color='E2E8F0')
            )

            for row_idx, row_data in enumerate(self.current_rows, 5):
                for col_idx, val in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.font = Font(name="Segoe UI", size=9)
                    cell.border = thin_border
                    if isinstance(val, (int, float)):
                        cell.number_format = "$#,##0.00"

            # Auto fit column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(file_path)
            messagebox.showinfo("Export Successful", f"✅ Excel spreadsheet saved successfully:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save Excel file:\n{str(e)}")

    def export_pdf(self):
        """Generates a professional corporate PDF report with ReportLab."""
        if not self.current_rows:
            messagebox.showwarning("Export Warning", "No data available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            initialfile=f"Brightloop_{self.REPORT_TYPES[self.report_type_var.get()]}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )
        if not file_path:
            return

        try:
            # Create landscape document
            doc = SimpleDocTemplate(
                file_path,
                pagesize=landscape(letter),
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=40
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontSize=18,
                leading=22,
                textColor=colors.HexColor("#0f172a")
            )
            subtitle_style = ParagraphStyle(
                'DocSubtitle',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor("#64748b")
            )
            table_cell_style = ParagraphStyle(
                'TableCell',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#1e293b")
            )
            table_head_style = ParagraphStyle(
                'TableHead',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                fontName="Helvetica-Bold",
                textColor=colors.white
            )

            story = []

            # 1. Branding Header
            title_p = Paragraph(f"<b>Brightloop Software</b> — {self.report_type_var.get()}", title_style)
            sub_text = f"Report Generated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}  |  Filter Scope: {self.status_var.get()}  |  Total Records: {len(self.current_rows)}"
            subtitle_p = Paragraph(sub_text, subtitle_style)

            story.append(title_p)
            story.append(subtitle_p)
            story.append(Spacer(1, 15))

            # 2. Table Data Preparation
            headers = [Paragraph(f"<b>{h[0]}</b>", table_head_style) for h in self.current_headers]
            table_data = [headers]

            for row in self.current_rows:
                row_cells = []
                for idx, val in enumerate(row):
                    header_name = self.current_headers[idx][0]
                    if isinstance(val, (int, float)) and ("($)" in header_name or "Amount" in header_name or "Subtotal" in header_name or "Total" in header_name or "Paid" in header_name or "MRR" in header_name):
                        str_val = f"${float(val):,.2f}"
                    else:
                        str_val = str(val) if val is not None else ""
                    row_cells.append(Paragraph(str_val, table_cell_style))
                table_data.append(row_cells)

            # 3. Create ReportLab Table
            pdf_table = Table(table_data, repeatRows=1)
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))

            story.append(pdf_table)

            # Build PDF with page numbers
            doc.build(story, canvasmaker=NumberedCanvas)
            messagebox.showinfo("Export Successful", f"✅ PDF report generated successfully:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not generate PDF report:\n{str(e)}")


class ReportsWindow(tk.Toplevel):
    """Standalone window for Reports."""
    def __init__(self, parent=None, db_path=None):
        super().__init__(parent)
        self.title("Brightloop Software - Reporting Module (Member 4)")
        self.geometry("1200x800")
        self.minsize(950, 650)
        ReportsFrame(self, db_path)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Brightloop Software - Reports Module (Member 4)")
    root.geometry("1220x820")
    root.minsize(1000, 650)
    app = ReportsFrame(root)
    root.mainloop()
