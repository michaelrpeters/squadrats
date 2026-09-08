import os
import csv
import time
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_rankings():
    # --- 1. CREDENTIALS & SETUP ---
    SQUADRATS_EMAIL = "squadrats@cornut.com.au"
    SQUADRATS_PASSWORD = "qebtop-cuhmu9-xoqkId"
    
    profile_url = "https://squadrats.com/u/B9KS1EA5qaZO7TG1d471EB97R5J3"
    login_url = "https://squadrats.com/login"
    map_url = "https://squadrats.com/map/earth"
    
    # Generate today's datestamp (e.g., 2026-09-02_143000)
    datestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    current_folder = os.getcwd()
    
    print("Configuring Chrome to download to the current folder...")
    chrome_options = Options()
    prefs = {
        "download.default_directory": current_folder, 
        "download.prompt_for_download": False,
        "directory_upgrade": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    print("Launching Chrome browser...")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15) 
    
    try:
        # --- 2. GO DIRECTLY TO LOGIN ---
        print("Navigating to login page...")
        driver.get(login_url)
        
        email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        email_field.send_keys(SQUADRATS_EMAIL)
        
        password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        password_field.send_keys(SQUADRATS_PASSWORD)
        password_field.send_keys(Keys.RETURN)
        
        # --- 3. FORCE NAVIGATION TO PROFILE ---
        print("Logged in! Waiting for cookies to settle...")
        time.sleep(3) 
        
        print("Jumping straight to your profile page...")
        driver.get(profile_url) 
        time.sleep(3) 

        # --- 4. FAST SCROLL TO BOTTOM ---
        print("Scrolling to the bottom to trigger all lazy-loaded tiles...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # --- 5. DOM-BASED WAIT FOR NORTH CAROLINA ---
        print("Reached the bottom! Waiting for North Carolina's stats to populate (max 90s)...")
        
        max_attempts = 90
        nc_loaded = False
        
        for attempt in range(max_attempts):
            try:
                tile_bars = driver.find_elements(By.CSS_SELECTOR, ".tile-bar")
                for bar in tile_bars:
                    region_name = bar.find_element(By.CSS_SELECTOR, ".region-name").text
                    if "North Carolina" in region_name:
                        rank = bar.find_element(By.CSS_SELECTOR, ".rank").text
                        if len(rank.strip()) > 1: 
                            nc_loaded = True
                            break
                            
                if nc_loaded:
                    print(f"North Carolina data fully loaded after {attempt + 1} seconds!")
                    break 
            except Exception:
                pass
            time.sleep(1)

        # --- 6. THE DEEP EXTRACTION LOOP ---
        print("\nExtracting ALL data, clicking through every stat for every region...")
        time.sleep(2) 
        
        final_rankings = []
        tiles = driver.find_elements(By.CSS_SELECTOR, "a.region-cell")
        total_tiles = len(tiles)
        
        print(f"Found {total_tiles} regions to process. This will take a moment...\n")
        
        for i, tile in enumerate(tiles, start=1):
            try:
                # Get the region name (this stays the same for the whole tile)
                region = driver.execute_script("return arguments[0].querySelector('.region-name').innerText;", tile).strip()
                
                print(f"[{i}/{total_tiles}] Extracting stats for {region}...")
                
                row_data = {'Region': region}
                dots = tile.find_elements(By.CSS_SELECTOR, ".cell-meta .dot")
                
                for dot in dots:
                    # Identify which stat we are looking at (e.g., "Yardinho")
                    stat_name = dot.get_attribute("aria-label").replace("Show ", "").strip()
                    
                    # Click the dot
                    driver.execute_script("arguments[0].click();", dot)
                    time.sleep(0.15) # Wait 150ms for the page numbers to recalculate
                    
                    # NOW extract both the newly updated rank and the count!
                    # Added safety checks in case a user has zero stats and the element doesn't render
                    rank = driver.execute_script("return arguments[0].querySelector('.rank') ? arguments[0].querySelector('.rank').innerText : 'N/A';", tile).strip()
                    count = driver.execute_script("return arguments[0].querySelector('.meta-count') ? arguments[0].querySelector('.meta-count').innerText : '0';", tile).strip()
                    
                    # Save both to the row dictionary
                    row_data[f"{stat_name} Rank"] = rank
                    row_data[f"{stat_name} Count"] = count
                
                final_rankings.append(row_data)
                
            except Exception as e:
                print(f"[{i}/{total_tiles}] Error extracting data for tile, skipping...")
                pass

        # --- 7. SAVE TO WIDE-FORMAT CSV ---
        csv_filename = f"squadrats_rankings_{datestamp}.csv"
        print(f"\nSaving data to {csv_filename}...")
        
        # Build the 13 column headers
        categories = ['Squadrats', 'Squadratinhos', 'Übersquadrat', 'Übersquadratinho', 'Yard', 'Yardinho']
        fieldnames = ['Region']
        for cat in categories:
            fieldnames.append(f"{cat} Rank")
            fieldnames.append(f"{cat} Count")
        
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in final_rankings:
                writer.writerow(row)
                
        # --- 8. DOWNLOAD THE KML ---
        print("\nNavigating to map page to download KML...")
        driver.get(map_url)
        
        kml_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(., 'Download KML')]")))
        kml_btn.click()
        
        print("Waiting for KML download to finish...")
        downloaded_file = None
        
        for _ in range(30):
            files = glob.glob(os.path.join(current_folder, "*.kml"))
            if files:
                downloaded_file = max(files, key=os.path.getctime)
                break
            time.sleep(1)
            
        if downloaded_file:
            time.sleep(1) 
            new_kml_name = f"squadrats_earth_{datestamp}.kml"
            new_kml_path = os.path.join(current_folder, new_kml_name)
            
            if os.path.exists(new_kml_path):
                os.remove(new_kml_path)
                
            os.rename(downloaded_file, new_kml_path)
            print(f"Success! KML saved as: {new_kml_name}")
        else:
            print("Error: KML download timed out or failed.")

        print("\nAll tasks completed successfully!")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_rankings()
