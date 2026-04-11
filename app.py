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


@app.route("/dashboard-v2")
def dashboard_v2():
    return render_template("dashboard_v2.html")


@app.route("/api/hr/powerbi")
def hr_powerbi():
    """Single endpoint returning all aggregations for the Power BI-style dashboard,
    filtered by optional query params: dept, gender, travel, overtime, attrition."""
    dept        = request.args.get("dept",       "All")
    gender      = request.args.get("gender",     "All")
    travel      = request.args.get("travel",     "All")
    overtime    = request.args.get("overtime",   "All")
    attrition   = request.args.get("attrition",  "All")
    age_group   = request.args.get("age_group",  "All")
    perf        = request.args.get("perf",        "All")
    wlb_level   = request.args.get("wlb_level",  "All")
    tenure_grp  = request.args.get("tenure_grp", "All")

    df = DF.copy()
    if dept       != "All": df = df[df["Department"]        == dept]
    if gender     != "All": df = df[df["Gender"]            == gender]
    if travel     != "All": df = df[df["BusinessTravel"]    == travel]
    if overtime   != "All": df = df[df["OverTime"]          == overtime]
    if attrition  != "All": df = df[df["Attrition"]         == attrition]
    if age_group  != "All": df = df[df["AgeGroup"].astype(str) == age_group]
    if perf       != "All":
        perf_rev = {"Low":1,"Good":2,"Excellent":3,"Outstanding":4}
        if perf in perf_rev: df = df[df["PerformanceRating"] == perf_rev[perf]]
    if wlb_level  != "All":
        wlb_rev  = {"Low":1,"Fair":2,"Good":3,"Excellent":4}
        if wlb_level in wlb_rev: df = df[df["WorkLifeBalance"] == wlb_rev[wlb_level]]
    if tenure_grp != "All": df = df[df["TenureGroup"].astype(str) == tenure_grp]

    total    = len(df)
    attr_n   = int((df["Attrition"] == "Yes").sum())
    attr_r   = round(attr_n / total * 100, 1) if total else 0.0
    avg_sal  = int(df["Salary"].mean())        if total else 0
    avg_ten  = round(float(df["YearsAtCompany"].mean()), 1) if total else 0.0
    avg_age  = round(float(df["Age"].mean()), 1)            if total else 0.0

    # Headcount by dept
    hc = df.groupby("Department").size().reset_index(name="n").sort_values("n", ascending=False)

    # Attrition rate by dept
    tot_d  = DF.groupby("Department").size()
    left_d = DF[DF["Attrition"]=="Yes"].groupby("Department").size().reindex(tot_d.index, fill_value=0)
    attr_d = (left_d / tot_d * 100).round(1).reset_index()
    attr_d.columns = ["Department","Rate"]
    attr_d = attr_d.set_index("Department")

    # Avg salary by dept
    sal_d = df.groupby("Department")["Salary"].mean().round(0).astype(int)

    dept_labels = hc["Department"].tolist()

    # Age distribution
    age_g = df.groupby("AgeGroup", observed=False).size().reset_index(name="n")

    # Performance
    perf_map = {1:"Low",2:"Good",3:"Excellent",4:"Outstanding"}
    perf_g = df["PerformanceRating"].value_counts().sort_index().reset_index()
    perf_g.columns = ["r","n"]
    perf_g["label"] = perf_g["r"].map(perf_map)

    # Gender
    gen_g = df["Gender"].value_counts().reset_index()
    gen_g.columns = ["g","n"]

    # WLB
    wlb_map = {1:"Low",2:"Fair",3:"Good",4:"Excellent"}
    wlb_g = df["WorkLifeBalance"].value_counts().sort_index().reset_index()
    wlb_g.columns = ["l","n"]
    wlb_g["label"] = wlb_g["l"].map(wlb_map)

    # OT
    ot_g = df["OverTime"].value_counts().reset_index()
    ot_g.columns = ["o","n"]

    # Tenure
    ten_g = df.groupby("TenureGroup", observed=False).size().reset_index(name="n")

    # Smart insights
    insights = []
    if total > 0:
        top_dept = hc.iloc[0]["Department"] if len(hc) else "N/A"
        insights.append(f"<b>{top_dept}</b> is the largest department with <b>{int(hc.iloc[0]['n'])}</b> employees.")
        if len(attr_d):
            worst = attr_d["Rate"].idxmax()
            insights.append(f"Highest attrition is in <b>{worst}</b> at <b>{attr_d.loc[worst,'Rate']}%</b>.")
        if (df["OverTime"]=="Yes").sum() > 0:
            ot_pct = round((df["OverTime"]=="Yes").mean()*100,1)
            insights.append(f"<b>{ot_pct}%</b> of employees work overtime — a key attrition risk factor.")
        top_sal_dept = sal_d.idxmax() if len(sal_d) else "N/A"
        insights.append(f"<b>{top_sal_dept}</b> leads in avg salary at <b>${sal_d.max():,}</b>.")
        male_pct = round((df["Gender"]=="Male").mean()*100,1) if total else 0
        insights.append(f"Workforce is <b>{male_pct}%</b> male / <b>{round(100-male_pct,1)}%</b> female.")

    return jsonify({
        "kpi": {
            "total": total, "active": total - attr_n,
            "attrition_count": attr_n, "attrition_rate": attr_r,
            "avg_salary": avg_sal, "avg_age": avg_age, "avg_tenure": avg_ten,
        },
        "headcount_by_dept": {
            "labels": dept_labels,
            "headcount": hc["n"].tolist(),
            "attrition_rate": [float(attr_d.loc[d,"Rate"]) if d in attr_d.index else 0 for d in dept_labels],
            "avg_salary": [int(sal_d.get(d, 0)) for d in dept_labels],
        },
        "age_dist":  {"labels": age_g["AgeGroup"].astype(str).tolist(), "values": age_g["n"].tolist()},
        "perf_dist": {"labels": perf_g["label"].tolist(),  "values": perf_g["n"].tolist()},
        "gender":    {"labels": gen_g["g"].tolist(),        "values": gen_g["n"].tolist()},
        "wlb":       {"labels": wlb_g["label"].tolist(),    "values": wlb_g["n"].tolist()},
        "overtime":  {"labels": ot_g["o"].tolist(),         "values": ot_g["n"].tolist()},
        "tenure":    {"labels": ten_g["TenureGroup"].astype(str).tolist(), "values": ten_g["n"].tolist()},
        "insights":  insights,
        "filter_options": {
            "departments": sorted(DF["Department"].unique().tolist()),
            "genders":     sorted(DF["Gender"].unique().tolist()),
            "travel":      sorted(DF["BusinessTravel"].unique().tolist()),
        },
    })


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
