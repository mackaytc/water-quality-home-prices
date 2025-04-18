"""
===============================================================================
 Title: mapping_water_systems_to_ztcas.py
 Description:
     Cleans up the PWS service boundary data and creates crosswalks between 
     water system boundaries and Zip Code Tabulation Areas (ZTCAs) for both 
     2000 and 2010. Then merges this crosswalk with home price data.
===============================================================================
"""

# -----------------------------------------------------------------------------
# Import Libraries and Config
# -----------------------------------------------------------------------------
import os
import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Run central config file to reference project directories
# If running interactively, uncomment & set working directory to code directory
sys.path.append(r"C:\Users\macka\github-repos\water-quality-home-prices\code")

import config

# -----------------------------------------------------------------------------
# Loading PWS Boundary System Data
# -----------------------------------------------------------------------------
print("Loading PWS boundary data...")

# Load shapefile data
pws_sf = gpd.read_file(os.path.join(
    config.RAW_CWS_DIR,
    "California_Drinking_Water_System_Area_Boundaries.shp"
))

# Check for duplicated rows in the PWS data
duplicates = pws_sf.groupby("SABL_PWSID").size().reset_index(name='n')
duplicates = duplicates[duplicates['n'] > 1]
print(f"Found {len(duplicates)} PWS IDs with multiple polygons")

# -----------------------------------------------------------------------------
# Load Violations Panel to Identify Systems of Interest
# -----------------------------------------------------------------------------
print("Loading violations panel data...")

# Load violations panel data
panel_data = pd.read_csv(os.path.join(
    config.PROCESSED_DATA_DIR,
    "CA_monthly_violation_panel.csv"
))

# Identify systems with violations
PWS_with_violation_IDs = panel_data[
    (panel_data["tier1_all"] == 1) | 
    (panel_data["arsenic"] == 1) | 
    (panel_data["dbcp"] == 1)
]["PWS ID"].unique()

print(f"Found {len(PWS_with_violation_IDs)} water systems with violations")

# Create a subset of PWS data with only systems that have violations
pws_with_violations = pws_sf[pws_sf["SABL_PWSID"].isin(PWS_with_violation_IDs)].copy()

# Check for duplicate systems in the filtered data
pws_with_violations_multiples = pws_with_violations.groupby("SABL_PWSID").size().reset_index(name='n')
pws_with_violations_multiples = pws_with_violations_multiples[pws_with_violations_multiples['n'] > 1]
print(f"Systems with multiple polygons in filtered data: {len(pws_with_violations_multiples)}")

# -----------------------------------------------------------------------------
# Loading ZTCA Boundary Data
# -----------------------------------------------------------------------------
print("Loading ZTCA boundary data (2000 and 2010)...")

# Load the ZCTA shapefiles from your directory structure
# Using the exact paths from your screenshots
ztca_shapes_00 = gpd.read_file(os.path.join(
    config.RAW_DATA_DIR, 
    "ZCTA-census-boundaries",
    "ZCTA-2000",
    "tl_2010_06_zcta500.shp"
))

ztca_shapes_10 = gpd.read_file(os.path.join(
    config.RAW_DATA_DIR, 
    "ZCTA-census-boundaries",
    "ZCTA-2010",
    "tl_2010_06_zcta510.shp"
))

print(f"Loaded {len(ztca_shapes_00)} ZCTAs from 2000")
print(f"Loaded {len(ztca_shapes_10)} ZCTAs from 2010")

# Make sure CRS match for spatial operations
# Set CRS to equal-area projection for California using EPSG:3310
pws_with_violations = pws_with_violations.to_crs(epsg=3310)
ztca_equal_area = ztca_shapes_00.to_crs(epsg=3310)

# Calculate area of each ZTCA and store in square meters
ztca_equal_area["zcta_area_m2"] = ztca_equal_area.geometry.area

# Save a separate non-GeoDataFrame object list with each ZTCA + its area in meters
# Make sure to use the correct column name based on your shapefile
# For 2000 ZCTAs, the ZIP code column appears to be "ZCTA5CE00"
ztca_area = ztca_equal_area[["ZCTA5CE00", "zcta_area_m2"]].copy()
ztca_area = pd.DataFrame(ztca_area.drop(columns="geometry"))

# Now, deal with water systems where we had multiple rows in PWS data
# Group by PWS ID and use union to combine geometries
pws_with_violations = pws_with_violations.dissolve(by="SABL_PWSID", aggfunc="first").reset_index()

# Calculate area of each PWS in square meters
pws_with_violations["pws_area_m2"] = pws_with_violations.geometry.area

# -----------------------------------------------------------------------------
# Spatial Overlay of PWS and ZTCA Boundaries
# -----------------------------------------------------------------------------
print("Performing spatial overlay (this will take some time)...")

output = []
output_sf = []

for i, pws_index in enumerate(PWS_with_violation_IDs):
    print(f"Running Spatial Overlay for CWS {i+1} of {len(PWS_with_violation_IDs)}: {pws_index}")
    
    # Filter for current PWS
    pws_poly = pws_with_violations[pws_with_violations["SABL_PWSID"] == pws_index]
    
    if pws_poly.empty:
        print(f"No geometry found for PWS ID {pws_index}, skipping...")
        continue
    
    # Find ZTCAs that intersect with this PWS
    # This is more efficient than checking all ZTCAs
    spatial_index = ztca_equal_area.sindex
    possible_matches_index = list(spatial_index.intersection(pws_poly.iloc[0].geometry.bounds))
    possible_matches = ztca_equal_area.iloc[possible_matches_index]
    
    if len(possible_matches) == 0:
        # Handle case with no intersections
        output.append(pd.DataFrame({
            "SABL_PWSID": [pws_index],
            "intersect_area_m2": [0],
            "ZCTA5CE00": [None],
            "zcta_area_m2": [None],
            "coverage_frac_ztca": [0]
        }))
        print(f"No ZTCA intersections found for CWS {i+1} ({pws_index})")
        continue
    
    # Now, use intersection to measure spatial overlap
    actual_intersects = possible_matches[possible_matches.intersects(pws_poly.iloc[0].geometry)]
    
    if len(actual_intersects) == 0:
        # Double-check that there really are no intersections
        output.append(pd.DataFrame({
            "SABL_PWSID": [pws_index],
            "intersect_area_m2": [0],
            "ZCTA5CE00": [None],
            "zcta_area_m2": [None],
            "coverage_frac_ztca": [0]
        }))
        continue
    
    # Calculate intersection
    overlap = gpd.overlay(pws_poly, actual_intersects, how='intersection')
    
    # Export GeoDataFrame for plotting and visual checks
    output_sf.append(overlap[["SABL_PWSID", "ZCTA5CE00", "geometry"]])
    
    # Create area column for each overlap polygon
    overlap["intersect_area_m2"] = overlap.geometry.area
    
    # Convert to DataFrame and join with ZTCA area data
    overlap_df = overlap[["SABL_PWSID", "intersect_area_m2", "ZCTA5CE00"]].copy()
    overlap_df = pd.DataFrame(overlap_df.drop(columns="geometry"))
    
    # Join with ZTCA area information and calculate coverage fraction
    overlap_df = overlap_df.merge(ztca_area, on="ZCTA5CE00", how="left")
    overlap_df["coverage_frac_ztca"] = overlap_df["intersect_area_m2"] / overlap_df["zcta_area_m2"]
    
    output.append(overlap_df)

# Combine all results
if output:
    pws_zcta_overlay = pd.concat(output, ignore_index=True)
else:
    pws_zcta_overlay = pd.DataFrame(columns=["SABL_PWSID", "intersect_area_m2", "ZCTA5CE00", "zcta_area_m2", "coverage_frac_ztca"])

if output_sf:
    output_sf_combined = pd.concat(output_sf, ignore_index=True)
    output_sf_combined = gpd.GeoDataFrame(output_sf_combined, geometry="geometry")
else:
    output_sf_combined = gpd.GeoDataFrame(columns=["SABL_PWSID", "ZCTA5CE00", "geometry"], geometry="geometry")

# Save crosswalk file of PWS to ZTCA + GeoDataFrame version of spatial data
pws_zcta_overlay.to_csv(os.path.join(
    config.PROCESSED_DATA_DIR, 
    "CA-PWS-to-ZTCA-2000-crosswalk.csv"
), index=False)

output_sf_combined.to_file(os.path.join(
    config.PROCESSED_DATA_DIR,
    "CA-PWS-to-ZTCA-2000-crosswalk-SF.geojson"
), driver="GeoJSON")

print("Crosswalk files created and saved.")