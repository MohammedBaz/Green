import streamlit as st
import ee
#import ee.mapclient
import folium
from datetime import datetime
import numpy as np
from pprint import pprint

# Initialize Earth Engine
try:
    ee.Initialize(project='ee-mdbaz02')  # Replace with your project ID
except ee.EEException as e:
    if 'Need to authenticate' in str(e):
        print("You need to authenticate Earth Engine.")
        ee.Authenticate()
        ee.Initialize(project='ee-mdbaz02')  # Replace with your project ID
        print("Earth Engine has been initialized after authentication.")
    else:
        st.error(f"Earth Engine initialization error: {e}")
        st.stop()

# ... (Your existing Streamlit code for map display and time series) ...

st.subheader("Get Pixel Data for a Specific Location")

# Get user input for latitude and longitude
latitude = st.number_input("Enter Latitude:", value=24.7136)
longitude = st.number_input("Enter Longitude:", value=46.6753)

if st.button("Get Pixel Data"):
    point = ee.Geometry.Point(longitude, latitude)
    start_date = '2024-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')

    landsat_collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA')
    filtered_collection = landsat_collection.filterDate(start_date, end_date).filterBounds(point)
    first_image = filtered_collection.first()

    if first_image:
        st.write("Metadata of the first image:")
        metadata = first_image.getInfo()
        st.json(metadata)

        red_band = first_image.select('B4')
        region = point.buffer(100).bounds()  # Small buffer for pixel data
        array_dict = red_band.sampleRectangle(region=region).getInfo()

        st.write("\nPixel values of the Red band (dictionary format):")
        st.json(array_dict)
    else:
        st.warning(f"No Landsat images found for the specified date and location.")
