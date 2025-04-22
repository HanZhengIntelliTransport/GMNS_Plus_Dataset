# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 00:36:27 2025

@author: hnzhu
"""

import pandas as pd
import numpy as np
from geopy.distance import geodesic
import time
import os




current_path = os.path.dirname(os.path.abspath(__file__))
#current_path = r"C:\Users\hnzhu\ASU Dropbox\Henan Zhu\TAPLite Project\0321_Network_POI" # Update this path to match your folder directory

link_file = os.path.join(current_path, "link.csv")
node_file = os.path.join(current_path, "node.csv")
node_taz_file = os.path.join(current_path, "TAZ_centroid.csv")

# Import CSV files as DataFrames
link_df = pd.read_csv(link_file)
#node_df = pd.read_csv(node_file, dtype={'osm_node_id': str})
node_df = pd.read_csv(node_file)
node_taz_df = pd.read_csv(node_taz_file)


# Start timing
start_time = time.time()


# %%
def process_and_save_activity_node_data(node_df, node_taz_df, output_path=None):
    """
    Processes node_df by adding new_node_id and filtering rows with non-null zone_id, 
    then saves the filtered DataFrame (activity_node_df) to a CSV file.

    Args:
        node_df (pd.DataFrame): DataFrame containing original node data.
        node_taz_df (pd.DataFrame): DataFrame containing TAZ node data.
        output_file (str): Path to save the activity_node_df as a CSV file. Default is "activity_node.csv".

    Returns:
        tuple: Updated node_df with new_node_id and activity_node_df.
    """
    try:
        print("Starting to process node data...")

        # Step 1: Find the maximum node_id in node_taz_df
        print("Finding the maximum node_id in node_taz_df...")
        max_node_id_taz = node_taz_df['poi_id'].max()
        min_node_id = node_df['node_id'].min()
        print(f"Maximum node_id in node_taz_df: {max_node_id_taz}")

        # Step 2: Add (max_node_id_taz + 1) to all node_ids in node_df
        print("Adding new_node_id to node_df...")        
        node_df['new_node_id'] = node_df['node_id'] + max_node_id_taz - min_node_id + 1
        print("New node_id generation completed.")
        

        # Step 3: Filter rows where 'zone_id' is not null to create activity_node_df
        print("Filtering rows in node_df where 'zone_id' is not null...")
        activity_node_df = node_df[node_df['zone_id'].notnull()]
        print(f"Filtered {len(activity_node_df)} rows with non-null zone_id.")
        # DataFrame with null zone_id (common nodes)
        common_node_df = node_df[node_df['zone_id'].isnull()]
        print(f"Filtered {len(common_node_df)} rows with null zone_id.")

        # Step 4: Save the activity_node_df to a CSV file
        file_name = "activity_node.csv"
        output_file = os.path.join(output_path, file_name)
        print(f"Saving activity_node_df to '{output_file}'...")
        activity_node_df.to_csv(output_file, index=False)
        print(f"File saved successfully to '{output_file}'.")
        
        # Step 5: Save the common_node_df to a CSV file
        file_name1 = "common_node.csv"
        output_file1 = os.path.join(output_path, file_name1)
        print(f"Saving common_node_df to '{output_file1}'...")
        common_node_df.to_csv(output_file1, index=False)
        print(f"File saved successfully to '{output_file1}'.")
        
        
        # Return the updated DataFrames
        return node_df, activity_node_df, common_node_df

    except Exception as e:
        print(f"An error occurred while processing node data: {e}")

# Example usage
output_path = current_path
updated_node_df, activity_node_df, common_node_df = process_and_save_activity_node_data(node_df, node_taz_df, output_path)


# %%
def generate_connector_links(node_df, node_taz_df, output_path=None):
    """
    Generates bi-directional connector links between activity nodes and their nearest TAZ nodes,
    adding geometry and length columns.

    Args:
        activity_node_df (pd.DataFrame): DataFrame containing activity nodes with 'new_node_id', 'x_coord', and 'y_coord'.
        node_taz_df (pd.DataFrame): DataFrame containing TAZ nodes with 'node_id', 'x_coord', and 'y_coord'.
        output_file (str, optional): Path to save the connector_links_df as a CSV file. Default is None.

    Returns:
        pd.DataFrame: A DataFrame containing bi-directional connector links with columns:
                      'link_id', 'from_node_id', 'to_node_id', 'geometry', 'length'.
    """
    try:
        print("Starting to generate connector links...")

        # Create an empty list to store the connector links
        connector_links = []

        # Step 1: Calculate the nearest TAZ node for each activity node
        print("Calculating nearest TAZ nodes for activity nodes...")
        total_length = 0
        pair_number = 0
        for idx, taz_node in node_taz_df.iterrows():
            # Extract activity node details
            taz_node_id = taz_node['poi_id']
            taz_node_x = taz_node['x_coord']
            taz_node_y = taz_node['y_coord']

            # Calculate the Euclidean distance to all TAZ nodes
            node_df['distance'] = np.sqrt(
                (node_df['x_coord'] - taz_node_x) ** 2 + 
                (node_df['y_coord'] - taz_node_y) ** 2
            )

            # Find the nearest TAZ node
            nearest_node = node_df.loc[node_df['distance'].idxmin()]
            nearest_node_id = nearest_node['node_id']
            nearest_node_x = nearest_node['x_coord']
            nearest_node_y = nearest_node['y_coord']
            # Step 2: Create bi-directional connector links with geometry and length
            for from_id, to_id, from_x, from_y, to_x, to_y in [
                (nearest_node_id, taz_node_id, nearest_node_x, nearest_node_y, taz_node_x, taz_node_y),
                (taz_node_id, nearest_node_id, taz_node_x, taz_node_y, nearest_node_x, nearest_node_y)
            ]:
                # Calculate geometry as a LINESTRING
                geometry = f"LINESTRING ({from_x} {from_y}, {to_x} {to_y})"

                # Calculate length in meters using geopy, if you wanna use actual distance, pls uncomment the following command
                #length = geodesic((from_y, from_x), (to_y, to_x)).meters
                total_length = total_length+geodesic((from_y, from_x), (to_y, to_x)).meters
                pair_number = pair_number+1
                length=100
                
                # Append link information to the list
                connector_links.append({
                    "link_id": len(connector_links) + 1,
                    "from_node_id": from_id,
                    "to_node_id": to_id,
                    "dir_flag": 1,
                    "length": length,
                    "lanes": 1,
                    "free_speed": 120,
                    "capacity": 100000,
                    "link_type_name": "connector",
                    "link_type": 0,
                    "geometry": geometry,
                    "allowed_uses": "auto",
                    "from_biway": 1,
                    "is_link": 0                    
                })
            
        # print("Calculating nearest activity nodes for taz nodes...")       
        # ave_pair_length = total_length/pair_number
        # print(f"ave pair length: '{ave_pair_length}' meters.")
        # for idx, taz_node in node_taz_df.iterrows():
        #     # Extract taz node details
        #     taz_node_id = taz_node['node_id']
        #     taz_node_x = taz_node['x_coord']
        #     taz_node_y = taz_node['y_coord']
        #     if any(taz_node['node_id'] == l['from_node_id'] for l in connector_links):
        #         continue
                    

        #     # Calculate the Euclidean distance to all taz nodes
        #     common_node_df['distance'] = np.sqrt(
        #         (common_node_df['x_coord'] - taz_node_x) ** 2 + 
        #         (common_node_df['y_coord'] - taz_node_y) ** 2
        #     )

        #     # Find the nearest ACT node
        #     nearest_common_node = common_node_df.loc[common_node_df['distance'].idxmin()]
        #     nearest_common_node_id = nearest_common_node['new_node_id']
        #     nearest_common_node_x = nearest_common_node['x_coord']
        #     nearest_common_node_y = nearest_common_node['y_coord']

        #     # Step 2: Create bi-directional connector links with geometry and length
        #     for from_id, to_id, from_x, from_y, to_x, to_y in [
        #         (nearest_common_node_id, taz_node_id, nearest_common_node_x, nearest_common_node_y, taz_node_x, taz_node_y),
        #         (taz_node_id, nearest_common_node_id, taz_node_x, taz_node_y, nearest_common_node_x, nearest_common_node_y)
        #     ]:
        #         # Calculate geometry as a LINESTRING
        #         geometry = f"LINESTRING ({from_x} {from_y}, {to_x} {to_y})"

        #         # Calculate length in meters using geopy, if you wanna use actual distance, pls uncomment the following command
        #         length = 100
                
                
        #         #To connect all mismatched TAZ
        #         #if geodesic((from_y, from_x), (to_y, to_x)).meters < 10*ave_pair_length:
        #         #if geodesic((from_y, from_x), (to_y, to_x)).meters < 88514:  # max length: 55miles # avg distance: 700 m
        #         # Append link information to the list
        #         connector_links.append({
        #             "link_id": len(connector_links) + 1,
        #             "from_node_id": from_id,
        #             "to_node_id": to_id,
        #             "dir_flag": 1,
        #             "length": length,
        #             "lanes": 1,
        #             "free_speed": 120,
        #             "capacity": 100000,
        #             "link_type_name": "connector",
        #             "link_type": 0,
        #             "geometry": geometry,
        #             "allowed_uses": "auto",
        #             "from_biway": 1,
        #             "is_link": 0                    
        #         })
     
        # Step 3: Convert the list of links to a DataFrame
        connector_links_df = pd.DataFrame(connector_links)
        print(f"Generated {len(connector_links_df)} connector links.")
        
        # Step3.5 Add new columns
        connector_links_df["toll_auto"] = 0
        connector_links_df["allowed_uses"] = None
        connector_links_df["VDF_alpha"] = 0.15
        connector_links_df["VDF_beta"] = 4
        connector_links_df["length_in_mile"] = connector_links_df["length"] / 1609
        connector_links_df["free_speed_in_mph"] = connector_links_df["free_speed"] / 1.60934
        connector_links_df["free_speed_in_mph_raw"] = round(connector_links_df["free_speed_in_mph"] / 5) * 5


        other_columns = ['ref_volume',	'base_volume',	'base_vol_auto',	'restricted_turn_nodes',	'VDF_fftt',	'VDF_toll_auto']
        for other_column in other_columns:
            connector_links_df[other_column] = None

        # Step 4: Save to a CSV file if an output file is provided
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
connector_links_df = generate_connector_links(node_df, node_taz_df, output_path)


# Display the connector links DataFrame
#print("Connector Links DataFrame:")
#print(connector_links_df.head())

#%%
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
        link_df["toll_auto"] = 0
        link_df["allowed_uses"] = None
        link_df["VDF_alpha"] = 0.15
        link_df["VDF_beta"] = 4
        link_df["length_in_mile"] = link_df["length"] / 1609
        link_df["free_speed_in_mph"] = link_df["free_speed"] / 1.60934
        link_df["free_speed_in_mph_raw"] = round(link_df["free_speed_in_mph"] / 5) * 5

        other_columns = ['ref_volume',	'base_volume',	'base_vol_auto',	'restricted_turn_nodes',	'VDF_fftt',	'VDF_toll_auto']
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
        #breakpoint()

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
def create_updated_node_df(updated_node_df, node_taz_df, output_path):
    """
    Creates a new Node_Updated_df by combining node_taz_df and node_df with updates.

    Args:
        node_df (pd.DataFrame): DataFrame containing the original node data with new_node_id.
        node_taz_df (pd.DataFrame): DataFrame containing TAZ nodes.
        output_file (str): Path to save the Node_Updated.csv file.
    """
    try:
        # Step 1: Rename 'node_id' in updated_node_df to 'old_node_id' and use 'new_node_id' as the current ID
        updated_node_df = updated_node_df.rename(columns={'node_id': 'old_node_id'})
        updated_node_df = updated_node_df.rename(columns={'new_node_id': 'node_id'})
        
        # Step 2: update zone_id
        #node_taz_df['zone_id'] = node_taz_df.apply(lambda row: int(row['node_id']) if row['zone_id'] is None else None, axis=1)
        updated_node_df['zone_id'] = None
        node_taz_df['node_id'] = node_taz_df['poi_id']
        
        # Step 3: Combine node_taz_df and updated updated_node_df
        Node_Updated_df = pd.concat([node_taz_df, updated_node_df], ignore_index=True)

        # Step 4: Sort Node_Updated_df by 'node_id'
        Node_Updated_df = Node_Updated_df.sort_values(by=['node_id']).reset_index(drop=True)
        
        # Step 5: Remove the 'ctrl_type' and 'distance' columns
        Node_Updated_df = Node_Updated_df.drop(columns=['ctrl_type', 'distance'])
        
        # Step 5.5: Check the geometry element and fill it if it is empty
        # Replace empty or NaN values in the 'geometry' column with POINT(x_coord y_coord)
        for i in range(len(Node_Updated_df)):            
            if pd.isna(Node_Updated_df.loc[i, 'geometry']) or Node_Updated_df.loc[i, 'geometry'].strip() == '':  # Check for empty or NaN-like values
                x_coord = Node_Updated_df.loc[i, 'x_coord']
                y_coord = Node_Updated_df.loc[i, 'y_coord']
                Node_Updated_df.loc[i, 'geometry'] = f"POINT ({x_coord} {y_coord})"

        # Step 6: Save node_updated_df to a CSV file
        file_name = "node_updated.csv"
        output_file = os.path.join(output_path, file_name)
        Node_Updated_df.to_csv(output_file, index=False)
        print(f"The updated node data has been successfully saved to '{output_file}'.")
        return Node_Updated_df

    except Exception as e:
        print(f"An error occurred: {e}")
        
# Example usage
Node_Updated_df = create_updated_node_df(updated_node_df, node_taz_df, output_path)

# End timing
end_time = time.time()

# Print the computational time
print(f"Computational time: {end_time - start_time:.2f} seconds")

