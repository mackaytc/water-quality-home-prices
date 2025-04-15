"""
===============================================================================
 Title: config.py
 Description: Central configuration file with references to code/output folder 
              and data folder for water-quality-home-prices project.
 Created On: April 11, 2025
===============================================================================
"""

import os

# Absolute path to your GitHub repo (code + output)
PROJECT_DIR = r"C:\Users\macka\github-repos\water-quality-home-prices"

# Absolute path to your Google Drive data folder
DATA_DIR = r"G:\My Drive\research\water-stuff\python-data-files"

# Relative subdirectories for code & output 

CODE_DIR = os.path.join(PROJECT_DIR, "code")
NOTEBOOK_DIR = os.path.join(PROJECT_DIR, "output")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
OUTPUT_TBL_DIR = os.path.join(OUTPUT_DIR, "tables")
OUTPUT_FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
OUTPUT_OTHR_DIR = os.path.join(OUTPUT_DIR, "other-output")

# Relative subdirectories for data

RAW_DATA_DIR = os.path.join(DATA_DIR, "raw-data")

RAW_HOME_PRICE_DIR = os.path.join(RAW_DATA_DIR, "home-price-data")
RAW_CWS_DIR = os.path.join(RAW_DATA_DIR, "CWS-service-boundaries")
RAW_EPA_DIR = os.path.join(RAW_DATA_DIR, "EPA-SDWIS-downloads")
RAW_ZCTA_DIR = os.path.join(RAW_DATA_DIR, "ZCTA-census-boundaries")

PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed-data")
