import os
try:
    import ee
except ImportError:
    print("Please install Earth Engine API: pip install earthengine-api")
    print("Then authenticate using: earthengine authenticate")
    exit(1)

def main():
    print("Initializing Google Earth Engine...")
    try:
        ee.Initialize(project='your-google-project-id') # The user must have a Google Cloud Project for EE
    except Exception as e:
        print(f"Earth Engine Initialization Failed. Please run 'earthengine authenticate'. Error: {e}")
        return

    # MapBiomas Collection 9 (Annual Land Cover/Use)
    print("Loading MapBiomas Collection 9...")
    mapbiomas = ee.Image('projects/mapbiomas-workspace/public/collection9/mapbiomas_collection90_integration_v1')

    # SP State Boundary for clipping
    sp_boundary = ee.FeatureCollection("FAO/GAUL/2015/level1") \
                    .filter(ee.Filter.eq('ADM1_NAME', 'Sao Paulo'))

    years = [2013, 2022] # We can compare the start of the SINAN cohort to the end
    output_dir = "Data/MapBiomas_Urban_SP"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for year in years:
        band_name = f'classification_{year}'
        print(f"Processing MapBiomas Band: {band_name}")
        
        # Select the specific year and clip to SP State
        image_year = mapbiomas.select(band_name).clip(sp_boundary)
        
        # In MapBiomas Col 9, Urban Infrastructure is generally Class 24.
        # Check MapBiomas legend to confirm if 'Áreas Informais' got mapped to a sub-class (e.g. 32)
        # We will export the full categorical raster for the state so it can be vector-converted or masked later.
        
        task_name = f"Export_MapBiomas_SP_{year}"
        print(f"Starting GEE Export Task: {task_name} (Check Earth Engine Tasks tab online or wait for completion)")
        
        task = ee.batch.Export.image.toDrive(
            image=image_year,
            description=task_name,
            folder='MapBiomas_Downloads',
            scale=30, # MapBiomas is 30m resolution
            region=sp_boundary.geometry().bounds(),
            maxPixels=1e13
        )
        task.start()

    print("\nTasks successfully submitted to Google Earth Engine!")
    print("The GeoTIFF files will beautifully appear in your Google Drive 'MapBiomas_Downloads' folder once completed.")
    print("From there, we can extract the exact pixels that grew between 2013 and 2022 to identify the true new informal growth!")

if __name__ == "__main__":
    main()
