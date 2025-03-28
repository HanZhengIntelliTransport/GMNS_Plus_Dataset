import pandas as pd
import geopandas as gpd
from shapely import wkt
# from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
from sklearn.cluster import MiniBatchKMeans

# === PARAMETERS ===
INPUT_CSV = "poi.csv"  # Replace with your actual file path if different
OUTPUT_CSV = "poi_aggregated.csv"
N_CLUSTERS = 18000  # You can change this as needed

print("Step 1: Reading and preprocessing data...")

# === STEP 1: Load and preprocess ===
df = pd.read_csv(INPUT_CSV, dtype=str)


# Convert WKT strings to shapely objects
df['centroid'] = df['centroid'].apply(wkt.loads)
df['geometry'] = df['geometry'].apply(wkt.loads)

# Convert to GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry='geometry')

# Extract coordinates from centroids for clustering
coords = df['centroid'].apply(lambda pt: [pt.x, pt.y]).tolist()
print(f"Loaded {len(df)} rows. Beginning clustering...")

# === STEP 2: Clustering ===
kmeans = MiniBatchKMeans(n_clusters=N_CLUSTERS, random_state=0, batch_size=4096).fit(coords)
df['cluster'] = kmeans.labels_

print(f"Clustering completed. Formed {N_CLUSTERS} clusters.")

# === STEP 3: Aggregation by cluster ===
print("Step 3: Aggregating rows within each cluster...")
aggregated = []

for cluster_id, group in df.groupby('cluster'):
    print(f"  Aggregating cluster {cluster_id} with {len(group)} items...")

    # combined_geometry = MultiPolygon(group['geometry'].tolist()).buffer(0)

    # Clean invalid geometries before union
    clean_geometries = [geom.buffer(0) for geom in group['geometry']]

    combined_geometry = unary_union(clean_geometries)

    combined_centroid = combined_geometry.centroid

    agg_row = {
        'name': ','.join(group['name'].dropna().astype(str)),
        'poi_id': cluster_id,
        'osm_way_id': ','.join(group['osm_way_id'].dropna().astype(str)),
        'osm_relation_id': ','.join(
            group['osm_relation_id'].dropna().astype(str)) if 'osm_relation_id' in group else '',
        'building': ','.join(group['building'].dropna().astype(str)),
        'amenity': ','.join(group['amenity'].dropna().astype(str)),
        'way': ','.join(group['way'].dropna().astype(str)),
        'geometry': combined_geometry,
        'centroid': combined_centroid,
        'area': round(group['area'].astype(float).sum(), 2),
        'area_ft2': round(group['area_ft2'].astype(float).sum(), 2)
    }
    aggregated.append(agg_row)

print("Aggregation completed.")

# === STEP 4: Create GeoDataFrame and Save ===
print("Step 4: Writing output to CSV...")

agg_gdf = gpd.GeoDataFrame(aggregated)
agg_gdf['centroid'] = agg_gdf['centroid'].astype(str)
agg_gdf['geometry'] = agg_gdf['geometry'].astype(str)

agg_gdf.to_csv(OUTPUT_CSV, index=False)

print(f"✅ Done! Aggregated results saved to: {OUTPUT_CSV}")
