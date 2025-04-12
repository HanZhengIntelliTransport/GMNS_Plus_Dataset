import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

# Step 1: Create city data
cities = pd.DataFrame({
    "city": ["Seattle", "Portland", "San Francisco", "Las Vegas", "Phoenix", "Denver", "Dallas", "Austin", "New Orleans",
             "Minneapolis", "Milwaukee", "Chicago", "Pittsburgh", "Atlanta", "Miami", "Washington", "Philadelphia", "New York", "Boston", "Honolulu"],
    "longitude": [-122.33, -122.67, -122.42, -115.15, -112.07, -104.99, -96.80, -97.74, -90.07,
                  -93.27, -87.91, -87.63, -79.99, -84.39, -80.19, -77.04, -75.17, -74.01, -71.06, -157.86],
    "latitude": [47.61, 45.52, 37.77, 36.17, 33.45, 39.74, 32.78, 30.27, 29.95,
                 44.98, 43.04, 41.88, 40.44, 33.75, 25.76, 38.90, 39.95, 40.71, 42.36, 21.31]
})

# Step 2: Convert city data to GeoDataFrame
geometry = [Point(xy) for xy in zip(cities["longitude"], cities["latitude"])]
geo_cities = gpd.GeoDataFrame(cities, geometry=geometry, crs="EPSG:4326")

# Step 3: Load the US base map from GeoPandas built-in dataset
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
usa = world[world['name'] == 'United States of America']

# Step 4: Plot the map
fig, ax = plt.subplots(figsize=(12, 8))
usa.boundary.plot(ax=ax, linewidth=1, color='black')            # Plot country boundary
geo_cities.plot(ax=ax, color='red', markersize=50)              # Plot city points

# Step 5: Add city labels
for x, y, label in zip(geo_cities.geometry.x, geo_cities.geometry.y, geo_cities["city"]):
    ax.text(x + 0.5, y + 0.5, label, fontsize=9)

# Step 6: Final touches
ax.set_title("The Geospatial Distribution of 20 Representative U.S. Cities", fontsize=14)
ax.set_axis_off()

plt.show()
