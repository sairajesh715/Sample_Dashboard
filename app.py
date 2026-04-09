import os
import pandas as pd
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, "hr_data.csv"))
    df["HireDate"] = pd.to_datetime(df["HireDate"])
    df["HireMonth"] = df["HireDate"].dt.to_period("M").astype(str)

    age_bins   = [20, 25, 30, 35, 40, 45, 50, 56, 65]
    age_labels = ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-55", "56+"]
    df["AgeGroup"] = pd.cut(df["Age"], bins=age_bins, labels=age_labels, right=False)

    ten_bins   = [0, 2, 5, 8, 12, 50]
    ten_labels = ["0-1 yr", "2-4 yr", "5-7 yr", "8-11 yr", "12+ yr"]
    df["TenureGroup"] = pd.cut(df["YearsAtCompany"], bins=ten_bins, labels=ten_labels, right=False)
    return df


DF = load_data()


# ── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ── KPI Summary ───────────────────────────────────────────────────────────────

@app.route("/api/hr/summary")
def hr_summary():
    total      = len(DF)
    attrition  = int((DF["Attrition"] == "Yes").sum())
    male       = int((DF["Gender"] == "Male").sum())
    female     = int((DF["Gender"] == "Female").sum())
    return jsonify({
        "total_employees":  total,
        "active_employees": total - attrition,
        "attrition_count":  attrition,
        "attrition_rate":   round(attrition / total * 100, 1),
        "avg_salary":       int(DF["Salary"].mean()),
        "avg_age":          round(DF["Age"].mean(), 1),
        "male_count":       male,
        "female_count":     female,
        "avg_tenure":       round(DF["YearsAtCompany"].mean(), 1),
        "dept_count":       int(DF["Department"].nunique()),
    })


# ── Workforce Overview ────────────────────────────────────────────────────────

@app.route("/api/hr/headcount-by-dept")
def headcount_by_dept():
    g = DF.groupby("Department").size().reset_index(name="count")
    g = g.sort_values("count", ascending=False)
    return jsonify({"labels": g["Department"].tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/gender-distribution")
def gender_distribution():
    g = DF["Gender"].value_counts().reset_index()
    g.columns = ["gender", "count"]
    return jsonify({"labels": g["gender"].tolist(), "values": g["count"].tolist()})


# ── Demographics ──────────────────────────────────────────────────────────────

@app.route("/api/hr/age-distribution")
def age_distribution():
    g = DF.groupby("AgeGroup", observed=False).size().reset_index(name="count")
    return jsonify({"labels": g["AgeGroup"].astype(str).tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/education-distribution")
def education_distribution():
    mapping = {1: "Below College", 2: "College", 3: "Bachelor", 4: "Master", 5: "Doctorate"}
    g = DF["Education"].value_counts().sort_index().reset_index()
    g.columns = ["level", "count"]
    g["label"] = g["level"].map(mapping)
    return jsonify({"labels": g["label"].tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/tenure-distribution")
def tenure_distribution():
    g = DF.groupby("TenureGroup", observed=False).size().reset_index(name="count")
    return jsonify({"labels": g["TenureGroup"].astype(str).tolist(), "values": g["count"].tolist()})


# ── Attrition Analysis ────────────────────────────────────────────────────────

@app.route("/api/hr/attrition-by-dept")
def attrition_by_dept():
    total = DF.groupby("Department").size()
    left  = DF[DF["Attrition"] == "Yes"].groupby("Department").size().reindex(total.index, fill_value=0)
    rate  = (left / total * 100).round(1).reset_index()
    rate.columns = ["Department", "Rate"]
    rate  = rate.sort_values("Rate", ascending=False)
    return jsonify({"labels": rate["Department"].tolist(), "values": rate["Rate"].tolist()})


@app.route("/api/hr/attrition-by-age")
def attrition_by_age():
    total = DF.groupby("AgeGroup", observed=False).size()
    left  = DF[DF["Attrition"] == "Yes"].groupby("AgeGroup", observed=False).size()
    rate  = (left / total * 100).round(1).reset_index()
    rate.columns = ["AgeGroup", "Rate"]
    rate["AgeGroup"] = rate["AgeGroup"].astype(str)
    return jsonify({"labels": rate["AgeGroup"].tolist(), "values": rate["Rate"].tolist()})


# ── Recruitment ───────────────────────────────────────────────────────────────

@app.route("/api/hr/monthly-hiring")
def monthly_hiring():
    g = DF.groupby("HireMonth").size().reset_index(name="count")
    g = g.sort_values("HireMonth")
    return jsonify({"labels": g["HireMonth"].tolist(), "values": g["count"].tolist()})


# ── Performance & Satisfaction ────────────────────────────────────────────────

@app.route("/api/hr/performance-distribution")
def performance_distribution():
    mapping = {1: "Low", 2: "Good", 3: "Excellent", 4: "Outstanding"}
    g = DF["PerformanceRating"].value_counts().sort_index().reset_index()
    g.columns = ["rating", "count"]
    g["label"] = g["rating"].map(mapping)
    return jsonify({"labels": g["label"].tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/worklife-balance")
def worklife_balance():
    mapping = {1: "Low", 2: "Fair", 3: "Good", 4: "Excellent"}
    g = DF["WorkLifeBalance"].value_counts().sort_index().reset_index()
    g.columns = ["level", "count"]
    g["label"] = g["level"].map(mapping)
    return jsonify({"labels": g["label"].tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/overtime-distribution")
def overtime_distribution():
    g = DF["OverTime"].value_counts().reset_index()
    g.columns = ["overtime", "count"]
    return jsonify({"labels": g["overtime"].tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/satisfaction-by-dept")
def satisfaction_by_dept():
    mapping   = {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
    g         = DF.groupby(["Department", "JobSatisfaction"]).size().reset_index(name="count")
    depts     = sorted(DF["Department"].unique().tolist())
    datasets  = {}
    for level, label in mapping.items():
        sub  = g[g["JobSatisfaction"] == level]
        d    = dict(zip(sub["Department"], sub["count"]))
        datasets[label] = [int(d.get(dept, 0)) for dept in depts]
    return jsonify({"labels": depts, "datasets": datasets})


# ── Compensation & Work Patterns ──────────────────────────────────────────────

@app.route("/api/hr/salary-by-dept")
def salary_by_dept():
    g = DF.groupby("Department")["Salary"].mean().round(0).reset_index()
    g.columns = ["dept", "avg_salary"]
    g = g.sort_values("avg_salary", ascending=False)
    return jsonify({"labels": g["dept"].tolist(), "values": g["avg_salary"].astype(int).tolist()})


@app.route("/api/hr/travel-distribution")
def travel_distribution():
    g = DF["BusinessTravel"].value_counts().reset_index()
    g.columns = ["travel", "count"]
    return jsonify({"labels": g["travel"].tolist(), "values": g["count"].tolist()})


@app.route("/api/hr/employees")
def get_employees():
    """Return paginated/filtered employee records for drill-down modals and Excel export."""
    try:
        ftype    = request.args.get("filter_type",  "all")
        fvalue   = request.args.get("filter_value", "")
        sort_by  = request.args.get("sort_by", "")
        # per_page=9999 is used by the Excel export to fetch all rows at once
        try:
            per_page = max(1, min(int(request.args.get("per_page", 15)), 9999))
            page     = max(1, int(request.args.get("page", 1)))
        except (ValueError, TypeError):
            per_page, page = 15, 1

        df = DF.copy()

        if ftype == "department":
            df = df[df["Department"] == fvalue]
        elif ftype == "gender":
            df = df[df["Gender"] == fvalue]
        elif ftype == "age_group":
            df = df[df["AgeGroup"].astype(str) == fvalue]
        elif ftype == "education":
            edu_map = {"Below College": 1, "College": 2, "Bachelor": 3, "Master": 4, "Doctorate": 5}
            df = df[df["Education"] == edu_map.get(fvalue, -1)]
        elif ftype == "tenure":
            df = df[df["TenureGroup"].astype(str) == fvalue]
        elif ftype == "performance":
            perf_map = {"Low": 1, "Good": 2, "Excellent": 3, "Outstanding": 4}
            df = df[df["PerformanceRating"] == perf_map.get(fvalue, -1)]
        elif ftype == "wlb":
            wlb_map = {"Low": 1, "Fair": 2, "Good": 3, "Excellent": 4}
            df = df[df["WorkLifeBalance"] == wlb_map.get(fvalue, -1)]
        elif ftype == "overtime":
            df = df[df["OverTime"] == fvalue]
        elif ftype == "satisfaction":
            sat_map = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
            df = df[df["JobSatisfaction"] == sat_map.get(fvalue, -1)]
        elif ftype == "travel":
            df = df[df["BusinessTravel"] == fvalue]
        elif ftype == "attrition":
            df = df[df["Attrition"] == fvalue]
        elif ftype == "attrition_dept":
            df = df[(df["Department"] == fvalue) & (df["Attrition"] == "Yes")]
        elif ftype == "attrition_age":
            df = df[(df["AgeGroup"].astype(str) == fvalue) & (df["Attrition"] == "Yes")]
        elif ftype == "hire_month":
            df = df[df["HireMonth"] == fvalue]
        # "all" — no filter applied

        if sort_by == "salary":
            df = df.sort_values("Salary", ascending=False)
        elif sort_by == "age":
            df = df.sort_values("Age")
        elif sort_by == "years":
            df = df.sort_values("YearsAtCompany", ascending=False)

        total       = int(len(df))
        total_pages = max(1, (total + per_page - 1) // per_page)
        page        = min(page, total_pages)
        df_page     = df.iloc[(page - 1) * per_page: page * per_page]

        perf_labels = {1: "Low", 2: "Good", 3: "Excellent", 4: "Outstanding"}
        sat_labels  = {1: "Low", 2: "Medium", 3: "High",    4: "Very High"}

        records = []
        for _, r in df_page.iterrows():
            records.append({
                "id":           int(r["EmployeeID"]),
                "name":         str(r["Name"]),
                "department":   str(r["Department"]),
                "job_title":    str(r["JobTitle"]),
                "age":          int(r["Age"]),
                "gender":       str(r["Gender"]),
                "salary":       int(r["Salary"]),
                "years":        int(r["YearsAtCompany"]),
                "performance":  perf_labels.get(int(r["PerformanceRating"]), "—"),
                "satisfaction": sat_labels.get(int(r["JobSatisfaction"]), "—"),
                "attrition":    str(r["Attrition"]),
                "overtime":     str(r["OverTime"]),
            })

        # FIX: float() before round() ensures Python float, not numpy.float64
        # (numpy.float64 is not JSON-serializable by Flask's default encoder)
        avg_sal   = int(float(df["Salary"].mean()))                      if total > 0 else 0
        avg_age   = round(float(df["Age"].mean()), 1)                    if total > 0 else 0.0
        attr_rate = round(float((df["Attrition"] == "Yes").mean()) * 100, 1) if total > 0 else 0.0
        avg_ten   = round(float(df["YearsAtCompany"].mean()), 1)         if total > 0 else 0.0

        return jsonify({
            "total":       total,
            "page":        int(page),
            "total_pages": int(total_pages),
            "records":     records,
            "stats": {
                "avg_salary":     avg_sal,
                "avg_age":        avg_age,
                "attrition_rate": attr_rate,
                "avg_tenure":     avg_ten,
            },
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "detail": traceback.format_exc()}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
