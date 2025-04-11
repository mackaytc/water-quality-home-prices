"""
===============================================================================
 Title: 01-data-cleaning-home-prices.py
 Description:
     Cleans and reshapes the Zillow zip-code level home price data and checks
     availability relative to all California zip codes. 
===============================================================================
"""

# -----------------------------------------------------------------------------
# Import Libraries and Config
# -----------------------------------------------------------------------------
import os
import re
import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# Run central config file to reference project directories - if you're running
# this interactively, uncomment below and set wd to code directory 

sys.path.append(r"C:\Users\macka\github-repos\water-quality-home-prices\code")

import config

# -----------------------------------------------------------------------------
# Load Home Price Data
# -----------------------------------------------------------------------------
zillow_file = os.path.join(
    config.RAW_HOME_PRICE_DIR,
    "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)

zip_data = pd.read_csv(zillow_file)
print(f"Total rows read: {len(zip_data):,}")

# -----------------------------------------------------------------------------
# Filter for California Only
# -----------------------------------------------------------------------------
ca_zip_data = zip_data[zip_data["State"] == "CA"].copy()
n_unique_zips = ca_zip_data["RegionName"].nunique()
print(f"Number of unique CA zip codes in Zillow data: {n_unique_zips:,}")

# -----------------------------------------------------------------------------
# Reshape Data (Wide -> Long)
# -----------------------------------------------------------------------------
# Identify columns that begin with digits (i.e., date columns)
date_cols = [c for c in ca_zip_data.columns if re.match(r'^\d', c)]

ca_zip_data_long = ca_zip_data.melt(
    id_vars=[col for col in ca_zip_data.columns if col not in date_cols],
    value_vars=date_cols,
    var_name="Date",
    value_name="Value"
)

# Convert Date strings to datetime (adjust format if necessary)
ca_zip_data_long["Date"] = pd.to_datetime(
    ca_zip_data_long["Date"],
    format="%Y-%m-%d",
    errors="coerce"
)

print("Long data shape:", ca_zip_data_long.shape)

# -----------------------------------------------------------------------------
# Check for Balanced Panel and Missing Values
# -----------------------------------------------------------------------------
ca_zip_data_long["n_rows"] = (
    ca_zip_data_long.groupby("RegionName")["RegionName"].transform("size")
)

ca_zip_data_long["n_missing_rows"] = (
    ca_zip_data_long.groupby("RegionName")["Value"].transform(lambda x: x.isna().sum())
)

print("\nSummary of 'n_rows' per zip code:")
print(ca_zip_data_long["n_rows"].describe())

print("\nSummary of 'n_missing_rows' per zip code:")
print(ca_zip_data_long["n_missing_rows"].describe())

# -----------------------------------------------------------------------------
# Final Data Cleaning (Year/Month Columns, Rename, Select)
# -----------------------------------------------------------------------------
ca_zip_data_long["year"] = ca_zip_data_long["Date"].dt.year
ca_zip_data_long["month"] = ca_zip_data_long["Date"].dt.month

# Rename columns to mimic your R approach
ca_zip_data_long.rename(
    columns={
        "RegionName":  "zip_code",
        "CountyName":  "county_name",
        "Value":       "avg_home_price"
    },
    inplace=True
)

# Rename all columns to lowercase
ca_zip_data_long.columns = [col.lower() for col in ca_zip_data_long.columns]

# Keep only relevant columns
CA_home_price_panel = ca_zip_data_long[
    ["zip_code", "city", "metro", "county_name", "date", "avg_home_price", "year", "month"]
].copy()

# -----------------------------------------------------------------------------
# Save Final Data
# -----------------------------------------------------------------------------
output_file = os.path.join(config.PROCESSED_DATA_DIR, "CA_home_price_panel.csv")
CA_home_price_panel.to_csv(output_file, index=False)
print(f"\nFinal cleaned dataset saved to:\n{output_file}")

# -----------------------------------------------------------------------------
# Reload and Summaries
# -----------------------------------------------------------------------------
# If you want to confirm the saved file loads properly:
# Highlight these lines in VS Code to run them
test_df = pd.read_csv(output_file, parse_dates=["date"])
print("Reloaded dataset shape:", test_df.shape)
print(test_df.head(3))

# -----------------------------------------------------------------------------
# Geographic Check Using GeoPandas (Example)
# -----------------------------------------------------------------------------
# If you have a shapefile of CA ZIP codes, you might do:
# shape_file = os.path.join(config.RAW_CWS_DIR, "ca_zcta10.shp")  # Example name
# zip_shapes = gpd.read_file(shape_file)
# print("Shapefile loaded with", len(zip_shapes), "rows.")

# # Plot a quick map
# zip_shapes.plot()
# plt.title("California Zip Codes from Shapefile")
# plt.show()

# # Compare zip codes:
# all_ca_zips = zip_shapes["ZCTA5CE10"].astype(str).unique()
# zillow_zips = test_df["zip_code"].astype(str).unique()
# missing_zips = set(all_ca_zips) - set(zillow_zips)
# print("\nZip codes in shapefile but missing in Zillow data:")
# print(missing_zips)

print("\nScript finished.")
