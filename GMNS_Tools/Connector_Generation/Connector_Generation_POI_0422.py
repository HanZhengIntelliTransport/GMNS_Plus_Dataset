# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 00:36:27 2025

@author: hnzhu
"""
import os
import time
import pandas as pd
import numpy as np
from shapely import wkt
from geopy.distance import geodesic
from shapely.geometry import Point
from shapely.errors import WKTReadingError

# Get current script path
current_path = os.path.dirname(os.path.abspath(__file__))

# File paths
link_file = os.path.join(current_path, "link.csv")
node_file = os.path.join(current_path, "node.csv")
node_poi_file = os.path.join(current_path, "poi_aggregated.csv")

# Load CSVs
link_df = pd.read_csv(link_file)
node_df = pd.read_csv(node_file)
node_poi_df = pd.read_csv(node_poi_file)

# poid_id start index:
node_poi_df_start = 1  # this is the designed start index
min_node_id_poi = node_poi_df['poi_id'].min()
node_poi_df['poi_id'] = node_poi_df['poi_id'] - min_node_id_poi + node_poi_df_start

# if poi information doesn't include x_coord and y_coord, we need to extract them from geometry
#####
# # Step 1: Convert WKT strings to Shapely geometry
node_poi_df['centroid'] = node_poi_df['centroid'].apply(wkt.loads)

# Extract x (longitude) and y (latitude) from the Point
node_poi_df['x_coord'] = node_poi_df['centroid'].apply(lambda p: p.x)
node_poi_df['y_coord'] = node_poi_df['centroid'].apply(lambda p: p.y)
# Step 3: Convert Shapely geometries back to WKT strings
#node_poi_df['centroid'] = node_poi_df['centroid'].apply(wkt.loads)
node_poi_df['centroid'] = node_poi_df['centroid'].apply(
    lambda g: wkt.loads(g) if isinstance(g, str) else g)
node_poi_df = node_poi_df.drop(columns='geometry').rename(columns={'centroid': 'geometry'})
node_poi_df['geometry'] = node_poi_df['geometry'].apply(lambda g: g.wkt)


# Start timing
start_time = time.time()


# %%
def process_node_data(node_df, node_poi_df, output_path=None):
    try:
        print("Starting to process node data...")

        # Step 1: Find the maximum node_id in node_poi_df
        print("Finding the maximum node_id in node_poi_df...")
        max_node_id_poi = node_poi_df['poi_id'].max()
        min_node_id = node_df['node_id'].min()
        print(f"Maximum node_id in node_poi_df: {max_node_id_poi}")

        # Step 2: Add (max_node_id_poi + 1) to all node_ids in node_df
        print("Adding new_node_id to node_df...")
        node_df['new_node_id'] = node_df['node_id'] + max_node_id_poi - min_node_id + 1
        print("New node_id generation completed.")
        return node_df

    except Exception as e:
        print(f"An error occurred while processing node data: {e}")


# Example usage
output_path = current_path
updated_node_df = process_node_data(node_df, node_poi_df, output_path)


# %%
def generate_connector_links(updated_node_df, node_poi_df, output_path=None):
    try:
        print("Starting to generate connector links...")
        # Force x/y coordinate columns to be float
        updated_node_df[['x_coord', 'y_coord']] = updated_node_df[['x_coord', 'y_coord']].astype(float)
        node_poi_df[['x_coord', 'y_coord']] = node_poi_df[['x_coord', 'y_coord']].astype(float)
        
        connector_links = []
        total_length = 0
        pair_number = 0

        for idx, poi_node in node_poi_df.iterrows():
            poi_node_id = poi_node['poi_id']
            poi_node_x = poi_node['x_coord']
            poi_node_y = poi_node['y_coord']

            updated_node_df['distance'] = np.sqrt(
                (updated_node_df['x_coord'] - poi_node_x) ** 2 +
                (updated_node_df['y_coord'] - poi_node_y) ** 2
            )

            nearest_node = nearest_node = updated_node_df.loc[updated_node_df['distance'].idxmin()]
            nearest_node_id = nearest_node['new_node_id']
            nearest_node_x = nearest_node['x_coord']
            nearest_node_y = nearest_node['y_coord']

            for from_id, to_id, from_x, from_y, to_x, to_y in [
                (nearest_node_id, poi_node_id, nearest_node_x, nearest_node_y, poi_node_x, poi_node_y),
                (poi_node_id, nearest_node_id, poi_node_x, poi_node_y, nearest_node_x, nearest_node_y)
            ]:
                geometry = f"LINESTRING ({from_x} {from_y}, {to_x} {to_y})"
                total_length += geodesic((from_y, from_x), (to_y, to_x)).meters
                pair_number += 1
                #length = 0
                length = geodesic((from_y, from_x), (to_y, to_x)).meters

                connector_links.append({
                    "link_id": len(connector_links) + 1,
                    "from_node_id": from_id,
                    "to_node_id": to_id,
                    "dir_flag": 1,
                    "length": length,
                    "lanes": 1,
                    "free_speed": 5, #for walk network
                    "capacity": 3600, # for walk network
                    "link_type_name": "connector",
                    "link_type": 0,
                    "geometry": geometry,
                    "allowed_uses": "auto",
                    "from_biway": 1,
                    "is_link": 0
                })

        connector_links_df = pd.DataFrame(connector_links)
        print(f"Generated {len(connector_links_df)} connector links.")

        connector_links_df["vdf_toll"] = 0
        connector_links_df["allowed_uses"] = None
        connector_links_df["vdf_alpha"] = 0.15
        connector_links_df["vdf_beta"] = 4
        connector_links_df["vdf_plf"] = 1
        connector_links_df["vdf_length_mi"] = connector_links_df["length"] / 1609
        connector_links_df["vdf_free_speed_in_mph"] = connector_links_df["free_speed"] / 1.60934
        connector_links_df["free_speed_in_mph_raw"] = round(connector_links_df["vdf_free_speed_in_mph"] / 5) * 5
        connector_links_df["vdf_fftt"] = (connector_links_df["length"] / connector_links_df["free_speed"]) * 0.06

        other_columns = ['ref_volume', 'base_volume', 'base_vol_auto', 'restricted_turn_nodes']
        for other_column in other_columns:
            connector_links_df[other_column] = None

        file_name = "connector_links.csv"
        output_file = os.path.join(output_path, file_name)
        if output_file:
            connector_links_df.to_csv(output_file, index=False)
            print(f"The connector links have been successfully saved to '{output_file}'.")
        else:
            print("Output file not provided. Skipping file saving.")

        return connector_links_df

    except Exception as e:
        print(f"An error occurred while generating connector links: {e}")


# Example usage
connector_links_df = generate_connector_links(updated_node_df, node_poi_df, output_path)


# %%
def update_and_merge_links(link_df, updated_node_df, connector_links_df, output_path):
    """
    Updates link_df with new_node_id, merges it with connector_links_df, and saves the updated file.

    Args:
        link_df (pd.DataFrame): DataFrame containing the original link data.
        node_df (pd.DataFrame): DataFrame containing node_id and new_node_id mapping.
        connector_links_df (pd.DataFrame): DataFrame containing the connector links.
        output_file (str): Path to save the updated Link_Updated.csv file.
    """
    try:
        # Step 1: Create a mapping of node_id to new_node_id
        node_id_map = dict(zip(updated_node_df['node_id'], updated_node_df['new_node_id']))

        # Step 2: Update from_node_id and to_node_id in link_df
        link_df['from_node_id'] = link_df['from_node_id'].map(node_id_map)
        link_df['to_node_id'] = link_df['to_node_id'].map(node_id_map)

        # Step 3: Validate if there are any unmatched IDs
        if link_df['from_node_id'].isnull().any() or link_df['to_node_id'].isnull().any():
            print("Warning: Some from_node_id or to_node_id in link_df could not be mapped to new_node_id.")

        # Step 3.5: Add new column to link_df
        # Step3.5 Add new columns
        link_df["vdf_toll"] = 0
        link_df["allowed_uses"] = None
        link_df["vdf_alpha"] = 0.15
        link_df["vdf_beta"] = 4
        link_df["vdf_plf"] = 1
        link_df["vdf_length_mi"] = link_df["length"] / 1609
        link_df["vdf_free_speed_mph"] = link_df["free_speed"] / 1.60934
        link_df["free_speed_in_mph_raw"] = round(link_df["vdf_free_speed_mph"] / 5) * 5
        link_df["vdf_fftt"] = (link_df["length"] / link_df["free_speed"]) * 0.06

        other_columns = ['ref_volume', 'base_volume', 'base_vol_auto', 'restricted_turn_nodes']
        for other_column in other_columns:
            link_df[other_column] = None

        # Step 4: Align columns between link_df and connector_links_df
        all_columns = set(link_df.columns).union(connector_links_df.columns)

        # Add missing columns with None
        for col in all_columns:
            if col not in link_df.columns:
                link_df[col] = None
            if col not in connector_links_df.columns:
                connector_links_df[col] = None

        # Ensure connector_links_df has the same column order as link_df
        connector_links_df = connector_links_df[link_df.columns]
        # breakpoint()

        # Step 5: Combine link_df and connector_links_df
        combined_links_df = pd.concat([link_df, connector_links_df], ignore_index=True)

        # Step 6: Sort and assign new link_id
        combined_links_df = combined_links_df.sort_values(by=['from_node_id', 'to_node_id']).reset_index(drop=True)
        combined_links_df['link_id'] = range(1, len(combined_links_df) + 1)

        # Step 7: Save the updated DataFrame to the output file
        file_name = "link_updated.csv"
        output_file = os.path.join(output_path, file_name)
        combined_links_df.to_csv(output_file, index=False)
        print(f"Updated and merged data has been saved to {output_file}.")

    except Exception as e:
        print(f"An error occurred: {e}")


# Example usage
update_and_merge_links(link_df, updated_node_df, connector_links_df, output_path)


# %%
def create_updated_node_df(updated_node_df, node_poi_df, output_path):
    try:
        updated_node_df = updated_node_df.rename(columns={'node_id': 'old_node_id'})
        updated_node_df = updated_node_df.rename(columns={'new_node_id': 'node_id'})

        updated_node_df['zone_id'] = None
        node_poi_df['node_id'] = node_poi_df['poi_id']

        Node_Updated_df = pd.concat([node_poi_df, updated_node_df], ignore_index=True)
        Node_Updated_df = Node_Updated_df.sort_values(by=['node_id']).reset_index(drop=True)
        Node_Updated_df = Node_Updated_df.drop(columns=['ctrl_type', 'distance'])

        for i in range(len(Node_Updated_df)):
            if pd.isna(Node_Updated_df.loc[i, 'geometry']) or Node_Updated_df.loc[i, 'geometry'].strip() == '':
                x_coord = Node_Updated_df.loc[i, 'x_coord']
                y_coord = Node_Updated_df.loc[i, 'y_coord']
                Node_Updated_df.loc[i, 'geometry'] = f"POINT ({x_coord} {y_coord})"

        file_name = "node_updated.csv"
        output_file = os.path.join(output_path, file_name)
        Node_Updated_df = Node_Updated_df.drop(columns='zone_id', errors='ignore').rename(columns={'poi_id': 'zone_id'})
        
        #Important!! MOVE node_id to the 1st column
        Node_Updated_df = Node_Updated_df[['node_id'] + [c for c in Node_Updated_df.columns if c != 'node_id']]
        Node_Updated_df.to_csv(output_file, index=False)       
        print(f"The updated node data has been successfully saved to '{output_file}'.")
        return Node_Updated_df

    except Exception as e:
        print(f"An error occurred: {e}")


# Example usage
Node_Updated_df = create_updated_node_df(updated_node_df, node_poi_df, output_path)

# End timing
end_time = time.time()
print(f"Computational time: {end_time - start_time:.2f} seconds")


