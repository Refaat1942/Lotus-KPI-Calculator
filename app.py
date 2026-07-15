import os
import pickle
from functools import wraps

import pandas as pd
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify,
)
from werkzeug.utils import secure_filename

from config import Config
from kpi_engine import KPIEngine, RESULT_COLUMNS, COMPARE_COLUMNS, SETTINGS_CATEGORIES

app = Flask(__name__)
app.config.from_object(Config)


def parse_iso_date_from_form(form, prefix):
    """Build YYYY-MM-DD from day/month/year select fields."""
    day = form.get(f"{prefix}_day", "").strip()
    month = form.get(f"{prefix}_month", "").strip()
    year = form.get(f"{prefix}_year", "").strip()
    if day and month and year:
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return form.get(prefix, "").strip()


@app.template_filter("is_arabic")
def is_arabic_filter(text):
    from kpi_engine import _is_arabic_text
    return _is_arabic_text(text)

_engines = {}

_DF_KEYS = {
    "main": "raw_df",
    "eval": "eval_df",
    "push": "push_df",
    "p2": "raw_df_p2",
}


def _session_file(sid, name):
    return os.path.join(app.config["DATA_CACHE"], f"sess_{sid}_{name}.pkl")


def _persist_dataframe(sid, name, df):
    path = _session_file(sid, name)
    if df is None:
        session.pop(f"has_{name}", None)
        if os.path.exists(path):
            os.remove(path)
        return
    os.makedirs(app.config["DATA_CACHE"], exist_ok=True)
    df.to_pickle(path)
    session[f"has_{name}"] = True


def _restore_dataframe(sid, name):
    path = _session_file(sid, name)
    if os.path.exists(path):
        return pd.read_pickle(path)
    return None


def _persist_engine_state(eng, sid):
    state = {
        "all_results": eng.all_results,
        "detailed_scores": eng.detailed_scores,
        "excluded_stats": eng.excluded_stats,
        "comp_results_data": eng.comp_results_data,
        "enable_eval": eng.enable_eval,
        "enable_push": eng.enable_push,
        "last_period": eng.last_period,
    }
    os.makedirs(app.config["DATA_CACHE"], exist_ok=True)
    with open(_session_file(sid, "state"), "wb") as f:
        pickle.dump(state, f)


def _restore_engine_state(eng, sid):
    path = _session_file(sid, "state")
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        state = pickle.load(f)
    eng.all_results = state.get("all_results", [])
    eng.detailed_scores = state.get("detailed_scores", {})
    eng.excluded_stats = state.get("excluded_stats", {})
    eng.comp_results_data = state.get("comp_results_data", [])
    eng.enable_eval = state.get("enable_eval", False)
    eng.enable_push = state.get("enable_push", False)
    eng.last_period = state.get("last_period", ("", ""))


def _persist_engine(eng):
    sid = session.get("sid")
    if not sid:
        return
    for name, attr in _DF_KEYS.items():
        _persist_dataframe(sid, name, getattr(eng, attr, None))
    if eng.all_results or eng.comp_results_data:
        _persist_engine_state(eng, sid)


def _restore_engine(eng):
    sid = session.get("sid")
    if not sid:
        return
    for name, attr in _DF_KEYS.items():
        df = _restore_dataframe(sid, name)
        if df is not None:
            setattr(eng, attr, df)
    _restore_engine_state(eng, sid)


def _clear_session_files(sid):
    if not sid:
        return
    for name in list(_DF_KEYS.keys()) + ["state"]:
        path = _session_file(sid, name)
        if os.path.exists(path):
            os.remove(path)


def get_engine():
    sid = session.get("sid")
    if not sid:
        sid = os.urandom(16).hex()
        session["sid"] = sid
    if sid not in _engines:
        _engines[sid] = KPIEngine(
            app.config["DATABASE_URL"],
            app.config["LOGIC_FILE"],
            app.config["DATA_CACHE"],
            app.config["UPLOAD_FOLDER"],
        )
    eng = _engines[sid]
    _restore_engine(eng)
    _reload_main_from_upload(eng)
    return eng


def _reload_main_from_upload(eng):
    """Fallback: re-read the original uploaded file if pickle restore missed."""
    if eng.raw_df is not None:
        return
    path = session.get("main_file_path")
    if path and os.path.exists(path):
        try:
            eng.raw_df = eng.read_file(path)
        except Exception:
            pass


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapped


def save_upload(file):
    filename = secure_filename(file.filename)
    if not filename:
        ext = os.path.splitext(file.filename or "")[1].lower() or ".xlsx"
        filename = f"upload_{os.urandom(8).hex()}{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(path)
    return path


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("upload"))
    if request.method == "POST":
        if (request.form.get("username") == app.config["ADMIN_USER"] and
                request.form.get("password") == app.config["ADMIN_PASS"]):
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("upload"))
        flash("Invalid username or password", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    sid = session.pop("sid", None)
    _engines.pop(sid, None)
    _clear_session_files(sid)
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return redirect(url_for("upload"))


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    eng = get_engine()
    date_from = session.get("date_from", "")
    date_to = session.get("date_to", "")

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "load_main" and "main_file" in request.files:
            f = request.files["main_file"]
            if f.filename:
                path = save_upload(f)
                eng.raw_df = eng.read_file(path)
                session["main_file_path"] = path
                date_from, date_to = eng.guess_date_range()
                session["date_from"] = date_from
                session["date_to"] = date_to
                _persist_engine(eng)
                flash("Main data loaded successfully!", "success")

        elif action == "load_eval" and "eval_file" in request.files:
            f = request.files["eval_file"]
            if f.filename:
                path = save_upload(f)
                eng.eval_df = eng.read_file(path)
                _persist_engine(eng)
                flash("Evaluation data loaded!", "success")

        elif action == "load_push" and "push_file" in request.files:
            f = request.files["push_file"]
            if f.filename:
                path = save_upload(f)
                eng.push_df = eng.read_file(path)
                _persist_engine(eng)
                flash("Push List data loaded!", "success")

        elif action == "calculate":
            _restore_engine(eng)
            _reload_main_from_upload(eng)
            if eng.raw_df is None:
                flash("Load data first.", "error")
                return render_template(
                    "upload.html",
                    date_from=session.get("date_from", date_from),
                    date_to=session.get("date_to", date_to),
                    has_main=bool(session.get("has_main") or session.get("main_file_path")),
                    has_eval=eng.eval_df is not None or session.get("has_eval"),
                    has_push=eng.push_df is not None or session.get("has_push"),
                )
            date_from = parse_iso_date_from_form(request.form, "date_from")
            date_to = parse_iso_date_from_form(request.form, "date_to")
            session["date_from"] = date_from
            session["date_to"] = date_to
            result = eng.process_data(
                date_from, date_to,
                enable_eval=request.form.get("enable_eval") == "on",
                enable_push=request.form.get("enable_push") == "on",
            )
            session["enable_eval"] = request.form.get("enable_eval") == "on"
            session["enable_push"] = request.form.get("enable_push") == "on"
            if not result["ok"]:
                flash(result["error"], "error")
            else:
                _persist_engine(eng)
                flash(f"Calculated and archived {result['count']} employees.", "success")
                return redirect(url_for("results"))

    return render_template(
        "upload.html",
        date_from=date_from,
        date_to=date_to,
        has_main=eng.raw_df is not None or session.get("has_main"),
        has_eval=eng.eval_df is not None or session.get("has_eval"),
        has_push=eng.push_df is not None or session.get("has_push"),
    )


@app.route("/results")
@login_required
def results():
    eng = get_engine()
    q = request.args.get("q", "")
    branch = request.args.get("branch", "All Branches")
    job = request.args.get("job", "All Jobs")
    shift = request.args.get("shift", "All Shifts")
    include_unknown = request.args.get("include_unknown", "1") == "1"
    rows = eng.filter_results(q, branch, job, shift, include_unknown)
    return render_template(
        "results.html",
        rows=rows,
        columns=RESULT_COLUMNS,
        branches=eng.get_branches() if eng.all_results else ["All Branches"],
        jobs=eng.get_jobs() if eng.all_results else ["All Jobs"],
        shifts=["All Shifts", "Morning Shift", "Evening Shift", "Night Shift", "Random"],
        filters={"q": q, "branch": branch, "job": job, "shift": shift, "include_unknown": include_unknown},
        has_data=bool(eng.all_results),
    )


@app.route("/results/delete/<code>", methods=["POST"])
@login_required
def delete_unknown(code):
    eng = get_engine()
    eng.delete_unknown_employee(code)
    _persist_engine(eng)
    flash("Unknown employee removed.", "success")
    return redirect(url_for("results"))


@app.route("/export/results")
@login_required
def export_results():
    eng = get_engine()
    if not eng.all_results:
        flash("No data to export.", "error")
        return redirect(url_for("results"))
    q = request.args.get("q", "")
    branch = request.args.get("branch", "All Branches")
    job = request.args.get("job", "All Jobs")
    shift = request.args.get("shift", "All Shifts")
    include_unknown = request.args.get("include_unknown", "1") == "1"
    rows = eng.filter_results(q, branch, job, shift, include_unknown)
    path = eng.export_dataframe(rows, RESULT_COLUMNS, "KPI_Results")
    return send_file(path, as_attachment=True, download_name="KPI_Results.xlsx")


@app.route("/detailed")
@login_required
def detailed():
    eng = get_engine()
    q = request.args.get("q", "")
    branch = request.args.get("branch", "All Branches")
    job = request.args.get("job", "All Jobs")
    code = request.args.get("code", "")
    suggestions = eng.get_employee_suggestions(q, branch, job) if eng.all_results else []
    selected = None
    detail_rows = []
    if code:
        emp_info = next((r for r in eng.all_results if str(r[1]) == code), None)
        if emp_info:
            selected = {
                "name": emp_info[0], "code": emp_info[1],
                "job": emp_info[2], "branch": emp_info[3],
            }
            detail_rows = eng.get_employee_detail(emp_info[0])
    return render_template(
        "detailed.html",
        suggestions=suggestions,
        selected=selected,
        detail_rows=detail_rows,
        branches=eng.get_branches() if eng.all_results else ["All Branches"],
        jobs=eng.get_jobs() if eng.all_results else ["All Jobs"],
        filters={"q": q, "branch": branch, "job": job, "code": code},
        has_data=bool(eng.all_results),
    )


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    eng = get_engine()
    if request.method == "POST":
        action = request.form.get("action", "save")
        if action == "import" and "logic_file" in request.files:
            f = request.files["logic_file"]
            if f.filename:
                import json
                new_logic = json.load(f)
                eng.save_logic(new_logic)
                flash("Logic template imported successfully!", "success")
        else:
            try:
                new_logic = eng.parse_logic_from_form(request.form)
                eng.save_logic(new_logic)
                flash("Settings saved!", "success")
                if action == "recalculate" and (eng.raw_df is not None or session.get("has_main")):
                    _restore_engine(eng)
                    d_from = session.get("date_from", "")
                    d_to = session.get("date_to", "")
                    if d_from and d_to:
                        result = eng.process_data(d_from, d_to, eng.enable_eval, eng.enable_push)
                        if result["ok"]:
                            _persist_engine(eng)
                            flash(f"Recalculated {result['count']} employees.", "success")
                            return redirect(url_for("results"))
                        flash(result["error"], "error")
                    else:
                        flash("Please load data in Upload tab first.", "warning")
            except Exception:
                flash("Check your inputs — invalid numbers.", "error")

    categories = []
    for cat_k, cat_n in SETTINGS_CATEGORIES:
        metrics = []
        for met_k, met_n in eng.get_settings_metrics(cat_k):
            tiers = eng.kpi_logic.get(cat_k, {}).get(met_k, [])
            if not tiers:
                tiers = [{"target": 0, "points": 0}]
            prev = 0
            tier_rows = []
            for tier in tiers:
                tier_rows.append({"from": prev, "target": tier["target"], "points": tier["points"]})
                try:
                    prev = int(float(tier["target"])) + 1
                except Exception:
                    prev = ""
            metrics.append({"key": met_k, "name": met_n, "tiers": tier_rows, "form_key": f"{cat_k}_{met_k}"})
        categories.append({"key": cat_k, "name": cat_n, "metrics": metrics})

    return render_template("settings.html", categories=categories)


@app.route("/export/logic")
@login_required
def export_logic():
    eng = get_engine()
    import json
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json", prefix="KPI_Template")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eng.kpi_logic, f, indent=4)
    return send_file(path, as_attachment=True, download_name="KPI_Template.json")


@app.route("/history")
@login_required
def history():
    eng = get_engine()
    summary = eng.load_history_summary()
    datasets, mapping = eng.get_saved_datasets()
    session["dataset_mapping"] = mapping
    return render_template(
        "history.html",
        summary=summary,
        datasets=datasets if datasets else ["No saved datasets"],
    )


@app.route("/history/<saved_at>")
@login_required
def history_detail(saved_at):
    eng = get_engine()
    cols, rows = eng.load_history_detail(saved_at)
    return render_template("history_detail.html", saved_at=saved_at, columns=cols, rows=rows)


@app.route("/history/export/<saved_at>")
@login_required
def history_export(saved_at):
    eng = get_engine()
    cols, rows = eng.load_history_detail(saved_at)
    safe_name = saved_at.replace(":", "-")
    path = eng.export_dataframe(rows, cols, f"Archived_KPI_{safe_name}")
    return send_file(path, as_attachment=True, download_name=f"Archived_KPI_{safe_name}.xlsx")


@app.route("/history/recalc", methods=["POST"])
@login_required
def history_recalc():
    eng = get_engine()
    sel = request.form.get("dataset", "")
    mapping = session.get("dataset_mapping", {})
    if not mapping:
        _, mapping = eng.get_saved_datasets()
    eng.enable_eval = session.get("enable_eval", False)
    eng.enable_push = session.get("enable_push", False)
    result = eng.recalc_dataset(sel, mapping)
    if result["ok"]:
        session["date_from"] = result.get("start", "")
        session["date_to"] = result.get("end", "")
        _persist_engine(eng)
        flash("Dataset recalculated successfully!", "success")
        return redirect(url_for("results"))
    flash(result["error"], "error")
    return redirect(url_for("history"))


@app.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    eng = get_engine()
    p2_from = session.get("p2_from", "")
    p2_to = session.get("p2_to", "")

    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "load_p2" and "p2_file" in request.files:
            f = request.files["p2_file"]
            if f.filename:
                path = save_upload(f)
                eng.raw_df_p2 = eng.read_file(path)
                p2_from, p2_to = eng.guess_date_range(eng.raw_df_p2)
                session["p2_from"] = p2_from
                session["p2_to"] = p2_to
                _persist_engine(eng)
                flash("Period 2 data loaded!", "success")
        elif action == "run_compare":
            _restore_engine(eng)
            p2_from = parse_iso_date_from_form(request.form, "p2_from")
            p2_to = parse_iso_date_from_form(request.form, "p2_to")
            session["p2_from"] = p2_from
            session["p2_to"] = p2_to
            result = eng.process_comparison(p2_from, p2_to)
            if result["ok"]:
                _persist_engine(eng)
                flash(f"Comparison completed for {result['count']} employees.", "success")
            else:
                flash(result["error"], "error")

    q = request.args.get("q", "")
    branch = request.args.get("branch", "All Branches")
    job = request.args.get("job", "All Jobs")
    rows = eng.filter_comp_results(q, branch, job) if eng.comp_results_data else []

    return render_template(
        "compare.html",
        rows=rows,
        columns=COMPARE_COLUMNS,
        branches=eng.get_branches() if eng.all_results else ["All Branches"],
        jobs=eng.get_jobs() if eng.all_results else ["All Jobs"],
        filters={"q": q, "branch": branch, "job": job},
        p2_from=p2_from,
        p2_to=p2_to,
        has_p1=bool(eng.all_results),
        has_p2=eng.raw_df_p2 is not None or session.get("has_p2"),
        has_comp=bool(eng.comp_results_data),
    )


@app.route("/export/compare")
@login_required
def export_compare():
    eng = get_engine()
    if not eng.comp_results_data:
        flash("No comparison data to export.", "error")
        return redirect(url_for("compare"))
    q = request.args.get("q", "")
    branch = request.args.get("branch", "All Branches")
    job = request.args.get("job", "All Jobs")
    rows = eng.filter_comp_results(q, branch, job)
    path = eng.export_dataframe(rows, COMPARE_COLUMNS, "KPI_Compare")
    return send_file(path, as_attachment=True, download_name="KPI_Compare.xlsx")


@app.route("/templates/<name>")
@login_required
def download_template(name):
    eng = get_engine()
    if name == "eval":
        path = eng.make_eval_template()
        return send_file(path, as_attachment=True, download_name="Evaluation_Template.xlsx")
    if name == "push":
        path = eng.make_push_template()
        return send_file(path, as_attachment=True, download_name="PushList_Template.xlsx")
    flash("Unknown template.", "error")
    return redirect(url_for("upload"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20000, debug=False)
