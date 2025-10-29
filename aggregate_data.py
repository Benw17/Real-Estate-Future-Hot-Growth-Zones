import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium

# 1. Load SA2 shapefile
shapefile_path = "data/SA2_2021_AUST_GDA2020.shp"
gdf = gpd.read_file(shapefile_path)

# 2. Load housing CSV
csv_path = "data/2021Census_G37_AUST_SA2.csv"
housing = pd.read_csv(csv_path)

# Strip whitespace and convert SA2 codes to string
gdf['SA2_CODE21'] = gdf['SA2_CODE21'].astype(str).str.strip()
housing['SA2_CODE_2021'] = housing['SA2_CODE_2021'].astype(str).str.strip()

# Ensure Total_Total is numeric
housing['Total_Total'] = pd.to_numeric(housing['Total_Total'], errors='coerce')
housing = housing.dropna(subset=['Total_Total'])

# 3. Merge shapefile and housing data
gdf = gdf.merge(
    housing[['SA2_CODE_2021', 'Total_Total']],
    left_on='SA2_CODE21',
    right_on='SA2_CODE_2021',
    how='inner'
)

# 4. Compute housing density
gdf['housing_density'] = gdf['Total_Total'] / gdf['AREASQKM21']

# 5. Identify high-density areas

high_density_threshold = gdf['housing_density'].quantile(0.70) # Top 30%
developed = gdf[gdf['housing_density'] >= high_density_threshold]

# 6. Create hot zones (buffered areas around high-density with room for growth)

# Project to meters for accurate buffering
gdf_m = gdf.to_crs(epsg=3857)
developed_m = developed.to_crs(epsg=3857)

# Buffer distance in meters
buffer_distance = 10000  # 10 km
buffered = developed_m.copy()
buffered['geometry'] = buffered.geometry.buffer(buffer_distance)

# Hot zones
hot_zones_m = gdf_m[gdf_m.geometry.intersects(buffered.unary_union)]
hot_zones_m = hot_zones_m[~hot_zones_m['SA2_CODE21'].isin(developed['SA2_CODE21'])]

# 7. Filter hot zones by realistic growth density
min_density = 10
max_density = 200
hot_zones_m = hot_zones_m[
    (hot_zones_m['housing_density'] >= min_density) &
    (hot_zones_m['housing_density'] <= max_density)
]

# 8. Static Map
plt.figure(figsize=(12,12))

# Base map (light grey)
gdf_m.plot(color='lightgrey', edgecolor='black', alpha=0.7)

# High-density areas (purple)
developed_m.plot(color='purple', edgecolor='black', alpha=0.7)

# Growth-ready hot zones (red)
hot_zones_m.plot(color='red', edgecolor='black', alpha=0.6)

plt.title("High-Density Areas (Purple) and Growth-Ready Hot Zones (Red)")
plt.axis('off')

# 9. Interactive Map with Folium

# Convert back to WGS84 for folium
gdf_f = gdf_m.to_crs(epsg=4326)
developed_f = developed_m.to_crs(epsg=4326)
hot_zones_f = hot_zones_m.to_crs(epsg=4326)

# Remove any missing geometries
gdf_f = gdf_f[~gdf_f['geometry'].isna()]
developed_f = developed_f[~developed_f['geometry'].isna()]
hot_zones_f = hot_zones_f[~hot_zones_f['geometry'].isna()]

# Create Folium map
m = folium.Map(location=[-25, 135], zoom_start=4)

# All areas in light grey
for _, row in gdf_f.iterrows():
    folium.GeoJson(
        row['geometry'],
        style_function=lambda f: {'color':'grey','fillOpacity':0.2}
    ).add_to(m)

# Developed areas in purple
for _, row in developed_f.iterrows():
    folium.GeoJson(
        row['geometry'],
        style_function=lambda f: {'fillColor':'purple','color':'purple','fillOpacity':0.7},
        tooltip=f"{row['SA2_CODE21']}: {row['housing_density']:.1f} dwellings/km²"
    ).add_to(m)

# Hot zones in red
for _, row in hot_zones_f.iterrows():
    folium.GeoJson(
        row['geometry'],
        style_function=lambda f: {'fillColor':'red','color':'red','fillOpacity':0.6},
        tooltip=f"{row['SA2_CODE21']}: {row['housing_density']:.1f} dwellings/km²"
    ).add_to(m)

# Save interactive map
m.save("growth_ready_hot_zone_map.html")
print("Interactive map saved as growth_ready_hot_zone_map.html")
