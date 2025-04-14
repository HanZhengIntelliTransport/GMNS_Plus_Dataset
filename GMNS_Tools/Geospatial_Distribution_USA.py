import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point

# Load city data
cities = pd.DataFrame({
    "city": ["Seattle", "Portland", "San Francisco", "Las Vegas", "Phoenix", "Denver", "Dallas", "Austin", "New Orleans",
             "Minneapolis", "Milwaukee", "Chicago", "Pittsburgh", "Atlanta", "Miami", "Washington", "Philadelphia", "New York", "Boston", "Honolulu"],
    "longitude": [-122.33, -122.67, -122.42, -115.15, -112.07, -104.99, -96.80, -97.74, -90.07,
                  -93.27, -87.91, -87.63, -79.99, -84.39, -80.19, -77.04, -75.17, -74.01, -71.06, -157.86],
    "latitude": [47.61, 45.52, 37.77, 36.17, 33.45, 39.74, 32.78, 30.27, 29.95,
                 44.98, 43.04, 41.88, 40.44, 33.75, 25.76, 38.90, 39.95, 40.71, 42.36, 21.31]
})

geometry = [Point(xy) for xy in zip(cities["longitude"], cities["latitude"])]
geo_cities = gpd.GeoDataFrame(cities, geometry=geometry, crs="EPSG:4326")

# Load Natural Earth Admin 1 (states/provinces)
states = gpd.read_file("ne_110m_admin_1_states_provinces/ne_110m_admin_1_states_provinces.shp")
usa_states = states[states["admin"] == "United States of America"]

# Create city GeoDataFrame subsets
cities_conus = geo_cities[~geo_cities['city'].isin(["Honolulu"])]
cities_ak = geo_cities[geo_cities['city'] == "Honolulu"]  # fix later if you add Alaska cities

# Split map by regions
ak = usa_states[usa_states["name"] == "Alaska"]
hi = usa_states[usa_states["name"] == "Hawaii"]
conus = usa_states[~usa_states["name"].isin(["Alaska", "Hawaii"])]

# Set up subplots
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6),
                                    gridspec_kw={'width_ratios': [2.5, 1, 1]})

# Plot CONUS
conus.boundary.plot(ax=ax1, linewidth=1)
cities_conus.plot(ax=ax1, color='red', markersize=50)
for x, y, label in zip(cities_conus.geometry.x, cities_conus.geometry.y, cities_conus["city"]):
    ax1.text(x + 0.5, y + 0.5, label, fontsize=8)
ax1.set_title("Continental U.S.")
ax1.set_axis_off()

# Plot Alaska
ak.boundary.plot(ax=ax2, linewidth=1)
# If you have AK cities, plot them here
ax2.set_title("Alaska")
ax2.set_axis_off()

# Plot Hawaii
hi.boundary.plot(ax=ax3, linewidth=1)
cities_ak.plot(ax=ax3, color='red', markersize=50)
for x, y, label in zip(cities_ak.geometry.x, cities_ak.geometry.y, cities_ak["city"]):
    ax3.text(x + 0.5, y + 0.5, label, fontsize=8)
ax3.set_title("Hawaii")
ax3.set_axis_off()

# Overall title
fig.suptitle("The Geospatial Distribution of 20 Representative U.S. Cities", fontsize=16)

plt.tight_layout()
plt.subplots_adjust(top=0.85)
plt.show()
