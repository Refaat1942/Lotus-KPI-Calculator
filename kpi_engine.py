"""KPI calculation engine — extracted from kpi.py (no GUI dependencies)."""
import copy
import json
import os
import tempfile
from datetime import datetime

import pandas as pd
import psycopg2

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_LIB = True
except ImportError:
    ARABIC_LIB = False

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

RESULT_COLUMNS = [
    "Employee Name", "Code", "Job Title", "Branch", "Main Shift", "Working Days",
    "REGULAR", "DELIVERY", "DIGITAL", "INSURANCE", "EVALUATION", "PUSH LIST", "TOTAL SCORE"
]

COMPARE_COLUMNS = [
    "Name", "Code", "Branch", "Job", "P1 Total", "P2 Total", "Growth %",
    "REGULAR Diff", "DELIVERY Diff", "DIGITAL Diff", "INSURANCE Diff"
]

SETTINGS_CATEGORIES = [
    ("REGULAR", "REGULAR (Cash)"),
    ("DELIVERY", "DELIVERY (Normal)"),
    ("DIGITAL", "DIGITAL (Marketplace)"),
    ("INSURANCE", "INSURANCE"),
    ("EVALUATION", "EVALUATION"),
    ("PUSH_LIST", "PUSH LIST"),
]


def fix_arabic(text):
    """Bidi fix for Tkinter/desktop (LTR widgets)."""
    if not ARABIC_LIB or pd.isna(text):
        return str(text)
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except Exception:
        return str(text)


def fix_arabic_web(text):
    """Reshape Arabic letters only — browsers handle direction via dir=auto."""
    if pd.isna(text):
        return str(text)
    s = str(text)
    if not ARABIC_LIB:
        return s
    try:
        if any("\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F" for c in s):
            return arabic_reshaper.reshape(s)
        return s
    except Exception:
        return s


def _is_arabic_text(text):
    s = str(text)
    return any("\u0600" <= c <= "\u06FF" for c in s)


def find_col(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def normalize_num(val):
    """Store whole numbers as int (no 16.0 in JSON or forms)."""
    f = float(val)
    return int(f) if f == int(f) else f


def fmt_num(val):
    """Format a number for display in inputs — no trailing .0."""
    if val is None or val == "":
        return ""
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        return f"{f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(val)


def _normalize_tier(tier):
    out = {
        "target": normalize_num(tier["target"]),
        "points": int(tier["points"]),
    }
    if "from" in tier:
        out["from"] = normalize_num(tier["from"])
    return out


def _normalize_logic(logic):
    normalized = copy.deepcopy(logic)
    for cat_k, metrics in normalized.items():
        if not isinstance(metrics, dict):
            continue
        for met_k, tiers in metrics.items():
            if isinstance(tiers, list):
                metrics[met_k] = [_normalize_tier(t) for t in tiers if isinstance(t, dict)]
    return normalized


class KPIEngine:
    def __init__(self, dsn, logic_file, data_cache, upload_folder):
        self.dsn = dsn
        self.logic_file = logic_file
        self.data_cache = data_cache
        self.upload_folder = upload_folder
        self.raw_df = None
        self.eval_df = None
        self.push_df = None
        self.raw_df_p2 = None
        self.kpi_logic = self.load_logic()
        self.all_results = []
        self.comp_results_data = []
        self.detailed_scores = {}
        self.excluded_stats = {}
        self.enable_eval = False
        self.enable_push = False
        self.last_period = ("", "")
        os.makedirs(data_cache, exist_ok=True)
        os.makedirs(upload_folder, exist_ok=True)
        self._setup_database()

    def _connect(self):
        """Return a new psycopg2 connection to the configured PostgreSQL database."""
        return psycopg2.connect(self.dsn)

    def _setup_database(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS kpi_records (
                id SERIAL PRIMARY KEY,
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
                job_title TEXT,
                excluded_sales REAL DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def load_logic(self):
        loaded = copy.deepcopy(DEFAULT_KPI_LOGIC)
        if os.path.exists(self.logic_file):
            try:
                with open(self.logic_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    for k in loaded.keys():
                        if k in file_data:
                            loaded[k] = file_data[k]
            except Exception:
                pass
        with open(self.logic_file, 'w', encoding='utf-8') as f:
            json.dump(loaded, f, indent=4)
        return loaded

    def save_logic(self, new_logic):
        new_logic = _normalize_logic(new_logic)
        with open(self.logic_file, 'w', encoding='utf-8') as f:
            json.dump(new_logic, f, indent=4)
        self.kpi_logic = new_logic

    def read_file(self, path):
        if path.endswith('.csv'):
            try:
                return pd.read_csv(path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                return pd.read_csv(path, encoding='windows-1256')
        return pd.read_excel(path)

    def guess_date_range(self, df=None):
        df = df if df is not None else self.raw_df
        if df is None:
            return "", ""
        col_date = find_col(df, ["Date", "التاريخ"])
        if not col_date:
            return "", ""
        valid = pd.to_datetime(df[col_date], errors='coerce').dropna()
        if valid.empty:
            return "", ""
        return valid.min().strftime("%Y-%m-%d"), valid.max().strftime("%Y-%m-%d")

    @staticmethod
    def translate_position(pos_name):
        if pd.isna(pos_name):
            return "Unknown"
        pos_str = str(pos_name).strip()
        if 'مساعد صيدلي' in pos_str:
            return 'Pharmacy Assistant'
        if 'صيدلي' in pos_str:
            return 'Pharmacist'
        if 'مدير فتر' in pos_str or 'shift manager' in pos_str.lower():
            return 'Shift Manager'
        if 'مدير' in pos_str or 'branch manager' in pos_str.lower():
            return 'Branch Manager'
        if 'كاشير' in pos_str:
            return 'Cashier'
        if 'تجميل' in pos_str:
            return 'Cosmetics Specialist'
        if 'دليفري' in pos_str or 'delivery' in pos_str.lower():
            return 'Delivery'
        if 'عامل' in pos_str:
            return 'Worker'
        if 'محاسب' in pos_str:
            return 'Accountant'
        return pos_str

    @staticmethod
    def classify_shift(time_val):
        try:
            val = str(time_val).strip()
            h = int(val.split(':')[0]) if ':' in val else int(float(time_val))
            if 0 <= h < 8:
                return 'Night Shift'
            elif 8 <= h < 16:
                return 'Morning Shift'
            else:
                return 'Evening Shift'
        except Exception:
            return 'Random'

    def get_points_from_tiers(self, value, tiers):
        if value < 0:
            return 0
        if not tiers:
            return 0

        # When tiers define explicit From/To ranges, match value inside [from, target].
        if any("from" in t for t in tiers):
            for t in sorted(tiers, key=lambda x: (float(x.get("from", 0)), float(x["target"]))):
                t_from = float(t.get("from", 0))
                t_to = float(t["target"])
                if t_from <= value <= t_to:
                    return t["points"]
            sorted_tiers = sorted(tiers, key=lambda x: float(x["target"]))
            if sorted_tiers and value > float(sorted_tiers[-1]["target"]):
                return sorted_tiers[-1]["points"]
            return 0

        # Legacy tiers (target only): cumulative ceiling — value <= target.
        valid_tiers = sorted(tiers, key=lambda x: x["target"])
        for t in valid_tiers:
            if value <= t["target"]:
                return t["points"]
        return valid_tiers[-1]["points"]

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

        details = [
            (cat_key, "Receipts", f"{recs:.0f}", f"{d_recs:.2f}".rstrip('0').rstrip('.'), f"{pts_recs:.0f}"),
            (cat_key, "Sales", f"{sales:,.0f}", f"{d_sales:,.0f}", f"{pts_sales:.0f}"),
            (cat_key, "Avg Rec", f"{avg_rec:,.0f}", f"{avg_rec:,.0f}", f"{pts_avg:.0f}"),
            (cat_key, "Units", f"{units:.0f}", f"{units_per_rec:.2f}".rstrip('0').rstrip('.'), f"{pts_units:.0f}"),
        ]
        return {"Pts": total_pts, "Details": details}

    def calculate_kpi(self, df, col_name, col_code, col_branch, col_rec, col_price, col_qty, col_group,
                      excluded_sales_dict, excluded_count_dict):
        self.all_results.clear()
        self.detailed_scores.clear()
        self.excluded_stats.clear()
        pharmacists = df[col_name].dropna().unique()
        for pharm in pharmacists:
            p_data = df[df[col_name] == pharm]
            raw_code = p_data[col_code].iloc[0] if col_code else None
            code = str(int(float(raw_code))) if pd.notnull(raw_code) else "N/A"
            job_title = str(p_data['Translated_Position'].iloc[0]) if 'Translated_Position' in p_data.columns else "Unknown"
            branch = str(p_data[col_branch].iloc[0]) if col_branch else "N/A"
            try:
                emp_shifts = p_data['Shift_Calculated'].mode()
                shift = emp_shifts[0] if not emp_shifts.empty else "Random"
            except Exception:
                shift = "Random"

            if 'Temp_Date_Str' in p_data.columns:
                pharm_working_days = p_data['Temp_Date_Str'].nunique()
            else:
                pharm_working_days = 1
            if pharm_working_days <= 0:
                pharm_working_days = 1

            ordered_types = [("DELIVERY", "DELIVERY"), ("DIGITAL", "DIGITAL|MARKET"), ("INSURANCE", "INSURANCE")]
            pts_dict = {"DELIVERY": 0, "DIGITAL": 0, "INSURANCE": 0}
            details_accum = []

            reg_res = self.calc_cat_detailed(
                p_data[~p_data[col_group].str.contains("DELIVERY|DIGITAL|MARKET|INSURANCE", na=False)],
                "REGULAR", col_rec, col_price, col_qty, pharm_working_days
            )

            for k, pattern in ordered_types:
                sub_res = self.calc_cat_detailed(
                    p_data[p_data[col_group].str.contains(pattern, na=False)],
                    k, col_rec, col_price, col_qty, pharm_working_days
                )
                pts_dict[k] = sub_res["Pts"]
                details_accum.extend(sub_res["Details"])

            eval_pts = 0
            push_pts = 0
            details_eval = []

            if self.enable_eval:
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
                    ("EVALUATION", "Working Days", f"{pharm_working_days:.0f}", "", "0"),
                ])

            if self.enable_push:
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

            row = [
                str(pharm), code, job_title, branch, shift,
                f"{pharm_working_days:.0f}",
                f"{reg_res['Pts']:.0f}", f"{pts_dict['DELIVERY']:.0f}",
                f"{pts_dict['DIGITAL']:.0f}", f"{pts_dict['INSURANCE']:.0f}",
                f"{eval_pts:.0f}", f"{push_pts:.0f}", f"{grand_total:.0f}",
            ]
            self.all_results.append(row)
            self.detailed_scores[str(pharm)] = reg_res["Details"] + details_accum

        self.all_results.sort(
            key=lambda x: float(x[-1]) if x[-1].replace('.', '', 1).isdigit() else 0,
            reverse=True
        )

    def process_data(self, date_from, date_to, enable_eval=False, enable_push=False, save_cache=True):
        if self.raw_df is None:
            return {"ok": False, "error": "Load data first."}

        self.enable_eval = enable_eval
        self.enable_push = enable_push

        if enable_eval and (self.eval_df is None or self.eval_df.empty):
            return {"ok": False, "error": "Evaluation is enabled. Please upload the evaluation sheet first, or disable it."}

        if enable_push and (self.push_df is None or self.push_df.empty):
            return {"ok": False, "error": "Push List is enabled. Please upload the push list sheet first, or disable it."}

        try:
            df = self.raw_df.copy()
            col_date = find_col(df, ["Date", "التاريخ"])
            col_name = find_col(df, ["Full Name", "Employee Name", "Name", "Salespers."])
            col_code = find_col(df, ["Salespers.", "Code", "كود الموظف"])
            col_job = find_col(df, ["Position Name", "الوظيفة", "Job Title", "Position", "المسمى الوظيفي", "Role"])
            col_branch = find_col(df, ["Branch Name", "Branch", "الفرع"])
            col_rec = find_col(df, ["Reciept.No", "Receipt Number", "Trans.", "Invoice"])
            col_price = find_col(df, ["Sales Price", "Gross Sales", "Net Sales", "Price"])
            col_qty = find_col(df, ["Quantity Dimenions", "Quantity", "Qty"])
            col_group = "Z Customer Group"
            col_pos = find_col(df, ["POS no.", "POS", "Terminal", "نقطة البيع", "رقم الكاشير"])
            col_mat_desc = find_col(df, ["Material Description", "Material Desc", "Item Name", "Description"])

            if col_group not in df.columns:
                return {"ok": False, "error": "Column 'Z Customer Group' is missing."}
            if not all([col_name, col_rec, col_price]):
                return {"ok": False, "error": "Critical columns missing."}

            if col_job:
                df['Translated_Position'] = df[col_job].apply(self.translate_position)
            else:
                df['Translated_Position'] = "Unknown"

            start_date = pd.to_datetime(date_from)
            end_date = pd.to_datetime(date_to)
            if col_date:
                df = df[(pd.to_datetime(df[col_date]) >= start_date) & (pd.to_datetime(df[col_date]) <= end_date)]

            df[col_price] = pd.to_numeric(df[col_price].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            if col_qty:
                df[col_qty] = pd.to_numeric(df[col_qty].astype(str).str.replace(',', ''), errors='coerce').fillna(1)
            else:
                col_qty = "Quantity Dimenions"
                df[col_qty] = 1

            col_hour = find_col(df, ["Hour of sale", "Time"])
            if col_hour:
                df['Shift_Calculated'] = df[col_hour].apply(self.classify_shift)
            else:
                df['Shift_Calculated'] = "Random"

            cols_to_join = [col_rec]
            if col_branch:
                cols_to_join.append(col_branch)
            if col_pos:
                cols_to_join.append(col_pos)
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
            self.calculate_kpi(df, col_name, col_code, col_branch, 'True_Receipt_ID', col_price, col_qty, col_group,
                                 excluded_sales_dict, excluded_count_dict)

            str_start = start_date.strftime("%Y-%m-%d")
            str_end = end_date.strftime("%Y-%m-%d")
            self.last_period = (str_start, str_end)
            self.save_results_to_db(str_start, str_end)

            if save_cache:
                timestamp = datetime.now().strftime('%y%m%d-%H%M')
                cache_filename = f"{str_start}_{str_end}_{timestamp}.pkl"
                try:
                    self.raw_df.to_pickle(os.path.join(self.data_cache, cache_filename))
                except Exception:
                    pass

            return {"ok": True, "count": len(self.all_results), "start": str_start, "end": str_end}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_results_to_db(self, start_date, end_date):
        conn = self._connect()
        cur = conn.cursor()
        for r in self.all_results:
            cur.execute(
                '''INSERT INTO kpi_records (start_date, end_date, emp_name, emp_code, job_title, branch, shift,
                   working_days, reg_pts, delivery_pts, digital_pts, insurance_pts, eval_pts, push_pts, grand_total)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (start_date, end_date, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12])
            )
        conn.commit()
        conn.close()

    def get_branches(self):
        branches = sorted({r[3] for r in self.all_results})
        return ["All Branches"] + list(branches)

    def get_jobs(self):
        jobs = sorted({r[2] for r in self.all_results})
        return ["All Jobs"] + list(jobs)

    def filter_results(self, q="", branch="All Branches", job="All Jobs", shift="All Shifts", include_unknown=True):
        q = q.lower()
        rows = []
        for r in self.all_results:
            if not include_unknown and r[2] == "Unknown":
                continue
            if (q in str(r[0]).lower() or q in str(r[1]).lower()) and \
               (branch == "All Branches" or branch == str(r[3])) and \
               (job == "All Jobs" or job == str(r[2])) and \
               (shift == "All Shifts" or shift == str(r[4])):
                rows.append([
                    fix_arabic_web(c) if i in (0, 2, 3, 4) and _is_arabic_text(c) else c
                    for i, c in enumerate(r)
                ])
        return rows

    def delete_unknown_employee(self, emp_code):
        self.all_results = [r for r in self.all_results if str(r[1]) != str(emp_code)]
        return True

    def get_employee_suggestions(self, q="", branch="All Branches", job="All Jobs"):
        q = q.lower()
        suggestions = []
        for r in self.all_results:
            name, code, j, b = str(r[0]).lower(), str(r[1]).lower(), str(r[2]), str(r[3])
            if (q in name or q in code) and \
               (branch == "All Branches" or branch == b) and \
               (job == "All Jobs" or job == j):
                suggestions.append({
                    "name": fix_arabic_web(r[0]) if _is_arabic_text(r[0]) else r[0],
                    "code": r[1],
                    "job": fix_arabic_web(r[2]) if _is_arabic_text(r[2]) else r[2],
                    "branch": fix_arabic_web(r[3]) if _is_arabic_text(r[3]) else r[3],
                })
        return suggestions

    def get_employee_detail(self, emp_name):
        rows = []
        ex_sales = self.excluded_stats.get(emp_name, {}).get("sales", 0.0)
        ex_count = self.excluded_stats.get(emp_name, {}).get("count", 0)
        current_category = None
        total_sales_all = total_recs_all = total_units_all = 0.0
        total_daily_sales = total_daily_recs = 0.0

        for dr in self.detailed_scores.get(emp_name, []):
            cat, metric = dr[0], dr[1]
            try:
                val = float(str(dr[2]).replace(',', ''))
                if metric == "Sales":
                    total_sales_all += val
                elif metric == "Receipts":
                    total_recs_all += val
                elif metric == "Units":
                    total_units_all += val
                d_val = float(str(dr[3]).replace(',', '').strip() or 0)
                if metric == "Sales":
                    total_daily_sales += d_val
                elif metric == "Receipts":
                    total_daily_recs += d_val
            except Exception:
                pass

            if current_category is not None and cat != current_category:
                rows.append({"type": "separator"})
            current_category = cat
            excluded = ""
            if cat == "DELIVERY":
                if metric == "Sales" and ex_sales > 0:
                    excluded = f"{ex_sales:,.0f}"
                elif metric == "Receipts" and ex_count > 0:
                    excluded = f"{ex_count:.0f}"
            rows.append({
                "type": "data",
                "category": cat, "metric": metric,
                "avg_month": dr[2], "avg_day": dr[3], "reward": dr[4], "excluded": excluded,
            })

        total = sum(float(str(r[-1]).replace(',', '')) for r in self.detailed_scores.get(emp_name, []))
        total_avg_all = total_sales_all / total_recs_all if total_recs_all > 0 else 0
        total_units_per_rec = total_units_all / total_recs_all if total_recs_all > 0 else 0

        rows.append({"type": "separator"})
        rows.append({"type": "summary", "category": "Total", "metric": "Receipts",
                     "avg_month": f"{total_recs_all:,.0f}", "avg_day": f"{total_daily_recs:.2f}".rstrip('0').rstrip('.'), "reward": "", "excluded": ""})
        rows.append({"type": "summary", "category": "Total", "metric": "Sales",
                     "avg_month": f"{total_sales_all:,.0f}", "avg_day": f"{total_daily_sales:,.0f}", "reward": "", "excluded": ""})
        rows.append({"type": "summary", "category": "Total", "metric": "Avg Rec",
                     "avg_month": f"{total_avg_all:,.0f}", "avg_day": f"{total_avg_all:,.0f}", "reward": "", "excluded": ""})
        rows.append({"type": "summary", "category": "Total", "metric": "Units",
                     "avg_month": f"{total_units_all:,.0f}", "avg_day": f"{total_units_per_rec:.2f}".rstrip('0').rstrip('.'), "reward": "", "excluded": ""})
        rows.append({"type": "reward", "category": "Total", "metric": "Rewards", "reward": f"{total:,.0f}"})
        rows.append({"type": "separator"})
        rows.append({"type": "excluded", "category": "Excluded", "metric": "Receipts", "avg_month": f"{ex_count:.0f}"})
        rows.append({"type": "excluded", "category": "Excluded", "metric": "Sales", "avg_month": f"{ex_sales:,.0f}"})
        return rows

    def get_saved_datasets(self):
        files = [f for f in os.listdir(self.data_cache) if f.endswith(".pkl")]
        mapping = {}
        display_list = []
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.data_cache, x)), reverse=True)
        for f in files:
            parts = f.replace(".pkl", "").split("_")
            try:
                display_name = f"Period: {parts[0]} → {parts[1]} (Saved: {parts[2]})"
            except Exception:
                display_name = f
            display_list.append(display_name)
            mapping[display_name] = os.path.join(self.data_cache, f)
        return display_list, mapping

    def recalc_dataset(self, dataset_key, mapping):
        if dataset_key not in mapping:
            return {"ok": False, "error": "No valid dataset selected."}
        try:
            self.raw_df = pd.read_pickle(mapping[dataset_key])
            d_from, d_to = self.guess_date_range()
            return self.process_data(d_from, d_to, self.enable_eval, self.enable_push, save_cache=False)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_history_summary(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """SELECT to_char(saved_at, 'YYYY-MM-DD HH24:MI:SS'),
                      start_date || ' to ' || end_date, COUNT(id)
               FROM kpi_records
               GROUP BY saved_at, start_date, end_date
               ORDER BY saved_at DESC"""
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def load_history_detail(self, saved_timestamp):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """SELECT emp_name, emp_code, job_title, branch, shift, working_days,
                      reg_pts, delivery_pts, digital_pts, insurance_pts, eval_pts, push_pts, grand_total
               FROM kpi_records
               WHERE to_char(saved_at, 'YYYY-MM-DD HH24:MI:SS') = %s""",
            (saved_timestamp,)
        )
        rows = cur.fetchall()
        conn.close()
        cols = ["Name", "Code", "Job Title", "Branch", "Main Shift", "Working Days",
                "REGULAR", "DELIVERY", "DIGITAL", "INSURANCE", "EVALUATION", "PUSH LIST", "TOTAL SCORE"]
        formatted = []
        for r in rows:
            fmt_r = list(r)
            for i in range(5, 13):
                if fmt_r[i] is not None:
                    try:
                        fmt_r[i] = f"{float(fmt_r[i]):.0f}"
                    except Exception:
                        pass
            formatted.append([
                fix_arabic_web(c) if isinstance(c, str) and i < 5 and _is_arabic_text(c) else c
                for i, c in enumerate(fmt_r)
            ])
        return cols, formatted

    def parse_logic_from_form(self, form_data):
        new_logic = copy.deepcopy(self.kpi_logic)
        for cat_k, _ in SETTINGS_CATEGORIES:
            if cat_k == "EVALUATION":
                metrics = ["performance", "customer_service", "knowledge"]
            elif cat_k == "PUSH_LIST":
                metrics = ["quantity"]
            else:
                metrics = ["receipts", "sales", "avg_receipt", "units"]
            for met_k in metrics:
                key = f"{cat_k}_{met_k}"
                froms = form_data.getlist(f"{key}_from")
                targets = form_data.getlist(f"{key}_target")
                points = form_data.getlist(f"{key}_points")
                tiers = []
                prev_start = 0
                for f_val, t_val, p_val in zip(froms, targets, points):
                    if t_val.strip() == "" and p_val.strip() == "":
                        continue
                    if f_val.strip() != "":
                        tier_from = float(f_val)
                    else:
                        tier_from = prev_start
                    tier = {
                        "from": normalize_num(tier_from),
                        "target": normalize_num(t_val),
                        "points": int(float(p_val)),
                    }
                    tiers.append(tier)
                    try:
                        prev_start = int(float(t_val)) + 1
                    except Exception:
                        prev_start = tier_from
                if tiers:
                    tiers.sort(key=lambda x: (x.get("from", 0), x["target"]))
                    new_logic[cat_k][met_k] = tiers
        return _normalize_logic(new_logic)

    def process_comparison(self, date_from, date_to):
        if not self.all_results:
            return {"ok": False, "error": "Please calculate Period 1 first."}
        if self.raw_df_p2 is None:
            return {"ok": False, "error": "Please load Period 2 data first."}

        try:
            df = self.raw_df_p2.copy()
            col_date = find_col(df, ["Date", "التاريخ"])
            col_name = find_col(df, ["Full Name", "Employee Name", "Name", "Salespers."])
            col_code = find_col(df, ["Salespers.", "Code", "كود الموظف"])
            col_branch = find_col(df, ["Branch Name", "Branch", "الفرع"])
            col_rec = find_col(df, ["Reciept.No", "Receipt Number", "Trans.", "Invoice"])
            col_price = find_col(df, ["Sales Price", "Gross Sales", "Net Sales", "Price"])
            col_qty = find_col(df, ["Quantity Dimenions", "Quantity", "Qty"])
            col_group = "Z Customer Group"
            col_pos = find_col(df, ["POS no.", "POS", "Terminal", "نقطة البيع", "رقم الكاشير"])
            col_mat_desc = find_col(df, ["Material Description", "Material Desc", "Item Name", "Description"])

            if not all([col_name, col_rec, col_price, col_group]):
                return {"ok": False, "error": "Critical columns missing in Period 2."}

            start_date = pd.to_datetime(date_from)
            end_date = pd.to_datetime(date_to)
            if col_date:
                df = df[(pd.to_datetime(df[col_date]) >= start_date) & (pd.to_datetime(df[col_date]) <= end_date)]

            df[col_price] = pd.to_numeric(df[col_price].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            if col_qty:
                df[col_qty] = pd.to_numeric(df[col_qty].astype(str).str.replace(',', ''), errors='coerce').fillna(1)
            else:
                col_qty = "Quantity Dimenions"
                df[col_qty] = 1

            cols_to_join = [col_rec]
            if col_branch:
                cols_to_join.append(col_branch)
            if col_pos:
                cols_to_join.append(col_pos)
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
            for pharm in df[col_name].dropna().unique():
                p_data = df[df[col_name] == pharm]
                raw_code = p_data[col_code].iloc[0] if col_code else None
                code = str(int(float(raw_code))) if pd.notnull(raw_code) else "N/A"

                if 'Temp_Date_Str' in p_data.columns:
                    pharm_working_days = p_data['Temp_Date_Str'].nunique()
                else:
                    pharm_working_days = 1
                if pharm_working_days <= 0:
                    pharm_working_days = 1

                ordered_types = [("DELIVERY", "DELIVERY"), ("DIGITAL", "DIGITAL|MARKET"), ("INSURANCE", "INSURANCE")]
                pts_dict = {"DELIVERY": 0, "DIGITAL": 0, "INSURANCE": 0}
                reg_res = self.calc_cat_detailed(
                    p_data[~p_data[col_group].str.contains("DELIVERY|DIGITAL|MARKET|INSURANCE", na=False)],
                    "REGULAR", 'True_Receipt_ID', col_price, col_qty, pharm_working_days
                )
                for k, pattern in ordered_types:
                    sub_res = self.calc_cat_detailed(
                        p_data[p_data[col_group].str.contains(pattern, na=False)],
                        k, 'True_Receipt_ID', col_price, col_qty, pharm_working_days
                    )
                    pts_dict[k] = sub_res["Pts"]
                grand_total = reg_res["Pts"] + sum(pts_dict.values())
                p2_scores[code] = {
                    "reg": reg_res["Pts"], "del": pts_dict["DELIVERY"],
                    "dig": pts_dict["DIGITAL"], "ins": pts_dict["INSURANCE"], "total": grand_total,
                }

            self.comp_results_data.clear()
            for r in self.all_results:
                name, code, branch, job = str(r[0]), str(r[1]), str(r[3]), str(r[2])
                p1_reg, p1_del, p1_dig, p1_ins, p1_tot = float(r[6]), float(r[7]), float(r[8]), float(r[9]), float(r[12])
                if code in p2_scores:
                    p2 = p2_scores[code]
                    p2_reg, p2_del, p2_dig, p2_ins, p2_tot = p2["reg"], p2["del"], p2["dig"], p2["ins"], p2["total"]
                else:
                    p2_reg = p2_del = p2_dig = p2_ins = p2_tot = 0

                growth_pct = ((p2_tot - p1_tot) / p1_tot * 100) if p1_tot > 0 else (100 if p2_tot > 0 else 0)
                row = [
                    fix_arabic_web(name) if _is_arabic_text(name) else name,
                    code,
                    fix_arabic_web(branch) if _is_arabic_text(branch) else branch,
                    fix_arabic_web(job) if _is_arabic_text(job) else job,
                    f"{p1_tot:.0f}", f"{p2_tot:.0f}",
                    f"{growth_pct:+.1f}%".replace('.0%', '%'),
                    f"{p2_reg - p1_reg:+.0f}", f"{p2_del - p1_del:+.0f}",
                    f"{p2_dig - p1_dig:+.0f}", f"{p2_ins - p1_ins:+.0f}",
                ]
                self.comp_results_data.append(row)

            return {"ok": True, "count": len(self.comp_results_data)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def filter_comp_results(self, q="", branch="All Branches", job="All Jobs"):
        q = q.lower()
        rows = []
        for r in self.comp_results_data:
            name, code = str(r[0]).lower(), str(r[1]).lower()
            if (q in name or q in code) and \
               (branch == "All Branches" or branch == r[2]) and \
               (job == "All Jobs" or job == r[3]):
                rows.append(r)
        return rows

    def export_dataframe(self, rows, columns, filename_prefix="Export"):
        fd, path = tempfile.mkstemp(suffix=".xlsx", prefix=filename_prefix)
        os.close(fd)
        pd.DataFrame(rows, columns=columns).to_excel(path, index=False, engine='openpyxl')
        return path

    def make_eval_template(self):
        fd, path = tempfile.mkstemp(suffix=".xlsx", prefix="Evaluation_Template")
        os.close(fd)
        pd.DataFrame(columns=["Emp Code", "Emp Name", "Branch", "Performance", "Customer Service", "Knowledge"]).to_excel(path, index=False)
        return path

    def make_push_template(self):
        fd, path = tempfile.mkstemp(suffix=".xlsx", prefix="PushList_Template")
        os.close(fd)
        pd.DataFrame(columns=["Emp Code", "Item Code", "Item Name", "Quantity Dimenions"]).to_excel(path, index=False)
        return path

    def get_settings_metrics(self, cat_k):
        if cat_k == "EVALUATION":
            return [("performance", "Performance"), ("customer_service", "Customer Service"), ("knowledge", "Knowledge")]
        if cat_k == "PUSH_LIST":
            return [("quantity", "Quantity")]
        return [("receipts", "Receipts"), ("sales", "Sales (EGP)"), ("avg_receipt", "Avg Receipt"), ("units", "Units")]
