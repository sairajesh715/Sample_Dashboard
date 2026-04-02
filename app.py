import os
import pandas as pd
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_data():
    geo = pd.read_csv(os.path.join(DATA_DIR, "geo.csv"))
    people = pd.read_csv(os.path.join(DATA_DIR, "people.csv"))
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    shipments = pd.read_csv(os.path.join(DATA_DIR, "shipments.csv"))

    df = shipments.merge(people, left_on="Sales Person", right_on="SP ID", how="left")
    df = df.merge(geo, left_on="Geo", right_on="GeoID", how="left")
    df = df.merge(products, left_on="Product", right_on="Product ID", how="left")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    return df


DF = load_data()

# Resolve column names after merge
COL_COUNTRY = "Geo_y" if "Geo_y" in DF.columns else "Geo"
COL_PRODUCT = "Product_y" if "Product_y" in DF.columns else "Product"
COL_PERSON = "Sales Person_y" if "Sales Person_y" in DF.columns else "Sales Person"


@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/summary")
def summary():
    total_revenue = int(DF["Amount"].sum())
    total_boxes = int(DF["Boxes"].sum())
    total_shipments = len(DF)
    total_salespeople = DF[COL_PERSON].nunique()
    avg_revenue_per_shipment = round(total_revenue / total_shipments, 2)
    top_product = DF.groupby(COL_PRODUCT)["Amount"].sum().idxmax()
    top_country = DF.groupby(COL_COUNTRY)["Amount"].sum().idxmax()
    return jsonify({
        "total_revenue": total_revenue,
        "total_boxes": total_boxes,
        "total_shipments": total_shipments,
        "total_salespeople": total_salespeople,
        "avg_revenue_per_shipment": avg_revenue_per_shipment,
        "top_product": top_product,
        "top_country": top_country,
    })


@app.route("/api/revenue-by-month")
def revenue_by_month():
    grouped = DF.groupby("Month").agg({"Amount": "sum", "Boxes": "sum"}).reset_index()
    grouped = grouped.sort_values("Month")
    return jsonify({
        "labels": grouped["Month"].tolist(),
        "revenue": grouped["Amount"].tolist(),
        "boxes": grouped["Boxes"].tolist(),
    })


@app.route("/api/revenue-by-country")
def revenue_by_country():
    grouped = DF.groupby(COL_COUNTRY)["Amount"].sum().reset_index()
    grouped.columns = ["country", "revenue"]
    grouped = grouped.sort_values("revenue", ascending=False)
    return jsonify({
        "labels": grouped["country"].tolist(),
        "values": grouped["revenue"].tolist(),
    })


@app.route("/api/revenue-by-category")
def revenue_by_category():
    grouped = DF.groupby("Category")["Amount"].sum().reset_index()
    grouped = grouped.sort_values("Amount", ascending=False)
    return jsonify({
        "labels": grouped["Category"].tolist(),
        "values": grouped["Amount"].tolist(),
    })


@app.route("/api/top-products")
def top_products():
    grouped = DF.groupby(COL_PRODUCT)["Amount"].sum().reset_index()
    grouped.columns = ["product", "revenue"]
    grouped = grouped.sort_values("revenue", ascending=False).head(10)
    return jsonify({
        "labels": grouped["product"].tolist(),
        "values": grouped["revenue"].tolist(),
    })


@app.route("/api/top-salespeople")
def top_salespeople():
    grouped = DF.groupby(COL_PERSON)["Amount"].sum().reset_index()
    grouped.columns = ["person", "revenue"]
    grouped = grouped.sort_values("revenue", ascending=False).head(10)
    return jsonify({
        "labels": grouped["person"].tolist(),
        "values": grouped["revenue"].tolist(),
    })


@app.route("/api/revenue-by-team")
def revenue_by_team():
    grouped = DF.groupby("Team")["Amount"].sum().reset_index()
    grouped = grouped.sort_values("Amount", ascending=False)
    return jsonify({
        "labels": grouped["Team"].tolist(),
        "values": grouped["Amount"].tolist(),
    })


@app.route("/api/revenue-by-region")
def revenue_by_region():
    grouped = DF.groupby("Region")["Amount"].sum().reset_index()
    grouped = grouped.sort_values("Amount", ascending=False)
    return jsonify({
        "labels": grouped["Region"].tolist(),
        "values": grouped["Amount"].tolist(),
    })


@app.route("/api/monthly-trend-by-region")
def monthly_trend_by_region():
    grouped = DF.groupby(["Month", "Region"])["Amount"].sum().reset_index()
    grouped = grouped.sort_values("Month")
    regions = grouped["Region"].unique().tolist()
    months = sorted(grouped["Month"].unique().tolist())
    datasets = {}
    for region in regions:
        region_data = grouped[grouped["Region"] == region]
        region_dict = dict(zip(region_data["Month"], region_data["Amount"]))
        datasets[region] = [int(region_dict.get(m, 0)) for m in months]
    return jsonify({"labels": months, "datasets": datasets})


@app.route("/api/drilldown")
def drilldown():
    """Return detailed rows when user clicks a chart data point."""
    chart = request.args.get("chart", "")
    value = request.args.get("value", "")
    if not chart or not value:
        return jsonify({"rows": [], "columns": []})

    filters = {
        "country": (COL_COUNTRY, value),
        "category": ("Category", value),
        "product": (COL_PRODUCT, value),
        "person": (COL_PERSON, value),
        "team": ("Team", value),
        "region": ("Region", value),
        "month": ("Month", value),
    }

    if chart not in filters:
        return jsonify({"rows": [], "columns": []})

    col, val = filters[chart]
    subset = DF[DF[col] == val].copy()
    subset["Date"] = subset["Date"].dt.strftime("%Y-%m-%d")

    display_cols = ["Date", COL_PERSON, COL_COUNTRY, COL_PRODUCT, "Category", "Team", "Amount", "Boxes"]
    rename = {COL_PERSON: "Sales Person", COL_COUNTRY: "Country", COL_PRODUCT: "Product"}
    out = subset[display_cols].rename(columns=rename)
    out = out.sort_values("Amount", ascending=False).head(50)

    return jsonify({
        "columns": out.columns.tolist(),
        "rows": out.values.tolist(),
        "total_rows": len(subset),
        "shown": min(50, len(subset)),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
