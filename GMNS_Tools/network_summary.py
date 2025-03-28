import os
import pandas as pd

# Define the directory containing city folders
base_dir = os.getcwd()

# List all directories (city folders)
city_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

# Define output file
output_file = "city_summary.csv"

# Initialize a list to store summary results
summary_data = []

# Process each city folder
for city in city_folders:
    city_path = os.path.join(base_dir, city)
    node_file = os.path.join(city_path, "node.csv")
    link_file = os.path.join(city_path, "link.csv")

    # Check if node file exists and read
    num_nodes = None
    if os.path.exists(node_file):
        try:
            node_df = pd.read_csv(node_file, encoding="utf-8")
            num_nodes = node_df.shape[0]
        except Exception as e:
            print(f"Error reading node.csv in {city}: {e}")

    # Check if link file exists
    if not os.path.exists(link_file):
        print(f"{city}: Missing link.csv, skipping link stats")
        summary_data.append([city, num_nodes, "no_links"] + [None] * 13)
        continue

    try:
        link_df = pd.read_csv(link_file, encoding="utf-8")
        link_df.columns = link_df.columns.str.strip().str.lower()
    except Exception as e:
        print(f"Error reading link.csv in {city}: {e}")
        summary_data.append([city, num_nodes, "read_error"] + [None] * 13)
        continue

    required_columns = {"link_id", "length", "free_speed", "capacity", "vdf_fftt"}
    missing_columns = required_columns - set(link_df.columns)

    if missing_columns:
        print(f"{city}: Missing required columns in link.csv -> {missing_columns}")
        summary_data.append([city, num_nodes, "incomplete_columns"] + [None] * 13)
        continue

    def compute_stats(df):
        return [
            df.shape[0],
            df["length"].min(), df["length"].max(), df["length"].mean(),
            df["free_speed"].min(), df["free_speed"].max(), df["free_speed"].mean(),
            df["capacity"].min(), df["capacity"].max(), df["capacity"].mean(),
            df["vdf_fftt"].min(), df["vdf_fftt"].max(), df["vdf_fftt"].mean(),
        ]

    if (link_df["length"] == 0).any():
        connectors = link_df[link_df["length"] == 0]
        physical_links = link_df[link_df["length"] > 0]

        connector_stats = compute_stats(connectors)
        physical_stats = compute_stats(physical_links)

        summary_data.append([city, num_nodes, "connectors"] + connector_stats)
        summary_data.append([city, num_nodes, "physical_links"] + physical_stats)
    else:
        all_stats = compute_stats(link_df)
        summary_data.append([city, num_nodes, "all_links"] + all_stats)

# Define column names
columns = [
    "city", "num_nodes", "link_type",
    "num_links", "min_length", "max_length", "avg_length",
    "min_free_speed", "max_free_speed", "avg_free_speed",
    "min_capacity", "max_capacity", "avg_capacity",
    "min_vdf_fftt", "max_vdf_fftt", "avg_vdf_fftt"
]

# Create DataFrame and save
summary_df = pd.DataFrame(summary_data, columns=columns)
summary_df.to_csv(output_file, index=False, encoding="utf-8")

print(f"Summary saved to {output_file}")
