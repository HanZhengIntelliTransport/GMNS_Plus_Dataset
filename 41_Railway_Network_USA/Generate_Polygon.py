import json
import pandas as pd
from shapely.geometry import MultiLineString, LineString, Polygon
from shapely.ops import unary_union
import math

# Load the GeoJSON file using json
with open('NTAD_Rail_Yards.geojson', 'r') as f:
    geojson_data = json.load(f)

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

# Function to create a minimized polygon with margin 'd' around the MultiLineString or LineString geometry
def create_envelope_polygon(coordinates, d):
    if not coordinates or not isinstance(coordinates, list):
        return None
    try:
        # Create a LineString or MultiLineString geometry
        lines = MultiLineString(coordinates) if len(coordinates) > 1 else LineString(coordinates[0])

        # Create a convex hull polygon that envelopes the lines
        envelope_polygon = lines.convex_hull

        # Create a buffer around the polygon (to simulate margin 'd')
        buffered_polygon = envelope_polygon.buffer(d / 111320)  # Convert meters to degrees (approx. conversion)

        # Simplify the polygon to reduce the number of points (up to 6 points)
        minimized_polygon = buffered_polygon.simplify(0.01, preserve_topology=True)

        # Ensure the polygon has no more than 6 points
        if len(minimized_polygon.exterior.coords) > 6:
            minimized_polygon = Polygon(minimized_polygon.exterior.coords[:6])

        return minimized_polygon
    except Exception as e:
        print(f"Error creating polygon: {e}")
        return None


# Set margin 'd' in meters (e.g., 50 meters)
d = 50

# Now, process the geometries to generate the polygons for each yard
yard_data_with_polygons = []
for feature in geojson_data['features']:
    try:
        # Extract YARDNAME from properties
        properties = feature.get('properties', {})
        yard_name = properties.get('YARDNAME', 'Unknown')

        # Extract coordinates from geometry (which are MultiLineString or LineString)
        geometry = feature.get('geometry', {})
        coordinates = []
        if geometry.get('type') == 'LineString':
            coordinates = [geometry.get('coordinates', [])]  # Wrap in list for uniformity
        elif geometry.get('type') == 'MultiLineString':
            coordinates = geometry.get('coordinates', [])

        # Skip rows with missing or malformed data
        if yard_name == 'Unknown' or not coordinates:
            continue

        # Generate a minimized polygon if valid coordinates exist
        polygon = create_envelope_polygon(coordinates, d)
        long_axis_nodes=find_longest_pair(polygon)
        if polygon:
            yard_data_with_polygons.append({
                'YardName': yard_name,
                'Polygon_WKT': polygon.wkt,
                'Main_Direction':long_axis_nodes
            })
        else:
            print(f"Invalid geometry for Yard: {yard_name}")
    except Exception as e:
        print(f"Error processing feature: {e}")

# Convert the data into a DataFrame for easier manipulation
yard_polygons_df = pd.DataFrame(yard_data_with_polygons)
yard_polygons_df.index += 1  # Auto-index starting from 1

# Insert an auto-increment index as the first column
yard_polygons_df.reset_index(drop=True, inplace=True)
yard_polygons_df.index += 1  # Auto-index starting from 1
yard_polygons_df.insert(0, 'ID', yard_polygons_df.index)

# Remove any empty or invalid columns (if any)
yard_polygons_df = yard_polygons_df[['ID', 'YardName', 'Polygon_WKT','Main_Direction']]

# Save the updated DataFrame with the auto-index to a new CSV file
csv_file_with_autoindex = "rail_yards_polygons.csv"
yard_polygons_df.to_csv(csv_file_with_autoindex, index=False)