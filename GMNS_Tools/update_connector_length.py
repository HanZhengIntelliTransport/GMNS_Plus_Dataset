# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 21:02:01 2025

@author: hnzhu
"""
import os
import pandas as pd
import shapely.wkt
from geopy.distance import great_circle

# Constants
METER_TO_MILE = 1 / 1609.34
KMH_TO_M_PER_MIN = 1000 / 60

# Get list of all subfolders in current directory
base_dir = os.getcwd()
folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

# Function to calculate length from geometry (great circle)
def calculate_length_from_geometry(geometry_wkt):
    try:
        line = shapely.wkt.loads(geometry_wkt)
        coords = list(line.coords)
        total_length = sum(
            great_circle((coords[i][1], coords[i][0]), (coords[i+1][1], coords[i+1][0])).meters
            for i in range(len(coords) - 1)
        )
        return total_length
    except Exception as e:
        print(f"⚠️ Geometry error: {e}")
        return 0

# Process each folder
for folder in folders:
    file_path = os.path.join(base_dir, folder, "link.csv")
    if not os.path.exists(file_path):
        print(f"❌ link.csv not found in {folder}")
        continue

    print(f"\n🔄 Processing: {file_path}")
    try:
        df = pd.read_csv(file_path)

        if not {'length', 'geometry', 'free_speed', 'vdf_length_mi', 'vdf_fftt'}.issubset(df.columns):
            print("⚠️ Missing required columns.")
            continue

        # Identify connector links (length == 0)
        connector_mask = df['length'] == 0

        if connector_mask.sum() == 0:
            print("✅ No connector links (length = 0) found. Skipping.")
            continue

        # Process only connector links
        df.loc[connector_mask, 'length'] = df.loc[connector_mask, 'geometry'].apply(calculate_length_from_geometry)
        df.loc[connector_mask, 'vdf_length_mi'] = df.loc[connector_mask, 'length'] * METER_TO_MILE

        # Recalculate vdf_fftt: time (min) = distance (m) / speed (km/h) * (60 / 1000)
        df.loc[connector_mask, 'vdf_fftt'] = df.loc[connector_mask].apply(
            lambda row: (row['length'] / (row['free_speed'] * KMH_TO_M_PER_MIN)) if row['free_speed'] > 0 else None,
            axis=1
        )

        # Save the updated file back
        df.to_csv(file_path, index=False)
        print(f"✅ Updated connector links in: {file_path}")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
