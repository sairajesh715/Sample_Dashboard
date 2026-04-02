import os
import pandas as pd
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Load data from CSV files (exported from MySQL raj_db)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_data():
    geo = pd.read_csv(os.path.join(DATA_DIR, "geo.csv"))
    people = pd.read_csv(os.path.join(DATA_DIR, "people.csv"))
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    shipments = pd.read_csv(os.path.join(DATA_DIR, "shipments.csv"))

    # Merge shipments with dimension tables
    df = shipments.merge(people, left_on="Sales Person", right_on="SP ID", how="left")
    df = df.merge(geo, left_on="Geo", right_on="GeoID", how="left")
    df = df.merge(products, left_on="Product", right_on="Product ID", how="left")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    return df

DF = load_data()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
def summary():
    total_revenue = int(DF["Amount"].sum())
    total_boxes = int(DF["Boxes"].sum())
    total_shipments = len(DF)
    total_salespeople = DF["Sales Person_x"].nunique() if "Sales Person_x" in DF.columns else DF["Sales Person"].nunique()
    avg_revenue_per_shipment = round(total_revenue / total_shipments, 2)
    return jsonify({
        "total_revenue": total_revenue,
        "total_boxes": total_boxes,
        "total_shipments": total_shipments,
        "total_salespeople": total_salespeople,
        "avg_revenue_per_shipment": avg_revenue_per_shipment,
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
    col = "Geo_y" if "Geo_y" in DF.columns else "Geo"
    grouped = DF.groupby(col)["Amount"].sum().reset_index()
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
    col = "Product_y" if "Product_y" in DF.columns else "Product"
    grouped = DF.groupby(col)["Amount"].sum().reset_index()
    grouped.columns = ["product", "revenue"]
    grouped = grouped.sort_values("revenue", ascending=False).head(10)
    return jsonify({
        "labels": grouped["product"].tolist(),
        "values": grouped["revenue"].tolist(),
    })


@app.route("/api/top-salespeople")
def top_salespeople():
    col = "Sales Person_y" if "Sales Person_y" in DF.columns else "Sales Person"
    grouped = DF.groupby(col)["Amount"].sum().reset_index()
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
