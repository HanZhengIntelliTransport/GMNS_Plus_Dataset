import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import os

# Step 1: City data
city_data = pd.DataFrame({
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
    ],
    "country": [
        "United States", "United States", "United States", "Germany", "United Kingdom", "United States", "United States",
        "United States", "United States", "Australia", "United States", "United States", "United States", "United States",
        "United States", "United States", "United States", "United States", "United States", "United States",
        "United States", "United States", "United States", "United States", "Australia", "United States"
    ]
})

# Step 2: Convert to GeoDataFrame
geometry = [Point(xy) for xy in zip(city_data["longitude"], city_data["latitude"])]
geo_cities = gpd.GeoDataFrame(city_data, geometry=geometry, crs="EPSG:4326")

# Step 3: Load shapefile
admin1_path = "ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp"
admin1 = gpd.read_file(admin1_path)

# Step 4: Country name mapping
country_name_mapping = {
    "United States": "United States of America",
    "Germany": "Germany",
    "United Kingdom": "United Kingdom",
    "Australia": "Australia"
}

# Step 5: Create output folder
output_dir = "country_maps"
os.makedirs(output_dir, exist_ok=True)

# Step 6: Arrowed label helper
def annotate_city_labels(ax, cities, dx=1.5, dy=1.0):
    for x, y, label in zip(cities.geometry.x, cities.geometry.y, cities["city"]):
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(x + dx, y + dy),
            textcoords="data",
            fontsize=9,
            color="red",
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
            ha="left", va="center"
        )

# Step 7: Process each country
for country in geo_cities["country"].unique():
    mapped_country = country_name_mapping.get(country, country)
    cities = geo_cities[geo_cities["country"] == country]
    country_shape = admin1[admin1["admin"] == mapped_country]

    if country == "United States":
        ak = country_shape[country_shape["name"] == "Alaska"]
        hi = country_shape[country_shape["name"] == "Hawaii"]
        conus = country_shape[~country_shape["name"].isin(["Alaska", "Hawaii"])]

        cities_ak = cities[cities["city"] == "Honolulu"]
        cities_conus = cities[~cities["city"].isin(["Honolulu"])]
        cities_hi = cities_ak

        # --- CONUS ---
        fig, ax = plt.subplots(figsize=(12, 8))
        conus.boundary.plot(ax=ax, linewidth=1, edgecolor="black")
        cities_conus.plot(ax=ax, color='red', markersize=60)
        annotate_city_labels(ax, cities_conus)
        ax.set_title("United States – CONUS (Mainland)")
        ax.set_axis_off()
        fig.savefig(os.path.join(output_dir, "United_States_CONUS.png"), dpi=300, bbox_inches='tight')
        plt.close(fig)

        # --- Alaska (zoomed) ---
        fig, ax = plt.subplots(figsize=(10, 6))
        ak.boundary.plot(ax=ax, linewidth=1, edgecolor="black")
        ax.set_xlim(-180, -130)
        ax.set_ylim(50, 72)
        ax.set_title("United States – Alaska")
        ax.set_axis_off()
        fig.savefig(os.path.join(output_dir, "United_States_Alaska.png"), dpi=300, bbox_inches='tight')
        plt.close(fig)

        # --- Hawaii ---
        fig, ax = plt.subplots(figsize=(8, 6))
        hi.boundary.plot(ax=ax, linewidth=1, edgecolor="black")
        cities_hi.plot(ax=ax, color='red', markersize=60)
        annotate_city_labels(ax, cities_hi)
        ax.set_title("United States – Hawaii")
        ax.set_axis_off()
        fig.savefig(os.path.join(output_dir, "United_States_Hawaii.png"), dpi=300, bbox_inches='tight')
        plt.close(fig)

        print("✅ Saved CONUS, Alaska, and Hawaii maps.")

    elif not country_shape.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        country_shape.boundary.plot(ax=ax, linewidth=1, edgecolor="black")
        cities.plot(ax=ax, color='red', markersize=60)
        annotate_city_labels(ax, cities,2,2)
        ax.set_title(f"{country} – Geospatial Distribution of Cities")
        ax.set_axis_off()
        filename = f"{country.replace(' ', '_')}_map.png"
        fig.savefig(os.path.join(output_dir, filename), dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"✅ Saved: {filename}")

    else:
        print(f"⚠️ Warning: No boundary found for '{country}' in shapefile.")

print("\n🎉 All maps with arrows and annotations are saved in 'country_maps/' folder.")
