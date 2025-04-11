"""
===============================================================================
 Title: 02-create-violations-panel.py
 Description:
     Creates violations panel using EPA SDWIS data. Takes violations-level 
     data downloaded from EPA's SDWIS portal and creates a panel of monthly-
     level observations for each CWS in California.

===============================================================================
"""

# -----------------------------------------------------------------------------
# Import Libraries and Config
# -----------------------------------------------------------------------------
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import re
from pathlib import Path

# If running interactively, uncomment & set working directory to code directory
sys.path.append(r"C:\Users\macka\github-repos\water-quality-home-prices\code")

import config

# -----------------------------------------------------------------------------
# Load and Subset Raw Violations Data
# -----------------------------------------------------------------------------
# Load raw data from EPA
violations_file = os.path.join(
    config.RAW_EPA_DIR,
    "Violation Report_20250308.xlsx"
)

# Skip the first 4 rows as they contain header information
violations_raw = pd.read_excel(violations_file, skiprows=4)

print(f"Total raw violations loaded: {len(violations_raw):,}")

# Initial filtering and cleaning
violations = violations_raw[
    (violations_raw["PWS Type Code"] == "CWS") & 
    (violations_raw["Public Notification Tier"].isin([1, 2])) &
    (violations_raw["Compliance Status"] != "Open")
].copy()

# Convert population served to numeric, removing commas
violations["population_served"] = violations["Population Served Count"].str.replace(",", "").astype(float)

# Convert date columns
violations["compliance_begin"] = pd.to_datetime(violations["Compliance Period Begin Date"])
violations["compliance_end"] = pd.to_datetime(violations["Compliance Period End Date"])
violations["rtc_end"] = pd.to_datetime(violations["RTC Date"])

# Use coalesce equivalent in pandas (first non-null value)
violations["end_date"] = violations["compliance_end"].fillna(violations["rtc_end"])

# Filter for CWS with population > 500
violations = violations[violations["population_served"] > 500].copy()

print(f"Filtered violations: {len(violations):,}")

# -----------------------------------------------------------------------------
# Create Monthly-Level Violations Measures
# -----------------------------------------------------------------------------
# Filter to ensure start date is before end date
violations = violations[violations["compliance_begin"] <= violations["end_date"]].copy()

# Function to expand a violation record to monthly observations
def expand_to_monthly(row):
    # Floor dates to the beginning of the month
    start_date = pd.Timestamp(row["compliance_begin"]).floor("M")
    end_date = pd.Timestamp(row["end_date"]).floor("M")
    
    # Generate sequence of months
    months = pd.date_range(start=start_date, end=end_date, freq="MS")
    
    # Create one row per month
    monthly_rows = []
    for month in months:
        monthly_row = row.copy()
        monthly_row["month"] = month
        monthly_rows.append(monthly_row)
    
    return pd.DataFrame(monthly_rows)

# Apply the function to each row and concatenate results
violations_list = []
for idx, row in violations.iterrows():
    monthly_rows = expand_to_monthly(row)
    violations_list.append(monthly_rows)

violations_monthly = pd.concat(violations_list, ignore_index=True)
print(f"Total monthly violation records: {len(violations_monthly):,}")

# Create violation indicators
violations_monthly["arsenic"] = (violations_monthly["Contaminant Name"] == "Arsenic").astype(int)
violations_monthly["dbcp"] = (violations_monthly["Contaminant Name"] == "1,2-DIBROMO-3-CHLOROPROPANE").astype(int)
violations_monthly["nitrate"] = violations_monthly["Contaminant Name"].isin(["Nitrate", "Nitrate-Nitrite"]).astype(int)
violations_monthly["tier1_all"] = (violations_monthly["Public Notification Tier"] == 1).astype(int)
violations_monthly["tier1_other"] = np.where(violations_monthly["nitrate"] == 1, 0, violations_monthly["tier1_all"])

# Aggregate to PWS ID and month level
violations_monthly_indicators = violations_monthly.groupby(["PWS ID", "month"]).agg({
    "arsenic": "max",
    "nitrate": "max",
    "dbcp": "max",
    "tier1_all": "max",
    "tier1_other": "max"
}).reset_index()

# Check resulting coding
print("\nViolations counts by type:")
for col in ["arsenic", "nitrate", "dbcp", "tier1_all", "tier1_other"]:
    count = violations_monthly_indicators[col].sum()
    print(f"{col}: {count:,}")

# -----------------------------------------------------------------------------
# Generate PWS Panel
# -----------------------------------------------------------------------------
# Get unique PWS IDs and date range
unique_pws_ids = violations["PWS ID"].unique()
min_date = violations_monthly_indicators["month"].min()
max_date = violations_monthly_indicators["month"].max()

# Create date range
date_range = pd.date_range(start=min_date, end=max_date, freq="MS")

# Create full panel with all combinations
pws_dates = [(pws_id, date) for pws_id in unique_pws_ids for date in date_range]
panel_data = pd.DataFrame(pws_dates, columns=["PWS ID", "month"])

# Merge with violations data
panel_data = panel_data.merge(
    violations_monthly_indicators,
    on=["PWS ID", "month"],
    how="left"
)

# Replace NAs with zeros
for col in ["arsenic", "dbcp", "nitrate", "tier1_all", "tier1_other"]:
    panel_data[col] = panel_data[col].fillna(0)

# Extract year and month
panel_data["year"] = panel_data["month"].dt.year
panel_data["month_num"] = panel_data["month"].dt.month

# Sort the data
panel_data = panel_data.sort_values(["PWS ID", "month"])

print(f"Panel data shape: {panel_data.shape}")

# -----------------------------------------------------------------------------
# Save Final Data
# -----------------------------------------------------------------------------
output_file = os.path.join(config.PROCESSED_DATA_DIR, "CA_monthly_violation_panel.csv")
panel_data.to_csv(output_file, index=False)
print(f"\nFinal panel dataset saved to:\n{output_file}")