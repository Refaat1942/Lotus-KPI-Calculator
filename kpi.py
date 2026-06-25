# kpi_calculator.py
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import json
import os
import sqlite3
from datetime import datetime
from PIL import Image
from tkcalendar import DateEntry
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_LIB = True
except ImportError:
    ARABIC_LIB = False

def fix_arabic(text):
    if not ARABIC_LIB or pd.isna(text): return str(text)
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except:
        return str(text)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

GREEN_PRIMARY = "#27ae60"
GREEN_HOVER = "#2ecc71"
DARK_GREEN = "#1e8449"

DEFAULT_KPI_LOGIC = {
    "REGULAR": {
        "receipts": [{"target": 8, "points": 200}, {"target": 16, "points": 300}, {"target": 24, "points": 400}, {"target": 32, "points": 500}, {"target": 40, "points": 600}],
        "sales": [{"target": 2000, "points": 200}, {"target": 5000, "points": 400}, {"target": 10000, "points": 600}, {"target": 15000, "points": 800}, {"target": 20000, "points": 1000}],
        "avg_receipt": [{"target": 100, "points": 100}, {"target": 200, "points": 200}, {"target": 300, "points": 300}, {"target": 400, "points": 400}, {"target": 500, "points": 500}],
        "units": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}]
    },
    "DELIVERY": {
        "receipts": [{"target": 8, "points": 100}, {"target": 16, "points": 200}, {"target": 24, "points": 300}, {"target": 32, "points": 400}, {"target": 40, "points": 500}],
        "sales": [{"target": 2000, "points": 200}, {"target": 5000, "points": 400}, {"target": 10000, "points": 600}, {"target": 15000, "points": 800}, {"target": 20000, "points": 1000}],
        "avg_receipt": [{"target": 100, "points": 100}, {"target": 200, "points": 200}, {"target": 300, "points": 300}, {"target": 400, "points": 400}, {"target": 500, "points": 500}],
        "units": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}]
    },
    "DIGITAL": {
        "receipts": [{"target": 8, "points": 100}, {"target": 16, "points": 200}, {"target": 24, "points": 300}, {"target": 32, "points": 400}, {"target": 40, "points": 500}],
        "sales": [{"target": 2000, "points": 200}, {"target": 5000, "points": 400}, {"target": 10000, "points": 600}, {"target": 15000, "points": 800}, {"target": 20000, "points": 1000}],
        "avg_receipt": [{"target": 100, "points": 100}, {"target": 200, "points": 200}, {"target": 300, "points": 300}, {"target": 400, "points": 400}, {"target": 500, "points": 500}],
        "units": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}]
    },
    "INSURANCE": {
         "receipts": [{"target": 4, "points": 200}, {"target": 8, "points": 300}, {"target": 12, "points": 400}, {"target": 16, "points": 500}, {"target": 20, "points": 600}],
         "sales": [{"target": 2000, "points": 200}, {"target": 5000, "points": 400}, {"target": 10000, "points": 600}, {"target": 15000, "points": 800}, {"target": 20000, "points": 1000}],
         "avg_receipt": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}],
         "units": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}]
    },
    "EVALUATION": {
         "performance": [{"target": 49, "points": 0}, {"target": 59, "points": 10}, {"target": 64, "points": 20}, {"target": 69, "points": 30}, {"target": 79, "points": 40}, {"target": 89, "points": 50}, {"target": 94, "points": 60}, {"target": 100, "points": 70}],
         "customer_service": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}],
         "knowledge": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}]
    },
    "PUSH_LIST": {
         "quantity": [{"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}, {"target": 0, "points": 0}]
    }
}

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="white")
        
        self.container = tk.Frame(self, bg="white")
        self.container.place(relx=0.5, rely=0.5, anchor="center")

        try:
            img_path = resource_path("logo.png")
            img = Image.open(img_path)
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.lbl_logo = ctk.CTkLabel(self.container, image=self.logo_img, text="", bg_color="white")
            self.lbl_logo.pack(pady=(0, 20))
        except: pass

        self.progress = ctk.CTkProgressBar(self.container, width=400, height=15, progress_color=GREEN_PRIMARY, fg_color="#e0e0e0")
        self.progress.set(0)
        self.progress.pack(pady=20)
        
        ctk.CTkLabel(self.container, text="KPI CALCULATOR SYSTEM", font=("Segoe UI", 18, "bold"), text_color="gray", bg_color="white").pack()
        self.copy_lbl = ctk.CTkLabel(self, text="Copyright Lotus Pharmacies 2026", font=("Segoe UI", 14, "bold"), text_color="#7f8c8d", bg_color="white")
        self.copy_lbl.pack(side="bottom", pady=40)

        self.animate_progress(0)

    def animate_progress(self, val):
        if val <= 1.0:
            self.progress.set(val)
            self.after(40, lambda: self.animate_progress(val + 0.01))

class KPICalculatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        splash = SplashScreen(self)
        self.after(4500, splash.destroy)
        self.after(4500, self.deiconify)
        self.after(4500, lambda: self.state('zoomed')) 

        self.title("Lotus KPI Calculator")
        self.geometry("1350x850")
        
        self.setup_database()
        
        self.raw_df = None
        self.eval_df = None
        self.push_df = None
        self.logic_file = "kpi_logic.json"
        self.kpi_logic = self.load_logic()
        self.all_results = []
        self.comp_results = []
        self.detailed_scores = {}
        self.excluded_stats = {}
        
        self.navbar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=(GREEN_PRIMARY, DARK_GREEN))
        self.navbar.pack(side="top", fill="x")
        ctk.CTkLabel(self.navbar, text="Lotus KPI System 📊", font=("Segoe UI", 26, "bold"), text_color="white").pack(side="left", padx=25, pady=10)
        
        self.theme_switch = ctk.CTkSwitch(self.navbar, text="Dark Mode", text_color="white", font=("Segoe UI", 13, "bold"), command=self.toggle_theme)
        self.theme_switch.select()
        self.theme_switch.pack(side="right", padx=30)
        
        self.tabs = ctk.CTkTabview(self, corner_radius=12)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tab_dashboard = self.tabs.add("1. Upload & Filter")
        self.tab_results = self.tabs.add("2. Overall KPI Results")
        self.tab_detailed = self.tabs.add("3. Detailed Score")
        self.tab_settings = self.tabs.add("4. KPI Logic Settings")
        self.tab_history = self.tabs.add("5. History by Period")
        self.tab_compare = self.tabs.add("6. Compare Periods")
        
        self.setup_dashboard()
        self.setup_results()
        self.setup_detailed()
        self.setup_settings()
        self.setup_history()
        self.setup_compare()
        self.apply_tree_styles()

    def toggle_theme(self):
        is_dark = self.theme_switch.get()
        if is_dark:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Dark Mode")
            if hasattr(self, 'lbl_selected_emp'): self.lbl_selected_emp.configure(bg="#2b2b2b", fg="white")
        else:
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Light Mode")
            if hasattr(self, 'lbl_selected_emp'): self.lbl_selected_emp.configure(bg="#fdfdfd", fg="black")
        self.apply_tree_styles()

    def setup_database(self):
        self.db_conn = sqlite3.connect("kpi_history.db")
        self.db_cursor = self.db_conn.cursor()
        self.db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS kpi_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                start_date TEXT,
                end_date TEXT,
                emp_name TEXT,
                emp_code TEXT,
                branch TEXT,
                shift TEXT,
                working_days REAL DEFAULT 0,
                reg_pts REAL,
                digital_pts REAL,
                delivery_pts REAL,
                insurance_pts REAL,
                eval_pts REAL DEFAULT 0,
                push_pts REAL DEFAULT 0,
                grand_total REAL,
                job_title TEXT
            )
        ''')
        try:
            self.db_cursor.execute("ALTER TABLE kpi_records ADD COLUMN excluded_sales REAL DEFAULT 0")
        except sqlite3.OperationalError: pass
        try:
            self.db_cursor.execute("ALTER TABLE kpi_records ADD COLUMN working_days REAL DEFAULT 0")
            self.db_cursor.execute("ALTER TABLE kpi_records ADD COLUMN eval_pts REAL DEFAULT 0")
            self.db_cursor.execute("ALTER TABLE kpi_records ADD COLUMN push_pts REAL DEFAULT 0")
        except sqlite3.OperationalError: pass
        self.db_conn.commit()

    def load_logic(self):
        loaded = DEFAULT_KPI_LOGIC.copy()
        if os.path.exists(self.logic_file):
            try:
                with open(self.logic_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    for k in loaded.keys():
                        if k in file_data:
                            loaded[k] = file_data[k]
            except: pass
        with open(self.logic_file, 'w', encoding='utf-8') as f:
            json.dump(loaded, f, indent=4)
        return loaded

    def setup_dashboard(self):
        frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        frame.pack(expand=True)
        ctk.CTkLabel(frame, text="Upload Data & Select Date Range", font=("Segoe UI", 24, "bold")).pack(pady=(0,25))
        self.btn_load = ctk.CTkButton(frame, text="📥 Load Main Excel/CSV", font=("Segoe UI", 18, "bold"), height=55, width=350, command=self.load_file)
        self.btn_load.pack(pady=10)
        
        self.enable_eval_var = ctk.BooleanVar(value=False)
        self.enable_push_var = ctk.BooleanVar(value=False)

        switches_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switches_frame.pack(pady=10)
        
        self.chk_eval = ctk.CTkSwitch(switches_frame, text="Enable Evaluation", variable=self.enable_eval_var, command=self.toggle_extras, font=("Segoe UI", 15, "bold"))
        self.chk_eval.pack(side="left", padx=15)
        
        self.chk_push = ctk.CTkSwitch(switches_frame, text="Enable Push List", variable=self.enable_push_var, command=self.toggle_extras, font=("Segoe UI", 15, "bold"))
        self.chk_push.pack(side="left", padx=15)

        self.extras_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.btn_load_eval = ctk.CTkButton(self.extras_frame, text="📁 Load Eval Sheet", font=("Segoe UI", 12), command=self.load_eval)
        self.btn_load_push = ctk.CTkButton(self.extras_frame, text="📁 Load Push List", font=("Segoe UI", 12), command=self.load_push)
        self.btn_download_temp = ctk.CTkButton(self.extras_frame, text="📥 Download Templates", font=("Segoe UI", 12), fg_color="#8e44ad", hover_color="#9b59b6", command=self.download_templates)
        
        date_frame = ctk.CTkFrame(frame, fg_color=("gray90", "gray20"), corner_radius=12)
        date_frame.pack(pady=25, padx=20, fill="x")
        ctk.CTkLabel(date_frame, text="Filter by Date Range (Calendar)", font=("Segoe UI", 17, "bold"), text_color=GREEN_PRIMARY).pack(pady=15)
        
        row_dates = ctk.CTkFrame(date_frame, fg_color="transparent")
        row_dates.pack(pady=10)
        ctk.CTkLabel(row_dates, text="From:", font=("Segoe UI", 15, "bold")).pack(side="left", padx=10)
        self.entry_date_from = DateEntry(row_dates, width=15, font=("Segoe UI", 13), background=GREEN_PRIMARY, foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.entry_date_from.pack(side="left", padx=10)
        ctk.CTkLabel(row_dates, text="To:", font=("Segoe UI", 15, "bold")).pack(side="left", padx=10)
        self.entry_date_to = DateEntry(row_dates, width=15, font=("Segoe UI", 13), background=GREEN_PRIMARY, foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.entry_date_to.pack(side="left", padx=10)
        
        self.btn_calc = ctk.CTkButton(frame, text="⚙️ Calculate & Save KPI", font=("Segoe UI", 18, "bold"), fg_color="#3498db", hover_color="#2980b9", height=55, width=350, command=self.process_data)
        self.btn_calc.pack(pady=25)
        self.status_lbl = ctk.CTkLabel(frame, text="Waiting for data...", text_color="gray", font=("Segoe UI", 15))
        self.status_lbl.pack(pady=10)

    def toggle_extras(self):
        for w in self.extras_frame.winfo_children(): w.pack_forget()
        
        show_frame = False
        if self.enable_eval_var.get():
            self.btn_load_eval.pack(side="left", padx=5)
            show_frame = True
        if self.enable_push_var.get():
            self.btn_load_push.pack(side="left", padx=5)
            show_frame = True
            
        if show_frame:
            self.btn_download_temp.pack(side="left", padx=5)
            self.extras_frame.pack(pady=5)
        else:
            self.extras_frame.pack_forget()

    def download_templates(self):
        folder = filedialog.askdirectory(title="Select Folder to Save Templates")
        if folder:
            try:
                pd.DataFrame(columns=["Emp Code", "Emp Name", "Branch", "Performance", "Customer Service", "Knowledge"]).to_excel(os.path.join(folder, "Evaluation_Template.xlsx"), index=False)
                pd.DataFrame(columns=["Emp Code", "Item Code", "Item Name", "Quantity Dimenions"]).to_excel(os.path.join(folder, "PushList_Template.xlsx"), index=False)
                messagebox.showinfo("Success", "Templates saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def load_eval(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")])
        if path:
            try:
                self.eval_df = pd.read_excel(path) if path.endswith('.xlsx') or path.endswith('.xls') else pd.read_csv(path)
                messagebox.showinfo("Success", "Evaluation data loaded!")
            except Exception as e: messagebox.showerror("Error", str(e))

    def load_push(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")])
        if path:
            try:
                self.push_df = pd.read_excel(path) if path.endswith('.xlsx') or path.endswith('.xls') else pd.read_csv(path)
                messagebox.showinfo("Success", "Push List data loaded!")
            except Exception as e: messagebox.showerror("Error", str(e))

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV", "*.csv")])
        if not file_path: return
        try:
            self.status_lbl.configure(text="Reading file...")
            self.update()
            if file_path.endswith('.csv'):
                try: self.raw_df = pd.read_csv(file_path, encoding='utf-8-sig')
                except UnicodeDecodeError: self.raw_df = pd.read_csv(file_path, encoding='windows-1256')
            else: self.raw_df = pd.read_excel(file_path)
            
            def find_col(df, possible_names):
                for name in possible_names:
                    if name in df.columns: return name
                return None
            
            col_date = find_col(self.raw_df, ["Date", "التاريخ"])
            if col_date:
                self.raw_df[col_date] = pd.to_datetime(self.raw_df[col_date], errors='coerce')
                valid_dates = self.raw_df[col_date].dropna()
                if not valid_dates.empty:
                    self.entry_date_from.set_date(valid_dates.min())
                    self.entry_date_to.set_date(valid_dates.max())
            self.status_lbl.configure(text=f"✅ Data loaded successfully!")
        except Exception as e: messagebox.showerror("Error", str(e))

    def apply_tree_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if is_dark else "#fdfdfd"
        fg = "white" if is_dark else "black"
        head_bg = "#1e8449"
        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, rowheight=40, font=("Segoe UI", 12))
        style.map('Treeview', background=[('selected', GREEN_PRIMARY)])
        style.configure("Treeview.Heading", font=("Segoe UI", 13, "bold"), background=head_bg, foreground="white")

    def auto_fit_columns(self, tree):
        for col in tree["columns"]:
            tree.column(col, stretch=False)
            max_width = len(str(col)) * 10
            for item in tree.get_children():
                vals = tree.item(item, "values")
                if vals:
                    val = vals[tree["columns"].index(col)]
                    val_len = len(str(val)) * 9
                    if val_len > max_width: max_width = val_len
            final_width = max(max_width + 40, 100)
            tree.column(col, width=final_width, minwidth=final_width)

    def treeview_sort_column(self, tv, col, reverse):
        items = [(tv.set(k, col), k) for k in tv.get_children('') if 'green_line' not in tv.item(k, 'tags') and 'summary_value' not in tv.item(k, 'tags') and 'reward_value' not in tv.item(k, 'tags') and 'excluded_value' not in tv.item(k, 'tags') and 'separator' not in tv.item(k, 'tags') and 'excluded_green_line' not in tv.item(k, 'tags')]
        def try_float(v):
            try: return float(str(v).replace('%', '').replace(',', '').strip())
            except: return str(v).lower()
        items.sort(key=lambda t: try_float(t[0]), reverse=reverse)
        for index, (val, k) in enumerate(items): tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def setup_results(self):
        top_frame = ctk.CTkFrame(self.tab_results, fg_color="transparent")
        top_frame.pack(fill="x", pady=10, padx=10)
        search_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        search_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(search_frame, text="🔍 Search:", font=("Segoe UI", 13, "bold")).pack(side="left", padx=5)
        
        self.search_entry_overall = ctk.CTkEntry(search_frame, width=150, font=("Segoe UI", 13))
        self.search_entry_overall.pack(side="left", padx=5)
        self.search_entry_overall.bind("<KeyRelease>", self.filter_overall_results)
        
        self.branch_filter = ctk.CTkComboBox(search_frame, values=["All Branches"], width=150, command=self.filter_overall_results)
        self.branch_filter.pack(side="left", padx=5)
        
        self.job_filter_overall = ctk.CTkComboBox(search_frame, values=["All Jobs"], width=150, command=self.filter_overall_results)
        self.job_filter_overall.pack(side="left", padx=5)
        
        self.shift_filter = ctk.CTkComboBox(search_frame, values=["All Shifts", "Morning Shift", "Evening Shift", "Night Shift"], width=130, command=self.filter_overall_results)
        self.shift_filter.pack(side="left", padx=5)
        
        self.chk_unknown_var = ctk.BooleanVar(value=True)
        self.chk_unknown = ctk.CTkCheckBox(search_frame, text="Include Unknown Jobs", variable=self.chk_unknown_var, command=self.filter_overall_results)
        self.chk_unknown.pack(side="left", padx=15)

        ctk.CTkButton(top_frame, text="Export Excel 📊", font=("Segoe UI", 15, "bold"), fg_color=GREEN_PRIMARY, height=40, command=lambda: self.export_excel(self.tree)).pack(side="right")
        
        self.tree_frame = ctk.CTkFrame(self.tab_results)
        self.tree_frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(self.tree_frame)
        scroll_y = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y"); scroll_x.pack(side="bottom", fill="x"); self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Delete>", self.delete_unknown_row)
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Delete Unknown Employee", command=lambda: self.delete_unknown_row(None))
        self.tree.bind("<Button-3>", lambda e: self.context_menu.post(e.x_root, e.y_root))

    def setup_history(self):
        top_frame = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        top_frame.pack(fill="x", pady=10, padx=10)
        
        db_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        db_frame.pack(side="left")
        ctk.CTkLabel(db_frame, text="📊 Results History (DB)", font=("Segoe UI", 15, "bold"), text_color=GREEN_PRIMARY).pack(side="left", padx=5)
        ctk.CTkButton(db_frame, text="🔄 Refresh", font=("Segoe UI", 12, "bold"), width=80, fg_color="#3498db", command=self.load_history_summary).pack(side="left", padx=5)
        
        cache_frame = ctk.CTkFrame(top_frame, fg_color=("gray90", "gray20"), corner_radius=8)
        cache_frame.pack(side="right", padx=5, ipady=5)
        ctk.CTkLabel(cache_frame, text="📁 Saved Datasets:", font=("Segoe UI", 13, "bold")).pack(side="left", padx=10)
        self.dataset_combo = ctk.CTkComboBox(cache_frame, width=250, values=["No saved datasets"])
        self.dataset_combo.pack(side="left", padx=5)
        ctk.CTkButton(cache_frame, text="⚡ Calculate KPI", font=("Segoe UI", 13, "bold"), width=100, fg_color="#e67e22", hover_color="#d35400", command=self.recalc_dataset).pack(side="left", padx=10)
        
        self.refresh_dataset_combo()

        self.history_summary_frame = ctk.CTkFrame(self.tab_history)
        self.history_summary_frame.pack(fill="both", expand=True, pady=5)
        self.history_summary_tree = ttk.Treeview(self.history_summary_frame)
        scroll_y = ttk.Scrollbar(self.history_summary_frame, orient="vertical", command=self.history_summary_tree.yview)
        self.history_summary_tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y"); self.history_summary_tree.pack(fill="both", expand=True)
        cols = ["Saved Timestamp", "Period", "Total Pharmacists Calculated"]
        self.history_summary_tree["columns"] = cols
        self.history_summary_tree["show"] = "headings"
        for c in cols: 
            self.history_summary_tree.heading(c, text=c, command=lambda _c=c: self.treeview_sort_column(self.history_summary_tree, _c, False))
        self.history_summary_tree.bind("<Double-1>", self.on_history_double_click)
        self.load_history_summary()

    def get_saved_datasets(self):
        try:
            os.makedirs("data_cache", exist_ok=True)
            files = [f for f in os.listdir("data_cache") if f.endswith(".pkl")]
            self.dataset_mapping = {}
            display_list = []
            files.sort(key=lambda x: os.path.getmtime(os.path.join("data_cache", x)), reverse=True)
            for f in files:
                parts = f.replace(".pkl", "").split("_")
                try: display_name = f"Period: {parts[0]} ➡ {parts[1]} (Saved: {parts[2]})"
                except: display_name = f
                display_list.append(display_name)
                self.dataset_mapping[display_name] = os.path.join("data_cache", f)
            return display_list if display_list else ["No saved datasets"]
        except: return ["No saved datasets"]

    def refresh_dataset_combo(self):
        if hasattr(self, 'dataset_combo'):
            vals = self.get_saved_datasets()
            self.dataset_combo.configure(values=vals)
            if vals and vals[0] != "No saved datasets":
                self.dataset_combo.set(vals[0])

    def recalc_dataset(self):
        sel = self.dataset_combo.get()
        if sel == "No saved datasets" or sel not in getattr(self, 'dataset_mapping', {}):
            messagebox.showwarning("Warning", "No valid dataset selected.")
            return
            
        filepath = self.dataset_mapping[sel]
        try:
            self.raw_df = pd.read_pickle(filepath)
            def find_col(df, possible_names):
                for name in possible_names:
                    if name in df.columns: return name
                return None
            col_date = find_col(self.raw_df, ["Date", "التاريخ"])
            if col_date:
                valid_dates = pd.to_datetime(self.raw_df[col_date], errors='coerce').dropna()
                if not valid_dates.empty:
                    self.entry_date_from.set_date(valid_dates.min())
                    self.entry_date_to.set_date(valid_dates.max())
            
            self.process_data(save_cache=False)
            self.status_lbl.configure(text="✅ Dataset Recalculated Successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load dataset: {str(e)}")

    def load_history_summary(self):
        query = """SELECT datetime(saved_at, 'localtime'), start_date || ' to ' || end_date, COUNT(id) FROM kpi_records GROUP BY saved_at, start_date, end_date ORDER BY saved_at DESC"""
        try:
            self.db_cursor.execute(query)
            for item in self.history_summary_tree.get_children(): self.history_summary_tree.delete(item)
            for row in self.db_cursor.fetchall(): self.history_summary_tree.insert("", "end", values=row)
            self.auto_fit_columns(self.history_summary_tree)
        except: pass

    def on_history_double_click(self, event):
        selected = self.history_summary_tree.selection()
        if not selected: return
        saved_timestamp = self.history_summary_tree.item(selected[0])['values'][0]
        detail_win = tk.Toplevel(self)
        detail_win.title(f"Period Details: {saved_timestamp}")
        detail_win.geometry("1300x600")
        detail_win.configure(bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#fdfdfd")
        top_frame = ctk.CTkFrame(detail_win, fg_color="transparent")
        top_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(top_frame, text=f"Data for calculation run on: {saved_timestamp}", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        query = "SELECT emp_name, emp_code, job_title, branch, shift, working_days, reg_pts, delivery_pts, digital_pts, insurance_pts, eval_pts, push_pts, grand_total FROM kpi_records WHERE datetime(saved_at, 'localtime') = ?"
        self.db_cursor.execute(query, (saved_timestamp,))
        rows = self.db_cursor.fetchall()
        cols = ["Name", "Code", "Job Title", "Branch", "Main Shift", "Working Days", "REGULAR", "DELIVERY", "DIGITAL", "INSURANCE", "EVALUATION", "PUSH LIST", "TOTAL SCORE"]
        
        # Format the numbers to remove .0
        formatted_rows = []
        for r in rows:
            fmt_r = list(r)
            for i in range(5, 13):
                if fmt_r[i] is not None:
                    try:
                        fmt_r[i] = f"{float(fmt_r[i]):.0f}"
                    except:
                        pass
            formatted_rows.append(fmt_r)

        def export_this():
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Archived_KPI_{saved_timestamp.replace(':', '-')}.xlsx")
            if path:
                pd.DataFrame(formatted_rows, columns=cols).to_excel(path, index=False, engine='openpyxl')
                messagebox.showinfo("Success", "Exported Successfully!")
                
        ctk.CTkButton(top_frame, text="📥 Export Detailed Excel", font=("Segoe UI", 14, "bold"), fg_color=GREEN_PRIMARY, command=export_this).pack(side="right")
        tree_frame = ctk.CTkFrame(detail_win); tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        detail_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=detail_tree.yview); scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=detail_tree.xview)
        detail_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y"); scroll_x.pack(side="bottom", fill="x"); detail_tree.pack(fill="both", expand=True)
        for c in cols: 
            detail_tree.heading(c, text=c, command=lambda _c=c: self.treeview_sort_column(detail_tree, _c, False))
        for r in formatted_rows: detail_tree.insert("", "end", values=r)
        self.auto_fit_columns(detail_tree)

    def save_results_to_db(self, start_date, end_date):
        for r in self.all_results:
            self.db_cursor.execute('''INSERT INTO kpi_records (start_date, end_date, emp_name, emp_code, job_title, branch, shift, working_days, reg_pts, delivery_pts, digital_pts, insurance_pts, eval_pts, push_pts, grand_total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                   (start_date, end_date, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12]))
        self.db_conn.commit()

    def translate_position(self, pos_name):
        if pd.isna(pos_name): return "Unknown"
        pos_str = str(pos_name).strip()
        if 'مساعد صيدلي' in pos_str: return 'Pharmacy Assistant'
        if 'صيدلي' in pos_str: return 'Pharmacist'
        if 'مدير فتر' in pos_str or 'shift manager' in pos_str.lower(): return 'Shift Manager'
        if 'مدير' in pos_str or 'branch manager' in pos_str.lower(): return 'Branch Manager'
        if 'كاشير' in pos_str: return 'Cashier'
        if 'تجميل' in pos_str: return 'Cosmetics Specialist'
        if 'دليفري' in pos_str or 'delivery' in pos_str.lower(): return 'Delivery'
        if 'عامل' in pos_str: return 'Worker'
        if 'محاسب' in pos_str: return 'Accountant'
        return pos_str

    def classify_shift(self, time_val):
        try:
            val = str(time_val).strip()
            h = int(val.split(':')[0]) if ':' in val else int(float(time_val))
            if 0 <= h < 8: return 'Night Shift'
            elif 8 <= h < 16: return 'Morning Shift'
            else: return 'Evening Shift'
        except: return 'Random'

    def process_data(self, save_cache=True):
        if self.raw_df is None: return messagebox.showwarning("Warning", "Load data first.")
        
        if self.enable_eval_var.get() and (self.eval_df is None or self.eval_df.empty):
            return messagebox.showwarning("Validation Error", "لقد قمت بتفعيل التقييم (Evaluation).\nيرجى رفع شيت التقييم أولاً، أو إلغاء التفعيل قبل الحساب.")
            
        if self.enable_push_var.get() and (self.push_df is None or self.push_df.empty):
            return messagebox.showwarning("Validation Error", "لقد قمت بتفعيل (Push List).\nيرجى رفع شيت البوش ليست أولاً، أو إلغاء التفعيل قبل الحساب.")

        def find_col(df, possible_names):
            for name in possible_names:
                if name in df.columns: return name
            return None
        try:
            df = self.raw_df.copy()
            col_date = find_col(df, ["Date", "التاريخ"])
            col_name = find_col(df, ["Full Name", "Employee Name", "Name", "Salespers."])
            col_code = find_col(df, ["Salespers.", "Code", "كود الموظف"])
            col_job  = find_col(df, ["Position Name", "الوظيفة", "Job Title", "Position", "المسمى الوظيفي", "Role"]) 
            col_branch = find_col(df, ["Branch Name", "Branch", "الفرع"])
            col_rec = find_col(df, ["Reciept.No", "Receipt Number", "Trans.", "Invoice"])
            col_price = find_col(df, ["Sales Price", "Gross Sales", "Net Sales", "Price"])
            col_qty = find_col(df, ["Quantity Dimenions", "Quantity", "Qty"])
            col_group = "Z Customer Group"
            col_pos = find_col(df, ["POS no.", "POS", "Terminal", "نقطة البيع", "رقم الكاشير"])
            col_mat_desc = find_col(df, ["Material Description", "Material Desc", "Item Name", "Description"])
            
            if col_group not in df.columns: return messagebox.showerror("Error", "Column 'Z Customer Group' is missing.")
            if not all([col_name, col_rec, col_price]): return messagebox.showerror("Error", "Critical columns missing.")

            if col_job: df['Translated_Position'] = df[col_job].apply(self.translate_position)
            else: df['Translated_Position'] = "Unknown"
            
            start_date = pd.to_datetime(self.entry_date_from.get_date()); end_date = pd.to_datetime(self.entry_date_to.get_date())
            if col_date: df = df[(pd.to_datetime(df[col_date]) >= start_date) & (pd.to_datetime(df[col_date]) <= end_date)]
            
            df[col_price] = pd.to_numeric(df[col_price].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df[col_qty] = pd.to_numeric(df[col_qty].astype(str).str.replace(',', ''), errors='coerce').fillna(1)
            
            col_hour = find_col(df, ["Hour of sale", "Time"])
            if col_hour: df['Shift_Calculated'] = df[col_hour].apply(self.classify_shift)
            else: df['Shift_Calculated'] = "Random"
            
            cols_to_join = [col_rec]
            if col_branch: cols_to_join.append(col_branch)
            if col_pos: cols_to_join.append(col_pos)
            
            if col_date:
                df['Temp_Date_Str'] = pd.to_datetime(df[col_date], errors='coerce').dt.strftime('%Y-%m-%d')
                cols_to_join.append('Temp_Date_Str')

            df['True_Receipt_ID'] = df[cols_to_join].astype(str).agg('_'.join, axis=1)

            df[col_group] = df[col_group].fillna("REGULAR").astype(str).str.upper()
            cond_normal_del = df[col_group].str.contains("NORMAL DELIVERY", case=False, na=False)
            
            if col_mat_desc:
                is_real_item = ~df[col_mat_desc].astype(str).str.contains("DELIVERY FEES", case=False, na=False)
                receipts_with_items = df.loc[is_real_item, 'True_Receipt_ID'].unique()
                cond_exclude = cond_normal_del & (~df['True_Receipt_ID'].isin(receipts_with_items))
            else:
                cond_exclude = cond_normal_del
                
            excluded_df = df[cond_exclude].copy()
            
            excluded_sales_dict = {}
            excluded_count_dict = {}
            if col_price and col_name and not excluded_df.empty:
                excluded_sales_dict = excluded_df.groupby(col_name)[col_price].sum().to_dict()
                excluded_count_dict = excluded_df.groupby(col_name)['True_Receipt_ID'].nunique().to_dict()

            df = df[~cond_exclude]
            
            self.calculate_kpi(df, col_name, col_code, col_branch, 'True_Receipt_ID', col_price, col_qty, col_group, excluded_sales_dict, excluded_count_dict)
            
            str_start, str_end = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            self.save_results_to_db(str_start, str_end); self.load_history_summary()
            
            if save_cache:
                os.makedirs("data_cache", exist_ok=True)
                timestamp = datetime.now().strftime('%y%m%d-%H%M')
                cache_filename = f"{str_start}_{str_end}_{timestamp}.pkl"
                try:
                    self.raw_df.to_pickle(os.path.join("data_cache", cache_filename))
                    self.refresh_dataset_combo()
                except: pass
                
            self.tabs.set("2. Overall KPI Results"); self.status_lbl.configure(text=f"✅ Calculated and Archived.")
        except Exception as e: messagebox.showerror("Error", str(e))

    def calculate_kpi(self, df, col_name, col_code, col_branch, col_rec, col_price, col_qty, col_group, excluded_sales_dict, excluded_count_dict):
        self.all_results.clear(); self.detailed_scores.clear(); self.excluded_stats.clear()
        unique_branches = set(); unique_jobs = set()
        pharmacists = df[col_name].dropna().unique()
        for pharm in pharmacists:
            p_data = df[df[col_name] == pharm]
            raw_code = p_data[col_code].iloc[0] if col_code else None
            code = str(int(float(raw_code))) if pd.notnull(raw_code) else "N/A"
            job_title = str(p_data['Translated_Position'].iloc[0]) if 'Translated_Position' in p_data.columns else "Unknown"
            unique_jobs.add(job_title)
            branch = str(p_data[col_branch].iloc[0]) if col_branch else "N/A"; unique_branches.add(branch)
            try:
                emp_shifts = p_data['Shift_Calculated'].mode()
                shift = emp_shifts[0] if not emp_shifts.empty else "Random"
            except: shift = "Random"
            
            if 'Temp_Date_Str' in p_data.columns:
                pharm_working_days = p_data['Temp_Date_Str'].nunique()
            else:
                pharm_working_days = 1
            if pharm_working_days <= 0: pharm_working_days = 1

            ordered_types = [("DELIVERY", "DELIVERY"), ("DIGITAL", "DIGITAL|MARKET"), ("INSURANCE", "INSURANCE")]
            pts_dict = {"DELIVERY": 0, "DIGITAL": 0, "INSURANCE": 0}
            details_accum = []
            
            reg_res = self.calc_cat_detailed(p_data[~p_data[col_group].str.contains("DELIVERY|DIGITAL|MARKET|INSURANCE", na=False)], "REGULAR", col_rec, col_price, col_qty, pharm_working_days)
            
            for k, pattern in ordered_types:
                sub_res = self.calc_cat_detailed(p_data[p_data[col_group].str.contains(pattern, na=False)], k, col_rec, col_price, col_qty, pharm_working_days)
                pts_dict[k] = sub_res["Pts"]
                details_accum.extend(sub_res["Details"])
                
            eval_pts = 0
            push_pts = 0
            details_eval = []
            
            if self.enable_eval_var.get():
                perf, cs, knw = 0, 0, 0
                if self.eval_df is not None and not self.eval_df.empty:
                    e_row = self.eval_df[self.eval_df['Emp Code'].astype(str) == str(code)]
                    if e_row.empty:
                        e_row = self.eval_df[self.eval_df['Emp Name'].astype(str) == str(pharm)]
                    if not e_row.empty:
                        perf = pd.to_numeric(e_row['Performance'].iloc[0], errors='coerce')
                        cs = pd.to_numeric(e_row['Customer Service'].iloc[0], errors='coerce')
                        knw = pd.to_numeric(e_row['Knowledge'].iloc[0], errors='coerce')
                        perf = 0 if pd.isna(perf) else perf
                        cs = 0 if pd.isna(cs) else cs
                        knw = 0 if pd.isna(knw) else knw

                logic_e = self.kpi_logic.get("EVALUATION", {})
                p_pts = self.get_points_from_tiers(perf, logic_e.get("performance", []))
                c_pts = self.get_points_from_tiers(cs, logic_e.get("customer_service", []))
                k_pts = self.get_points_from_tiers(knw, logic_e.get("knowledge", []))
                
                eval_pts = p_pts + c_pts + k_pts

                details_eval.extend([
                    ("EVALUATION", "Performance", f"{perf:.0f}", "", f"{p_pts:.0f}"),
                    ("EVALUATION", "Customer Service", f"{cs:.0f}", "", f"{c_pts:.0f}"),
                    ("EVALUATION", "Knowledge", f"{knw:.0f}", "", f"{k_pts:.0f}"),
                    ("EVALUATION", "Working Days", f"{pharm_working_days:.0f}", "", "0")
                ])

            if self.enable_push_var.get():
                push_qty = 0
                if self.push_df is not None and not self.push_df.empty:
                    p_rows = self.push_df[self.push_df['Emp Code'].astype(str) == str(code)]
                    if not p_rows.empty:
                        push_qty = pd.to_numeric(p_rows['Quantity Dimenions'], errors='coerce').sum()
                
                logic_p = self.kpi_logic.get("PUSH_LIST", {})
                pu_pts = self.get_points_from_tiers(push_qty, logic_p.get("quantity", []))
                push_pts = pu_pts

                details_eval.append(("EVALUATION", "Push List", f"{push_qty:.0f}", "", f"{pu_pts:.0f}"))

            details_accum.extend(details_eval)
            grand_total = reg_res["Pts"] + sum(pts_dict.values()) + eval_pts + push_pts
            
            ex_sales = excluded_sales_dict.get(pharm, 0.0)
            ex_count = excluded_count_dict.get(pharm, 0)
            self.excluded_stats[str(pharm)] = {"sales": ex_sales, "count": ex_count}
            
            # Use .0f to ensure no decimal values are shown
            row = [str(pharm), code, job_title, branch, shift, 
                   f"{pharm_working_days:.0f}", 
                   f"{reg_res['Pts']:.0f}", f"{pts_dict['DELIVERY']:.0f}", 
                   f"{pts_dict['DIGITAL']:.0f}", f"{pts_dict['INSURANCE']:.0f}", 
                   f"{eval_pts:.0f}", f"{push_pts:.0f}", f"{grand_total:.0f}"]
            self.all_results.append(row)
            
            self.detailed_scores[str(pharm)] = reg_res["Details"] + details_accum

        self.all_results.sort(key=lambda x: float(x[-1]) if x[-1].replace('.','',1).isdigit() else 0, reverse=True)
        sorted_branches = ["All Branches"] + sorted(list(unique_branches)); sorted_jobs = ["All Jobs"] + sorted(list(unique_jobs))
        
        self.branch_filter.configure(values=[fix_arabic(b) for b in sorted_branches])
        self.job_filter_overall.configure(values=[fix_arabic(j) for j in sorted_jobs])
        self.branch_filter_detailed.configure(values=[fix_arabic(b) for b in sorted_branches])
        self.job_filter_detailed.configure(values=[fix_arabic(j) for j in sorted_jobs])
        if hasattr(self, 'branch_filter_comp'):
            self.branch_filter_comp.configure(values=[fix_arabic(b) for b in sorted_branches])
            self.job_filter_comp.configure(values=[fix_arabic(j) for j in sorted_jobs])
        
        self.branch_filter.set(fix_arabic("All Branches"))
        self.job_filter_overall.set(fix_arabic("All Jobs"))
        self.branch_filter_detailed.set(fix_arabic("All Branches"))
        self.job_filter_detailed.set(fix_arabic("All Jobs"))
        
        cols_main = ["Employee Name", "Code", "Job Title", "Branch", "Main Shift", "Working Days", "REGULAR", "DELIVERY", "DIGITAL", "INSURANCE", "EVALUATION", "PUSH LIST", "TOTAL SCORE"]
        self.tree["columns"] = cols_main; self.tree["show"] = "headings"
        
        for c in cols_main: 
            self.tree.heading(c, text=c, command=lambda _c=c: self.treeview_sort_column(self.tree, _c, False))
            if c in ["Employee Name", "Job Title", "Branch", "Main Shift"]:
                self.tree.column(c, anchor="w")
            else:
                self.tree.column(c, anchor="center")
            
        self.filter_overall_results(); self.update_suggestions()

    def get_points_from_tiers(self, value, tiers):
        if value < 0: return 0 
        valid_tiers = [t for t in sorted(tiers, key=lambda x: x['target'])]
        if not valid_tiers: return 0
        for t in valid_tiers:
            if value <= t['target']: return t['points']
        return valid_tiers[-1]['points']

    def calc_cat_detailed(self, data, cat_key, col_rec, col_price, col_qty, days):
        if data.empty:
            sales, recs, units = 0, 0, 0
            d_sales, d_recs, avg_rec, units_per_rec = 0, 0, 0, 0
        else:
            sales = data[col_price].sum()
            recs = data[col_rec].nunique()
            units = data[col_qty].sum()
            d_sales = sales / days
            d_recs = recs / days
            avg_rec = sales / recs if recs > 0 else 0
            units_per_rec = units / recs if recs > 0 else 0
            
        logic = self.kpi_logic.get(cat_key, {})
        pts_recs = self.get_points_from_tiers(d_recs, logic.get("receipts", []))
        pts_sales = self.get_points_from_tiers(d_sales, logic.get("sales", []))
        pts_avg = self.get_points_from_tiers(avg_rec, logic.get("avg_receipt", []))
        pts_units = self.get_points_from_tiers(units_per_rec, logic.get("units", []))
        total_pts = pts_recs + pts_sales + pts_avg + pts_units
        
        # Remove trailing .0 via formatting and rstrip
        details = [(cat_key, "Receipts", f"{recs:.0f}", f"{d_recs:.2f}".rstrip('0').rstrip('.'), f"{pts_recs:.0f}"), 
                   (cat_key, "Sales", f"{sales:,.0f}", f"{d_sales:,.0f}", f"{pts_sales:.0f}"), 
                   (cat_key, "Avg Rec", f"{avg_rec:,.0f}", f"{avg_rec:,.0f}", f"{pts_avg:.0f}"), 
                   (cat_key, "Units", f"{units:.0f}", f"{units_per_rec:.2f}".rstrip('0').rstrip('.'), f"{pts_units:.0f}")]
        return {"Pts": total_pts, "Details": details}

    def filter_overall_results(self, event=None):
        q = self.search_entry_overall.get().lower()
        b_filter = self.branch_filter.get()
        j_filter = self.job_filter_overall.get()
        s_filter = self.shift_filter.get()
        include_unknown = self.chk_unknown_var.get()
        
        for item in self.tree.get_children(): self.tree.delete(item)
        for r in self.all_results:
            job = str(r[2])
            if not include_unknown and job == "Unknown": continue
            
            if (q in str(r[0]).lower() or q in str(r[1]).lower()) and \
               (b_filter == fix_arabic("All Branches") or b_filter == fix_arabic(str(r[3]))) and \
               (j_filter == fix_arabic("All Jobs") or j_filter == fix_arabic(job)) and \
               (s_filter == fix_arabic("All Shifts") or s_filter == fix_arabic(str(r[4]))):
                self.tree.insert("", "end", values=r)
        self.auto_fit_columns(self.tree)

    def delete_unknown_row(self, event):
        selected = self.tree.selection()
        if not selected: return
        values = self.tree.item(selected[0], "values")
        if values and values[2] == "Unknown":
            emp_code = values[1]
            self.all_results = [r for r in self.all_results if str(r[1]) != str(emp_code)]
            self.filter_overall_results()
            self.update_suggestions()
        else:
            messagebox.showwarning("Warning", "You can only delete employees with 'Unknown' job titles.")

    def setup_detailed(self):
        container = ctk.CTkFrame(self.tab_detailed, fg_color="transparent"); container.pack(fill="both", expand=True, padx=5, pady=5)
        left_panel = ctk.CTkFrame(container, width=320, corner_radius=12); left_panel.pack(side="left", fill="y", padx=(0, 10))
        ctk.CTkLabel(left_panel, text="🔍 Search & Filter", font=("Segoe UI", 18, "bold"), text_color=GREEN_PRIMARY).pack(pady=(15, 5))
        self.search_var_detailed = tk.StringVar()
        self.search_entry_detailed = ctk.CTkEntry(left_panel, textvariable=self.search_var_detailed, placeholder_text="Name or Code...", font=("Segoe UI", 14), width=270); self.search_entry_detailed.pack(pady=5, padx=15); self.search_entry_detailed.bind("<KeyRelease>", self.update_suggestions)
        self.branch_filter_detailed = ctk.CTkComboBox(left_panel, values=[fix_arabic("All Branches")], width=270, command=self.update_suggestions); self.branch_filter_detailed.pack(pady=5, padx=15)
        self.job_filter_detailed = ctk.CTkComboBox(left_panel, values=[fix_arabic("All Jobs")], width=270, command=self.update_suggestions); self.job_filter_detailed.pack(pady=5, padx=15)
        self.suggest_listbox = tk.Listbox(left_panel, font=("Segoe UI", 13), bg="#2b2b2b", fg="white", selectbackground=GREEN_PRIMARY); self.suggest_listbox.pack(fill="both", expand=True, padx=15, pady=10); self.suggest_listbox.bind("<<ListboxSelect>>", self.on_select_employee)
        right_panel = ctk.CTkFrame(container); right_panel.pack(side="right", fill="both", expand=True)
        
        self.lbl_selected_emp = tk.Label(right_panel, text="👤 Select from list", font=("Segoe UI", 20, "bold"), bg="#2b2b2b", fg="white")
        self.lbl_selected_emp.pack(pady=10)
        
        self.detail_tree = ttk.Treeview(right_panel)
        self.detail_tree["columns"] = ["Category", "Metric", "Avg/Month", "Avg/Day", "Reward", "Excluded"]
        self.detail_tree["show"] = "headings"
        
        for c in self.detail_tree["columns"]:
            self.detail_tree.heading(c, text=c)
            self.detail_tree.column(c, anchor="center")
                
        self.detail_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def update_suggestions(self, event=None):
        st, b_filter, j_filter = self.search_var_detailed.get().lower(), self.branch_filter_detailed.get(), self.job_filter_detailed.get()
        self.suggest_listbox.delete(0, tk.END)
        for r in self.all_results:
            name, code, job, branch = str(r[0]).lower(), str(r[1]).lower(), str(r[2]), str(r[3])
            if (st in name or st in code) and (b_filter == fix_arabic("All Branches") or b_filter == fix_arabic(branch)) and (j_filter == fix_arabic("All Jobs") or j_filter == fix_arabic(job)):
                self.suggest_listbox.insert(tk.END, f"{fix_arabic(r[0])} ({r[1]})")

    def on_select_employee(self, event):
        sel = self.suggest_listbox.curselection()
        if not sel: return
        selected_text = self.suggest_listbox.get(sel[0])
        try: code_str = selected_text.split("(")[-1].replace(")", "").strip()
        except: return
        emp_info = next((r for r in self.all_results if str(r[1]) == code_str), None)
        if emp_info:
            emp_name, job, branch = emp_info[0], emp_info[2], emp_info[3]
            self.lbl_selected_emp.configure(text=f"👤 {emp_name}  |  {job}  |  {branch}")
            
            for item in self.detail_tree.get_children(): self.detail_tree.delete(item)
            
            ex_sales = self.excluded_stats.get(emp_name, {}).get("sales", 0.0)
            ex_count = self.excluded_stats.get(emp_name, {}).get("count", 0)

            current_category = None
            total_sales_all = 0.0
            total_recs_all = 0.0
            total_units_all = 0.0
            
            total_daily_sales = 0.0
            total_daily_recs = 0.0
            
            for dr in self.detailed_scores.get(emp_name, []):
                cat = dr[0]
                metric = dr[1]
                
                try:
                    val = float(str(dr[2]).replace(',', ''))
                    if metric == "Sales": total_sales_all += val
                    elif metric == "Receipts": total_recs_all += val
                    elif metric == "Units": total_units_all += val
                    
                    d_val_str = str(dr[3]).replace(',', '').strip()
                    d_val = float(d_val_str)
                    if metric == "Sales": total_daily_sales += d_val
                    elif metric == "Receipts": total_daily_recs += d_val
                except: pass

                if current_category is not None and cat != current_category:
                    self.detail_tree.insert("", "end", values=("---------", "---------", "---------", "---------", "---------", "---------"), tags=('separator',))
                
                current_category = cat
                row_to_insert = list(dr)
                
                if cat == "DELIVERY":
                    if metric == "Sales" and ex_sales > 0:
                        row_to_insert.append(f"{ex_sales:,.0f}")
                    elif metric == "Receipts" and ex_count > 0:
                        row_to_insert.append(f"{ex_count:.0f}")
                    else: row_to_insert.append("")
                else: row_to_insert.append("")
                    
                self.detail_tree.insert("", "end", values=row_to_insert)
            
            total = sum([float(str(r[-1]).replace(',','')) for r in self.detailed_scores.get(emp_name, [])])
            
            total_avg_all = total_sales_all / total_recs_all if total_recs_all > 0 else 0
            total_units_per_rec = total_units_all / total_recs_all if total_recs_all > 0 else 0
            
            self.detail_tree.insert("", "end", values=("---------", "---------", "---------", "---------", "---------", "---------"), tags=('separator',))
            
            self.detail_tree.insert("", "end", values=("Total", "Receipts", f"{total_recs_all:,.0f}", f"{total_daily_recs:.2f}".rstrip('0').rstrip('.'), "", ""), tags=('summary_value',))
            self.detail_tree.insert("", "end", values=("Total", "Sales", f"{total_sales_all:,.0f}", f"{total_daily_sales:,.0f}", "", ""), tags=('summary_value',))
            self.detail_tree.insert("", "end", values=("Total", "Avg Rec", f"{total_avg_all:,.0f}", f"{total_avg_all:,.0f}", "", ""), tags=('summary_value',))
            self.detail_tree.insert("", "end", values=("Total", "Units", f"{total_units_all:,.0f}", f"{total_units_per_rec:.2f}".rstrip('0').rstrip('.'), "", ""), tags=('summary_value',))
            
            self.detail_tree.insert("", "end", values=("", "", "", "", "", ""), tags=('green_line',))
            self.detail_tree.insert("", "end", values=("Total", "Rewards", "", "", f"{total:,.0f}", ""), tags=('reward_value',))
            
            self.detail_tree.insert("", "end", values=("---------", "---------", "---------", "---------", "---------", "---------"), tags=('separator',))

            self.detail_tree.insert("", "end", values=("Excluded", "Receipts", f"{ex_count:.0f}", "", "", ""), tags=('excluded_value',))
            self.detail_tree.insert("", "end", values=("Excluded", "Sales", f"{ex_sales:,.0f}", "", "", ""), tags=('excluded_value',))
            
            self.detail_tree.tag_configure('green_line', background=GREEN_PRIMARY)
            
            is_dark = ctk.get_appearance_mode() == "Dark"
            row_bg = "#2b2b2b" if is_dark else "#fdfdfd"
            row_fg = "white" if is_dark else "black"
            
            self.detail_tree.tag_configure('summary_value', background=row_bg, foreground=row_fg, font=('Segoe UI', 13, 'bold'))
            self.detail_tree.tag_configure('reward_value', background=row_bg, foreground=row_fg, font=('Segoe UI', 14, 'bold'))
            self.detail_tree.tag_configure('excluded_value', background=row_bg, foreground=row_fg, font=('Segoe UI', 12, 'bold'))
            self.detail_tree.tag_configure('separator', foreground='gray') 
            
            self.auto_fit_columns(self.detail_tree)

    def add_tier_row(self, rows_frame, cat_k, met_k, t_val="0", p_val="0", f_val="0"):
        def fmt(v):
            try: return str(int(float(v))) if float(v).is_integer() else str(v)
            except: return str(v)

        row = ctk.CTkFrame(rows_frame, fg_color="transparent")
        row.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(row, text="From", font=("Segoe UI", 10)).pack(side="left")
        fe = ctk.CTkEntry(row, width=50, height=22, font=("Segoe UI", 11))
        fe.insert(0, fmt(f_val)) 
        fe.pack(side="left", padx=2)
        
        ctk.CTkLabel(row, text="To", font=("Segoe UI", 10, "bold")).pack(side="left")
        te = ctk.CTkEntry(row, width=65, height=22, font=("Segoe UI", 11))
        te.insert(0, fmt(t_val))
        te.pack(side="left", padx=2)
        
        ctk.CTkLabel(row, text="➡ Pts:", font=("Segoe UI", 10)).pack(side="left")
        pe = ctk.CTkEntry(row, width=60, height=22, font=("Segoe UI", 11))
        pe.insert(0, fmt(p_val))
        pe.pack(side="left", padx=2)
        
        btn_del = ctk.CTkButton(row, text="❌", width=25, height=22, fg_color="#c0392b", hover_color="#e74c3c", command=lambda r=row, c=cat_k, m=met_k: self.delete_tier_row(r, c, m))
        btn_del.pack(side="left", padx=5)

        field_data = {'target': te, 'points': pe, 'frame': row}
        self.entry_fields[f"{cat_k}_{met_k}"].append(field_data)

    def delete_tier_row(self, row_frame, cat_k, met_k):
        row_frame.destroy()
        self.entry_fields[f"{cat_k}_{met_k}"] = [f for f in self.entry_fields[f"{cat_k}_{met_k}"] if f['frame'] != row_frame]

    def setup_settings(self):
        top_bar = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(top_bar, text="📥 Import Template", font=("Segoe UI", 13, "bold"), fg_color="#8e44ad", hover_color="#9b59b6", command=self.import_logic).pack(side="left", padx=5)
        ctk.CTkButton(top_bar, text="📤 Export Template", font=("Segoe UI", 13, "bold"), fg_color="#2980b9", hover_color="#3498db", command=self.export_logic).pack(side="left", padx=5)
        
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_scroll.pack(fill="both", expand=True, padx=20, pady=5)
        
        btn_action_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        btn_action_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        
        ctk.CTkButton(btn_action_frame, text="💾 Save Logic Changes", font=("Segoe UI", 16, "bold"), fg_color="#e67e22", height=45, command=self.save_gui_logic).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(btn_action_frame, text="🔄 Save & Recalculate KPI", font=("Segoe UI", 16, "bold"), fg_color="#e74c3c", height=45, command=self.save_and_recalculate).pack(side="left", fill="x", expand=True, padx=5)
        
        self.render_logic_settings()

    def render_logic_settings(self):
        for widget in self.settings_scroll.winfo_children():
            widget.destroy()
            
        self.entry_fields = {}
        categories = [
            ("REGULAR", "🔵 REGULAR (Cash)"), 
            ("DELIVERY", "🛵 DELIVERY (Normal)"), 
            ("DIGITAL", "🟣 DIGITAL (Marketplace)"), 
            ("INSURANCE", "🏥 INSURANCE"),
            ("EVALUATION", "📋 EVALUATION"),
            ("PUSH_LIST", "🔥 PUSH LIST")
        ]
        
        for cat_k, cat_n in categories:
            cat_frame = ctk.CTkFrame(self.settings_scroll, fg_color=("gray95", "gray15"), corner_radius=10)
            cat_frame.pack(fill="x", pady=10, ipady=5)
            ctk.CTkLabel(cat_frame, text=cat_n, font=("Segoe UI", 18, "bold"), text_color=GREEN_PRIMARY).pack(anchor="w", padx=20, pady=5)
            metrics_container = ctk.CTkFrame(cat_frame, fg_color="transparent")
            metrics_container.pack(fill="x", padx=10, pady=5)
            
            if cat_k == "EVALUATION":
                metrics = [("performance", "Performance"), ("customer_service", "Customer Service"), ("knowledge", "Knowledge")]
            elif cat_k == "PUSH_LIST":
                metrics = [("quantity", "Quantity")]
            else:
                metrics = [("receipts", "Receipts"), ("sales", "Sales (EGP)"), ("avg_receipt", "Avg Receipt"), ("units", "Units")]
                
            for met_k, met_n in metrics:
                met_col = ctk.CTkFrame(metrics_container, fg_color=("gray90", "gray20"), corner_radius=8)
                met_col.pack(side="left", fill="both", expand=True, padx=5)
                ctk.CTkLabel(met_col, text=met_n, font=("Segoe UI", 14, "bold"), text_color="#f1c40f").pack(pady=5)
                
                rows_frame = ctk.CTkFrame(met_col, fg_color="transparent")
                rows_frame.pack(fill="both", expand=True)
                
                self.entry_fields[f"{cat_k}_{met_k}"] = []
                tiers = self.kpi_logic.get(cat_k, {}).get(met_k, [])
                if not tiers:
                    tiers = [{'target': 0, 'points': 0} for _ in range(5)]
                    
                prev_val = 0 
                for tier in tiers:
                    self.add_tier_row(rows_frame, cat_k, met_k, tier['target'], tier['points'], f_val=prev_val)
                    try: prev_val = int(float(tier['target'])) + 1
                    except: prev_val = ""
                
                btn_add = ctk.CTkButton(met_col, text="+ Add Tier", font=("Segoe UI", 11, "bold"), height=22, width=80, fg_color="#34495e", hover_color="#2c3e50", command=lambda rf=rows_frame, c=cat_k, m=met_k: self.add_tier_row(rf, c, m, "0", "0", ""))
                btn_add.pack(pady=5)

    def export_logic(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile="KPI_Template.json")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.kpi_logic, f, indent=4)
                messagebox.showinfo("Success", "Logic template exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def import_logic(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    new_logic = json.load(f)
                self.kpi_logic = new_logic
                with open(self.logic_file, 'w', encoding='utf-8') as f:
                    json.dump(self.kpi_logic, f, indent=4)
                self.render_logic_settings()
                messagebox.showinfo("Success", "Logic template imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import template.\n{str(e)}")

    def save_gui_logic(self):
        new_logic = self.kpi_logic.copy()
        try:
            for key, fields in self.entry_fields.items():
                cat, sub = key.split('_', 1)
                new_logic[cat][sub] = [{'target': float(f['target'].get()), 'points': int(f['points'].get())} for f in fields]
            with open(self.logic_file, 'w', encoding='utf-8') as f: json.dump(new_logic, f, indent=4)
            self.kpi_logic = new_logic; messagebox.showinfo("Success", "Settings saved!")
        except: messagebox.showerror("Error", "Check inputs.")

    def save_and_recalculate(self):
        self.save_gui_logic()
        if self.raw_df is not None:
            self.process_data()
        else:
            messagebox.showwarning("Warning", "Please load data in Tab 1 first before recalculating.")
            self.tabs.set("1. Upload & Filter")

    def export_excel(self, target_tree):
        if not target_tree.get_children(): return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Export_{datetime.now().strftime('%Y%m%d')}.xlsx")
        if path: 
            pd.DataFrame([target_tree.item(i)["values"] for i in target_tree.get_children()], columns=target_tree["columns"]).to_excel(path, index=False, engine='openpyxl')
            messagebox.showinfo("Success", "Exported Successfully!")

    def setup_compare(self):
        self.raw_df_p2 = None
        self.comp_results_data = []

        top_frame = ctk.CTkFrame(self.tab_compare, fg_color="transparent")
        top_frame.pack(fill="x", pady=10, padx=10)
        
        load_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        load_frame.pack(side="left")
        ctk.CTkLabel(load_frame, text="Upload Period 2 Data:", font=("Segoe UI", 14, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(load_frame, text="📥 Load Excel/CSV", font=("Segoe UI", 13, "bold"), command=self.load_p2_file).pack(side="left", padx=5)
        
        date_frame = ctk.CTkFrame(top_frame, fg_color=("gray90", "gray20"), corner_radius=8)
        date_frame.pack(side="left", padx=20)
        ctk.CTkLabel(date_frame, text="Period 2 Dates:", font=("Segoe UI", 13, "bold")).pack(side="left", padx=5)
        self.comp_date_from = DateEntry(date_frame, width=12, font=("Segoe UI", 11), background=GREEN_PRIMARY, foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.comp_date_from.pack(side="left", padx=5, pady=5)
        ctk.CTkLabel(date_frame, text="To:", font=("Segoe UI", 13, "bold")).pack(side="left")
        self.comp_date_to = DateEntry(date_frame, width=12, font=("Segoe UI", 11), background=GREEN_PRIMARY, foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.comp_date_to.pack(side="left", padx=5, pady=5)

        ctk.CTkButton(top_frame, text="⚡ Run Comparison", font=("Segoe UI", 14, "bold"), fg_color="#f39c12", hover_color="#e67e22", command=self.process_comparison).pack(side="left", padx=20)
        ctk.CTkButton(top_frame, text="Export Excel 📊", font=("Segoe UI", 14, "bold"), fg_color=GREEN_PRIMARY, command=lambda: self.export_excel(self.comp_tree)).pack(side="right")
        
        search_frame = ctk.CTkFrame(self.tab_compare, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(search_frame, text="🔍 Search:", font=("Segoe UI", 13, "bold")).pack(side="left", padx=5)
        self.search_entry_comp = ctk.CTkEntry(search_frame, width=150, font=("Segoe UI", 13))
        self.search_entry_comp.pack(side="left", padx=5)
        self.search_entry_comp.bind("<KeyRelease>", self.filter_comp_results)
        self.branch_filter_comp = ctk.CTkComboBox(search_frame, values=["All Branches"], width=150, command=self.filter_comp_results)
        self.branch_filter_comp.pack(side="left", padx=5)
        self.job_filter_comp = ctk.CTkComboBox(search_frame, values=["All Jobs"], width=150, command=self.filter_comp_results)
        self.job_filter_comp.pack(side="left", padx=5)
        self.status_lbl_comp = ctk.CTkLabel(search_frame, text="Waiting for P2 data...", text_color="gray", font=("Segoe UI", 13))
        self.status_lbl_comp.pack(side="right", padx=10)

        self.comp_tree_frame = ctk.CTkFrame(self.tab_compare)
        self.comp_tree_frame.pack(fill="both", expand=True, pady=5)
        self.comp_tree = ttk.Treeview(self.comp_tree_frame)
        scroll_y = ttk.Scrollbar(self.comp_tree_frame, orient="vertical", command=self.comp_tree.yview)
        scroll_x = ttk.Scrollbar(self.comp_tree_frame, orient="horizontal", command=self.comp_tree.xview)
        self.comp_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y"); scroll_x.pack(side="bottom", fill="x"); self.comp_tree.pack(fill="both", expand=True)

    def load_p2_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV", "*.csv")])
        if not file_path: return
        try:
            self.status_lbl_comp.configure(text="Reading Period 2 file...")
            self.update()
            if file_path.endswith('.csv'):
                try: self.raw_df_p2 = pd.read_csv(file_path, encoding='utf-8-sig')
                except UnicodeDecodeError: self.raw_df_p2 = pd.read_csv(file_path, encoding='windows-1256')
            else: self.raw_df_p2 = pd.read_excel(file_path)
            
            def find_col(df, possible_names):
                for name in possible_names:
                    if name in df.columns: return name
                return None
            col_date = find_col(self.raw_df_p2, ["Date", "التاريخ"])
            if col_date:
                self.raw_df_p2[col_date] = pd.to_datetime(self.raw_df_p2[col_date], errors='coerce')
                valid_dates = self.raw_df_p2[col_date].dropna()
                if not valid_dates.empty:
                    self.comp_date_from.set_date(valid_dates.min())
                    self.comp_date_to.set_date(valid_dates.max())
            self.status_lbl_comp.configure(text="✅ Period 2 Data loaded!")
        except Exception as e: messagebox.showerror("Error", str(e))

    def process_comparison(self):
        if not self.all_results: return messagebox.showwarning("Warning", "Please Calculate Period 1 in Tab 1 first!")
        if self.raw_df_p2 is None: return messagebox.showwarning("Warning", "Please load Period 2 data first!")
        
        try:
            df = self.raw_df_p2.copy()
            def find_col(df, possible_names):
                for name in possible_names:
                    if name in df.columns: return name
                return None
            col_date = find_col(df, ["Date", "التاريخ"])
            col_name = find_col(df, ["Full Name", "Employee Name", "Name", "Salespers."])
            col_code = find_col(df, ["Salespers.", "Code", "كود الموظف"])
            col_job  = find_col(df, ["Position Name", "الوظيفة", "Job Title", "Position", "المسمى الوظيفي", "Role"]) 
            col_branch = find_col(df, ["Branch Name", "Branch", "الفرع"])
            col_rec = find_col(df, ["Reciept.No", "Receipt Number", "Trans.", "Invoice"])
            col_price = find_col(df, ["Sales Price", "Gross Sales", "Net Sales", "Price"])
            col_qty = find_col(df, ["Quantity Dimenions", "Quantity", "Qty"])
            col_group = "Z Customer Group"
            col_pos = find_col(df, ["POS no.", "POS", "Terminal", "نقطة البيع", "رقم الكاشير"])
            col_mat_desc = find_col(df, ["Material Description", "Material Desc", "Item Name", "Description"])
            
            if not all([col_name, col_rec, col_price, col_group]): return messagebox.showerror("Error", "Critical columns missing in P2.")

            start_date = pd.to_datetime(self.comp_date_from.get_date())
            end_date = pd.to_datetime(self.comp_date_to.get_date())
            if col_date: df = df[(pd.to_datetime(df[col_date]) >= start_date) & (pd.to_datetime(df[col_date]) <= end_date)]
            
            df[col_price] = pd.to_numeric(df[col_price].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df[col_qty] = pd.to_numeric(df[col_qty].astype(str).str.replace(',', ''), errors='coerce').fillna(1)
            
            cols_to_join = [col_rec]
            if col_branch: cols_to_join.append(col_branch)
            if col_pos: cols_to_join.append(col_pos)
            if col_date:
                df['Temp_Date_Str'] = pd.to_datetime(df[col_date], errors='coerce').dt.strftime('%Y-%m-%d')
                cols_to_join.append('Temp_Date_Str')
            df['True_Receipt_ID'] = df[cols_to_join].astype(str).agg('_'.join, axis=1)

            df[col_group] = df[col_group].fillna("REGULAR").astype(str).str.upper()
            cond_normal_del = df[col_group].str.contains("NORMAL DELIVERY", case=False, na=False)
            if col_mat_desc:
                is_real_item = ~df[col_mat_desc].astype(str).str.contains("DELIVERY FEES", case=False, na=False)
                receipts_with_items = df.loc[is_real_item, 'True_Receipt_ID'].unique()
                df = df[~(cond_normal_del & (~df['True_Receipt_ID'].isin(receipts_with_items)))]
            else:
                df = df[~cond_normal_del]

            p2_scores = {}
            pharmacists = df[col_name].dropna().unique()
            for pharm in pharmacists:
                p_data = df[df[col_name] == pharm]
                raw_code = p_data[col_code].iloc[0] if col_code else None
                code = str(int(float(raw_code))) if pd.notnull(raw_code) else "N/A"
                
                if 'Temp_Date_Str' in p_data.columns:
                    pharm_working_days = p_data['Temp_Date_Str'].nunique()
                else:
                    pharm_working_days = 1
                if pharm_working_days <= 0: pharm_working_days = 1
                
                ordered_types = [("DELIVERY", "DELIVERY"), ("DIGITAL", "DIGITAL|MARKET"), ("INSURANCE", "INSURANCE")]
                pts_dict = {"DELIVERY": 0, "DIGITAL": 0, "INSURANCE": 0}
                
                reg_res = self.calc_cat_detailed(p_data[~p_data[col_group].str.contains("DELIVERY|DIGITAL|MARKET|INSURANCE", na=False)], "REGULAR", 'True_Receipt_ID', col_price, col_qty, pharm_working_days)
                for k, pattern in ordered_types:
                    sub_res = self.calc_cat_detailed(p_data[p_data[col_group].str.contains(pattern, na=False)], k, 'True_Receipt_ID', col_price, col_qty, pharm_working_days)
                    pts_dict[k] = sub_res["Pts"]
                    
                grand_total = reg_res["Pts"] + sum(pts_dict.values())
                p2_scores[code] = {"reg": reg_res["Pts"], "del": pts_dict["DELIVERY"], "dig": pts_dict["DIGITAL"], "ins": pts_dict["INSURANCE"], "total": grand_total}

            self.comp_results_data.clear()
            for r in self.all_results:
                name, code, branch, job = str(r[0]), str(r[1]), str(r[3]), str(r[2])
                p1_reg, p1_del, p1_dig, p1_ins, p1_tot = float(r[6]), float(r[7]), float(r[8]), float(r[9]), float(r[12])
                
                if code in p2_scores:
                    p2_data = p2_scores[code]
                    p2_reg, p2_del, p2_dig, p2_ins, p2_tot = p2_data["reg"], p2_data["del"], p2_data["dig"], p2_data["ins"], p2_data["total"]
                else:
                    p2_reg = p2_del = p2_dig = p2_ins = p2_tot = 0

                growth_pct = ((p2_tot - p1_tot) / p1_tot * 100) if p1_tot > 0 else (100 if p2_tot > 0 else 0)
                diff_reg = p2_reg - p1_reg
                diff_del = p2_del - p1_del
                diff_dig = p2_dig - p1_dig
                diff_ins = p2_ins - p1_ins
                
                row = [name, code, branch, job, 
                       f"{p1_tot:.0f}", f"{p2_tot:.0f}", 
                       f"{growth_pct:+.1f}%".replace('.0%', '%'), 
                       f"{diff_reg:+.0f}", f"{diff_del:+.0f}", 
                       f"{diff_dig:+.0f}", f"{diff_ins:+.0f}"]
                self.comp_results_data.append(row)

            cols_comp = ["Name", "Code", "Branch", "Job", "P1 Total", "P2 Total", "Growth %", "REGULAR Diff", "DELIVERY Diff", "DIGITAL Diff", "INSURANCE Diff"]
            self.comp_tree["columns"] = cols_comp
            self.comp_tree["show"] = "headings"
            for c in cols_comp: 
                self.comp_tree.heading(c, text=c, command=lambda _c=c: self.treeview_sort_column(self.comp_tree, _c, False))
                if c in ["Name", "Job", "Branch"]:
                    self.comp_tree.column(c, anchor="w")
                else:
                    self.comp_tree.column(c, anchor="center")
            
            self.filter_comp_results()
            self.status_lbl_comp.configure(text="✅ Comparison Completed!")
            
        except Exception as e: messagebox.showerror("Error", str(e))

    def filter_comp_results(self, event=None):
        q = self.search_entry_comp.get().lower()
        b_filter = self.branch_filter_comp.get()
        j_filter = self.job_filter_comp.get()
        
        self.comp_tree.delete(*self.comp_tree.get_children())
        for r in self.comp_results_data:
            name, code, branch, job = str(r[0]).lower(), str(r[1]).lower(), str(r[2]), str(r[3])
            if (q in name or q in code) and \
               (b_filter == fix_arabic("All Branches") or b_filter == fix_arabic(branch)) and \
               (j_filter == fix_arabic("All Jobs") or j_filter == fix_arabic(job)):
                self.comp_tree.insert("", "end", values=r)
        self.auto_fit_columns(self.comp_tree)

if __name__ == "__main__":
    KPICalculatorApp().mainloop()