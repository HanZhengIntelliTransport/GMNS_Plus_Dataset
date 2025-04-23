# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 20:40:13 2025

@author: hnzhu
"""
import os
import pandas as pd
import shapely.wkt
from geopy.distance import great_circle

# Constants
METER_TO_MILE = 1 / 1609.34
KMH_TO_MPH = 0.621371

# Get list of all subfolders
base_dir = os.getcwd()  # Make sure this is run in the folder where those city folders are
folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

# Function to calculate great-circle distance for each link
def calculate_length_from_geometry(geometry_wkt):
    try:
        line = shapely.wkt.loads(geometry_wkt)
        coords = list(line.coords)
        length_m = sum(
            great_circle((coords[i][1], coords[i][0]), (coords[i+1][1], coords[i+1][0])).meters
            for i in range(len(coords) - 1)
        )
        return length_m
    except Exception as e:
        print(f"Geometry parse error: {e}")
        return None

# Process each folder
for folder in folders:
    file_path = os.path.join(base_dir, folder, "link.csv")
    if os.path.exists(file_path):
        print(f"🔄 Processing: {file_path}")
        try:
            df = pd.read_csv(file_path)

            # Calculate new length using geometry
            df['length'] = df['geometry'].apply(calculate_length_from_geometry)

            # Update vdf_length_mi
            df['vdf_length_mi'] = df['length'] * METER_TO_MILE

            # Compute free_speed in km/h
            df['free_speed'] = df.apply(
                lambda row: (row['length'] / row['vdf_fftt']) * (60 / 1000) if row['vdf_fftt'] > 0 else None,
                axis=1
            )

            # Compute vdf_free_speed_mph
            df['vdf_free_speed_mph'] = df['free_speed'] * KMH_TO_MPH

            # Save updated CSV (overwrite)
            df.to_csv(file_path, index=False)
            print(f"✅ Updated: {file_path}")
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    else:
        print(f"⚠️ link.csv not found in {folder}")
