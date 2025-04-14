import streamlit as st
import ee
import folium
from datetime import datetime
import numpy as np
from pprint import pprint

st.write("Starting Green Cover Monitoring App...")

# Initialize Earth Engine
st.write("Initializing Earth Engine...")
try:
    ee.Initialize(project='ee-mdbaz02')  # Replace with your project ID
    st.write("Earth Engine initialized successfully.")
except ee.EEException as e:
    if 'Need to authenticate' in str(e):
        st.warning("Earth Engine needs authentication. This might happen on the first run in the cloud.")
        ee.Authenticate()
        ee.Initialize(project='ee-mdbaz02')  # Replace with your project ID
        st.write("Earth Engine initialized after authentication.")
    else:
        st.error(f"Earth Engine initialization error: {e}")
        st.stop()

# --- Define Area of Interest (Saudi Arabia) ---
st.write("Defining Area of Interest...")
saudi_arabia = ee.Geometry.Polygon(
    [[[34.5, 15.5], [56.5, 15.5], [56.5, 32.5], [34.5, 32.5], [34.5, 15.5]]]
)

# --- Date Range for Monitoring ---
st.write("Setting Date Range...")
start_date = '2024-01-01'  # Adjust as needed
end_date = datetime.now().strftime('%Y-%m-%d')

# --- Select Landsat Collection ---
st.write("Selecting Landsat Collection...")
landsat_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA')

# --- Function to Calculate NDVI ---
st.write("Defining NDVI Calculation Function...")
def calculate_ndvi(image):
    nir = image.select('B5')
    red = image.select('B4')
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return image.addBands(ndvi)

# --- Filter the Collection ---
st.write("Filtering Landsat Collection...")
filtered_landsat = landsat_collection.filterDate(start_date, end_date) \
    .filterBounds(saudi_arabia) \
    .filter(ee.Filter.lt('CLOUD_COVER', 30))

# --- Apply NDVI Calculation ---
st.write("Calculating NDVI for the collection...")
ndvi_collection = filtered_landsat.map(calculate_ndvi)

# --- Reduce the Collection (e.g., get the maximum NDVI composite) ---
st.write("Creating NDVI Composite...")
composite_image = ndvi_collection.qualityMosaic('NDVI')

# --- Visualization Parameters ---
ndvi_palette = ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                '74A901', '66A000', '529400', '3D8500', '107400', '115200',
                '0B1D00', '030D00']
ndvi_vis_params = {'min': -1, 'max': 1, 'palette': ndvi_palette}

# --- Streamlit Application ---
st.title("Saudi Arabia Green Cover Monitor (Landsat)")
st.subheader(f"Monitoring Period: {start_date} to {end_date}")
st.info("This application uses Landsat 8 imagery to monitor green cover (NDVI) in Saudi Arabia. Data is sourced from Google Earth Engine and is generally updated within a day or two of satellite overpass.")

# --- Display the NDVI Composite on a Map ---
st.subheader("Latest Green Cover (NDVI Composite)")
st.write("Generating Map...")
map_saudi = folium.Map(location=[24.7136, 46.6753], zoom_start=5)  # Approximate center of Saudi Arabia

# Get the Map ID and Token from Earth Engine
st.write("Getting Map ID from Earth Engine...")
map_id_dict = ee.mapclient.get_map_id({'image': composite_image, 'params': ndvi_vis_params})
folium.TileLayer(
    tiles=map_id_dict['tile_fetcher'].url_format,
    attr='Google Earth Engine',
    overlay=True,
    name='NDVI',
).add_to(map_saudi)

# Display the map in Streamlit
st.write("Displaying Map in Streamlit...")
from streamlit_folium import st_folium
st_folium(map_saudi, width=700, height=500)
st.caption("NDVI values range from -1 to 1, where higher values (towards green in the palette) indicate denser green vegetation.")

# --- Time Series Analysis (Optional but Recommended for Monitoring) ---
st.subheader("NDVI Time Series (Average over Saudi Arabia)")
st.info("This section shows the trend of average NDVI over time for the selected period. It might take a moment to load.")

def calculate_mean_ndvi(image):
    ndvi = image.select('NDVI')
    mean_ndvi = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=saudi_arabia,
        scale=30,  # Match Landsat resolution
        maxPixels=1e9
    )
    return mean_ndvi.set('date', image.date().format())

st.write("Calculating NDVI Time Series...")
try:
    ndvi_timeseries = ndvi_collection.map(calculate_mean_ndvi).getInfo()

    if ndvi_timeseries and 'features' in ndvi_timeseries:
        st.write("Processing Time Series Data...")
        dates = [datetime.strptime(f['properties']['date']['value'], '%Y-%m-%dT%H:%M:%S.%fZ') for f in ndvi_timeseries['features']]
        ndvi_values = [f['properties']['NDVI'] for f in ndvi_timeseries['features']]

        import pandas as pd
        df_timeseries = pd.DataFrame({'Date': dates, 'Average NDVI': ndvi_values})
        df_timeseries = df_timeseries.sort_values(by='Date')
        df_timeseries = df_timeseries.set_index('Date')

        st.write("Displaying Time Series Chart...")
        st.line_chart(df_timeseries)
        st.caption("Average NDVI for Saudi Arabia over time. Gaps might occur due to cloud cover filtering or data availability.")
    else:
        st.warning("Could not retrieve NDVI time series data.")

except Exception as e:
    st.error(f"Error generating NDVI time series: {e}")

# --- Get Pixel Data for a Specific Location ---
st.subheader("Get Pixel Data for a Specific Location")
st.write("Setting up Pixel Data Retrieval...")
latitude = st.number_input("Enter Latitude:", value=24.7136)
longitude = st.number_input("Enter Longitude:", value=46.6753)

if st.button("Get Pixel Data"):
    st.write("Fetching Pixel Data...")
    point = ee.Geometry.Point(longitude, latitude)
    start_date_pixel = '2024-01-01'
    end_date_pixel = datetime.now().strftime('%Y-%m-%d')

    landsat_collection_pixel = ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA')
    filtered_collection_pixel = landsat_collection_pixel.filterDate(start_date_pixel, end_date_pixel).filterBounds(point)
    first_image_pixel = filtered_collection_pixel.first()

    if first_image_pixel:
        st.write("Processing Pixel Data Metadata...")
        metadata = first_image_pixel.getInfo()
        st.json(metadata)

        red_band_pixel = first_image_pixel.select('B4')
        region_pixel = point.buffer(100).bounds()  # Small buffer for pixel data
        st.write("Sampling Pixel Data...")
        array_dict_pixel = red_band_pixel.sampleRectangle(region=region_pixel).getInfo()

        st.write("\nPixel values of the Red band (dictionary format):")
        st.json(array_dict_pixel)
    else:
        st.warning(f"No Landsat images found for the specified date and location.")

st.info("Data is typically updated within a day or two after satellite acquisition.")
