import pandas as pd
from shapely.wkt import loads as load_wkt
from shapely.geometry import LineString, Point
import math
import uuid


# Function to generate unique IDs for nodes and links
def generate_id():
    return str(uuid.uuid4())


# Function to calculate the distance between two points
def calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)


# Function to find the longest pair of nodes in the polygon (long axis)
def find_longest_pair(polygon):
    longest_distance = 0
    long_axis_nodes = None
    coords = list(polygon.exterior.coords)
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            distance = calculate_distance(coords[i], coords[j])
            if distance > longest_distance:
                longest_distance = distance
                long_axis_nodes = (coords[i], coords[j])
    return long_axis_nodes


# Function to assign long_axis_in and long_axis_out based on proximity to gates
def assign_in_out_nodes(long_axis_nodes, gate_in_coords, gate_out_coords):
    in_node, out_node = long_axis_nodes

    # Find the closest node to gate in
    if gate_in_coords:
        closest_gate_in = min(gate_in_coords, key=lambda gate: calculate_distance(in_node, gate))
        dist_in_node = calculate_distance(in_node, closest_gate_in)
        dist_out_node = calculate_distance(out_node, closest_gate_in)

        if dist_out_node < dist_in_node:
            in_node, out_node = out_node, in_node  # Swap nodes

    # Ensure that the other node is closest to the gate out
    if gate_out_coords:
        closest_gate_out = min(gate_out_coords, key=lambda gate: calculate_distance(out_node, gate))
        dist_in_node = calculate_distance(in_node, closest_gate_out)
        dist_out_node = calculate_distance(out_node, closest_gate_out)

        if dist_in_node < dist_out_node:
            in_node, out_node = out_node, in_node  # Swap back if needed

    return in_node, out_node


# Function to convert meters to degrees (for offsetting siding tracks)
def meters_to_degrees(offset_meters, y_coord):
    lat_offset = offset_meters / 111320  # 1 degree latitude ≈ 111,320 meters
    lon_offset = offset_meters / (111320 * math.cos(math.radians(y_coord)))  # Adjust longitude based on latitude
    return lon_offset, lat_offset


# Read rail yard polygon and output gate CSV files
yards_df = pd.read_csv('rail_yards_polygons.csv')
gates_df = pd.read_csv('gate.csv')

# Initialize lists to store nodes and links
nodes_data = []
links_data = []

# Parameter to control the number of siding tracks on each side of the main track
num_siding_tracks_per_side = 2  # Number of tracks on each side
track_offset_meters = 150  # Distance between parallel siding tracks in meters
length_decrease_factor = 0.9  # Factor to decrease the length of each siding track

# A dictionary to map node IDs to their coordinates for constructing the LINESTRING geometry later
node_coordinates = {}

# Process each row in rail_yards_polygons.csv (each yard)
for index, row in yards_df.iterrows():
    yard_name = row['YardName']
    yard_id = row['ID']
    polygon_wkt = row['Polygon_WKT']

    # Load the polygon geometry from WKT
    polygon = load_wkt(polygon_wkt)

    # Find the longest pair of nodes (long axis)
    long_axis_nodes = find_longest_pair(polygon)
    main_track_length = calculate_distance(long_axis_nodes[0], long_axis_nodes[1])

    # Find gates in output_gate.csv for the current yard
    yard_gates = gates_df[gates_df['belong_yard'] == yard_id]
    gate_in_coords = [(row['x_coord'], row['y_coord']) for index, row in yard_gates[yard_gates['direction'] == 'in'].iterrows()]
    gate_out_coords = [(row['x_coord'], row['y_coord']) for index, row in yard_gates[yard_gates['direction'] == 'out'].iterrows()]

    # Assign long_axis_in_node and long_axis_out_node based on proximity to gates
    long_axis_in_node, long_axis_out_node = assign_in_out_nodes(long_axis_nodes, gate_in_coords, gate_out_coords)

    # Add the long_axis_in and long_axis_out nodes to the node.csv
    long_axis_in_node_id = generate_id()
    long_axis_out_node_id = generate_id()

    nodes_data.append({
        'node_id': long_axis_in_node_id,
        'yard_name': yard_name,
        'node_type': 'long_axis_in',
        'x_coord': long_axis_in_node[0],
        'y_coord': long_axis_in_node[1]
    })

    nodes_data.append({
        'node_id': long_axis_out_node_id,
        'yard_name': yard_name,
        'node_type': 'long_axis_out',
        'x_coord': long_axis_out_node[0],
        'y_coord': long_axis_out_node[1]
    })

    # Store coordinates for constructing LINESTRING geometries later
    node_coordinates[long_axis_in_node_id] = long_axis_in_node
    node_coordinates[long_axis_out_node_id] = long_axis_out_node

    # Add the long axis link to link.csv
    links_data.append({
        'from_node_id': long_axis_in_node_id,
        'to_node_id': long_axis_out_node_id,
        'link_type': 'main_track',
        'geometry': f"LINESTRING({long_axis_in_node[0]} {long_axis_in_node[1]}, {long_axis_out_node[0]} {long_axis_out_node[1]})"
    })

    # Add gate_in and gate_out points to node.csv
    for gate_in in gate_in_coords:
        gate_in_node_id = generate_id()
        nodes_data.append({
            'node_id': gate_in_node_id,
            'yard_name': yard_name,
            'node_type': 'gate_in',
            'x_coord': gate_in[0],
            'y_coord': gate_in[1]
        })
        node_coordinates[gate_in_node_id] = gate_in  # Store coordinates

        links_data.append({
            'from_node_id': gate_in_node_id,
            'to_node_id': long_axis_in_node_id,
            'link_type': 'bridge_in',
            'geometry': f"LINESTRING({gate_in[0]} {gate_in[1]}, {long_axis_in_node[0]} {long_axis_in_node[1]})"
        })

    for gate_out in gate_out_coords:
        gate_out_node_id = generate_id()
        nodes_data.append({
            'node_id': gate_out_node_id,
            'yard_name': yard_name,
            'node_type': 'gate_out',
            'x_coord': gate_out[0],
            'y_coord': gate_out[1]
        })
        node_coordinates[gate_out_node_id] = gate_out  # Store coordinates

        links_data.append({
            'from_node_id': gate_out_node_id,
            'to_node_id': long_axis_out_node_id,
            'link_type': 'bridge_out',
            'geometry': f"LINESTRING({gate_out[0]} {gate_out[1]}, {long_axis_out_node[0]} {long_axis_out_node[1]})"
        })

    # Generate siding tracks (parallel to the main track) on both sides
    lon_offset, lat_offset = meters_to_degrees(track_offset_meters, long_axis_in_node[1])

    for i in range(1, num_siding_tracks_per_side + 1):
        # Decrease length of the siding track outward
        track_length = main_track_length * (length_decrease_factor ** i)
        length_ratio = track_length / main_track_length

        # Compute new coordinates based on length_ratio, keeping it parallel to the main track
        siding_in_node_pos = (long_axis_in_node[0], long_axis_in_node[1] + i * lat_offset)
        siding_out_node_pos = (long_axis_out_node[0], long_axis_out_node[1] + i * lat_offset)

        siding_in_node_neg = (long_axis_in_node[0], long_axis_in_node[1] - i * lat_offset)
        siding_out_node_neg = (long_axis_out_node[0], long_axis_out_node[1] - i * lat_offset)

        siding_in_node_pos_id = generate_id()
        siding_in_node_neg_id = generate_id()
        siding_out_node_pos_id = generate_id()
        siding_out_node_neg_id = generate_id()

        # Add nodes and links for positive and negative siding tracks
        nodes_data.append({
            'node_id': siding_in_node_pos_id,
            'yard_name': yard_name,
            'node_type': 'track',
            'x_coord': siding_in_node_pos[0],
            'y_coord': siding_in_node_pos[1]
        })

        nodes_data.append({
            'node_id': siding_out_node_pos_id,
            'yard_name': yard_name,
            'node_type': 'track',
            'x_coord': siding_out_node_pos[0],
            'y_coord': siding_out_node_pos[1]
        })

        nodes_data.append({
            'node_id': siding_in_node_neg_id,
            'yard_name': yard_name,
            'node_type': 'track',
            'x_coord': siding_in_node_neg[0],
            'y_coord': siding_in_node_neg[1]
        })

        nodes_data.append({
            'node_id': siding_out_node_neg_id,
            'yard_name': yard_name,
            'node_type': 'track',
            'x_coord': siding_out_node_neg[0],
            'y_coord': siding_out_node_neg[1]
        })

        # Store coordinates for LINESTRING construction
        node_coordinates[siding_in_node_pos_id] = siding_in_node_pos
        node_coordinates[siding_out_node_pos_id] = siding_out_node_pos
        node_coordinates[siding_in_node_neg_id] = siding_in_node_neg
        node_coordinates[siding_out_node_neg_id] = siding_out_node_neg

        # Add positive siding track links to link.csv (parallel to the main track)
        links_data.append({
            'from_node_id': siding_in_node_pos_id,
            'to_node_id': siding_out_node_pos_id,
            'link_type': 'siding_track',
            'geometry': f"LINESTRING({siding_in_node_pos[0]} {siding_in_node_pos[1]}, {siding_out_node_pos[0]} {siding_out_node_pos[1]})"
        })

        # Add negative siding track links to link.csv (parallel to the main track)
        links_data.append({
            'from_node_id': siding_in_node_neg_id,
            'to_node_id': siding_out_node_neg_id,
            'link_type': 'siding_track',
            'geometry': f"LINESTRING({siding_in_node_neg[0]} {siding_in_node_neg[1]}, {siding_out_node_neg[0]} {siding_out_node_neg[1]})"
        })

        # Connect siding track in_nodes to the long_axis_in_node
        links_data.append({
            'from_node_id': siding_in_node_pos_id,
            'to_node_id': long_axis_in_node_id,
            'link_type': 'track',
            'geometry': f"LINESTRING({siding_in_node_pos[0]} {siding_in_node_pos[1]}, {long_axis_in_node[0]} {long_axis_in_node[1]})"
        })

        links_data.append({
            'from_node_id': siding_in_node_neg_id,
            'to_node_id': long_axis_in_node_id,
            'link_type': 'track',
            'geometry': f"LINESTRING({siding_in_node_neg[0]} {siding_in_node_neg[1]}, {long_axis_in_node[0]} {long_axis_in_node[1]})"
        })

        # Connect siding track out_nodes to the long_axis_out_node
        links_data.append({
            'from_node_id': siding_out_node_pos_id,
            'to_node_id': long_axis_out_node_id,
            'link_type': 'track',
            'geometry': f"LINESTRING({siding_out_node_pos[0]} {siding_out_node_pos[1]}, {long_axis_out_node[0]} {long_axis_out_node[1]})"
        })

        links_data.append({
            'from_node_id': siding_out_node_neg_id,
            'to_node_id': long_axis_out_node_id,
            'link_type': 'track',
            'geometry': f"LINESTRING({siding_out_node_neg[0]} {siding_out_node_neg[1]}, {long_axis_out_node[0]} {long_axis_out_node[1]})"
        })

# Convert node and link data to DataFrames and save to CSV
nodes_df = pd.DataFrame(nodes_data)
links_df = pd.DataFrame(links_data)

# Save to CSV, now with the geometry column in the links.csv file
nodes_df.to_csv('A_Network_node.csv', index=False)
links_df.to_csv('A_Network_link.csv', index=False)

print("Nodes and links with geometry have been saved to node.csv and link.csv")

