import os
import pandas as pd
from flask import Flask, render_template, jsonify

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
