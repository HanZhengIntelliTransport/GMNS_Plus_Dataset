from shapely.wkt import loads
from geopy.distance import geodesic

def calculate_linestring_length(wkt_string):
    # Load the WKT LineString
    line = loads(wkt_string)

    # Get the coordinates and swap them (WKT format is LONG LAT, but geopy needs LAT LONG)
    coords = [(lat, lon) for lon, lat in line.coords]

    # Compute total length in meters
    total_length = sum(geodesic(coords[i], coords[i + 1]).meters for i in range(len(coords) - 1))

    return total_length

# Example usage:
linestring_wkt = "LINESTRING (23.5506 18.9009, 23.6731 19.0991)"
length_meters = calculate_linestring_length(linestring_wkt)
print(f"Length: {length_meters:.2f} meters")

# %%
from shapely.wkt import loads

def generate_google_maps_link(wkt_string):
    # Load the WKT LineString
    line = loads(wkt_string)

    # Extract coordinates and swap (WKT uses LONG LAT, but Google Maps needs LAT LONG)
    coord_pairs = [f"{lat},{lon}" for lon, lat in line.coords]

    # Construct the Google Maps URL
    google_maps_url = "https://www.google.com/maps/dir/" + "/".join(coord_pairs)

    return google_maps_url

# Example usage:
linestring_wkt = "LINESTRING (-117.81516143365 33.85017260317939, -117.82041419826294 33.84665693703933)"
maps_link = generate_google_maps_link(linestring_wkt)
print("Google Maps Link:", maps_link)
