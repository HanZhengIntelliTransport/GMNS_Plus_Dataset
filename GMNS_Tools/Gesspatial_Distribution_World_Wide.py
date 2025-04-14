import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point

# Final city coordinate table
city_coords = pd.DataFrame({
    "city": [
        "Anaheim", "Atlanta", "Austin", "Berlin", "Birmingham", "Boston", "Chicago", "Dallas", "Denver", "Gold Coast",
        "Honolulu", "Las Vegas", "Miami", "Milwaukee", "Minneapolis", "New Orleans", "New York", "Philadelphia",
        "Phoenix", "Pittsburgh", "Portland", "San Francisco", "Seattle", "Sioux Falls", "Sydney", "Washington, D.C."
    ],
    "latitude": [
        33.8353, 33.7490, 30.2672, 52.5200, 52.4862, 42.3601, 41.8781, 32.7767, 39.7392, -28.0167,
        21.3069, 36.1699, 25.7617, 43.0389, 44.9778, 29.9511, 40.7128, 39.9526,
        33.4484, 40.4406, 45.5051, 37.7749, 47.6062, 43.5446, -33.8688, 38.9072
    ],
    "longitude": [
        -117.9145, -84.3880, -97.7431, 13.4050, -1.8904, -71.0589, -87.6298, -96.7970, -104.9903, 153.4000,
        -157.8583, -115.1398, -80.1918, -87.9065, -93.2650, -90.0715, -74.0060, -75.1652,
        -112.0740, -79.9959, -122.6750, -122.4194, -122.3321, -96.7311, 151.2093, -77.0369
    ]
})

# Create GeoDataFrame
geometry = [Point(xy) for xy in zip(city_coords["longitude"], city_coords["latitude"])]
geo_cities = gpd.GeoDataFrame(city_coords, geometry=geometry, crs="EPSG:4326")

# Load world boundaries shapefile (assumes correct path)
world = gpd.read_file("ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")

# Plot the map
fig, ax = plt.subplots(figsize=(18, 9))
world.boundary.plot(ax=ax, linewidth=0.5, edgecolor='black')
geo_cities.plot(ax=ax, color='red', markersize=50)

# Add labels
for x, y, label in zip(geo_cities.geometry.x, geo_cities.geometry.y, geo_cities["city"]):
    ax.text(x + 1, y, label, fontsize=8)

# Styling
ax.set_title("Geospatial Distribution of 25 Representative Cities Worldwide", fontsize=16)
ax.set_axis_off()
plt.show()
