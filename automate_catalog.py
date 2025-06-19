# catalog_automation.py

import logging
import os

# Import scraper functions from their respective modules
from scrapers.scraper_lidl import scrape_lidl_ch
from scrapers.scraper_aldi import scrape_aldi_ch

# Import all necessary helper functions and constants from utils
from scrapers.utils import (
    setup_logging,
    cleanup_directory,
    clear_old_catalogs,
    add_catalog_to_firestore,
    download_pdf,
    convert_pdf_to_images,
    upload_images_to_storage,
    PDF_DOWNLOAD_DIR,
    LOCAL_IMAGE_DIR
)

# --- SETUP LOGGING IMMEDIATELY ---
setup_logging()

# =========================================================================================
# MAIN CONTROLLER
# =========================================================================================
def main():
    """Main execution function."""
    logging.info("--- STARTING CATALOG AUTOMATION SCRIPT ---")

    if not cleanup_directory(PDF_DOWNLOAD_DIR) or not cleanup_directory(LOCAL_IMAGE_DIR):
        logging.critical("Could not create/clean temporary directories. Exiting script.")
        return
    logging.info("Temporary directories created/cleaned successfully.")

    markets = {
        
        "aldi": {
            "scraper": scrape_aldi_ch,
            "languages": {
                "de": "https://www.aldi-suisse.ch/de/aktionen-und-angebote/aktuelle-flugblaetter-und-broschuren.html",
                "fr": "https://www.aldi-suisse.ch/fr/actions/brochures-semaine.html",
                "it": "https://www.aldi-suisse.ch/it/promozioni/settimana-e-brochure.html"
            },
            "titles": {
                "de": "Aktionen der Woche", "fr": "Actions de la semaine", "it": "Azioni della settimana"
            }
        }
    }
    
    for market_name, config in markets.items():
        logging.info(f"===== PROCESSING MARKET: {market_name.upper()} =====")
        scraper_function = config["scraper"]
        
        for lang_code, direct_url in config["languages"].items():
            logging.info(f"--- Processing Language: {lang_code.upper()} ---")
            
            # 1. Scrape Data
            all_found_catalogs = scraper_function(market_name, lang_code, direct_url)
            if not all_found_catalogs:
                logging.error(f"No valid catalogs found for {market_name.upper()} ({lang_code}). Skipping.")
                continue

            # 2. Clear Old Catalogs
            clear_old_catalogs(market_name, lang_code)
            
            # Take up to the 2 most recent catalogs
            catalogs_to_process = sorted(all_found_catalogs, key=lambda x: x[1], reverse=True)[:2]

            # 3. Loop Through Each Found Catalog
            for i, (pdf_url, validity_string) in enumerate(catalogs_to_process):
                catalog_id = f"catalog_{i+1}"
                logging.info(f"Processing catalog {i+1}/{len(catalogs_to_process)}. Validity: {validity_string}")

                # 4. Download PDF
                downloaded_pdf_path = download_pdf(pdf_url, market_name, lang_code, i)
                if not downloaded_pdf_path: continue
                
                # 5. Convert PDF to Images
                image_output_dir = os.path.join(LOCAL_IMAGE_DIR, market_name, lang_code, catalog_id)
                os.makedirs(image_output_dir, exist_ok=True)
                local_image_paths = convert_pdf_to_images(downloaded_pdf_path, image_output_dir)
                if not local_image_paths: continue

                # 6. Upload Images to Storage
                storage_urls = upload_images_to_storage(local_image_paths, market_name, lang_code, catalog_id)
                if not storage_urls: continue
                
                # 7. Add to Firestore
                thumbnail_url = storage_urls[0] if storage_urls else ''
                base_title = config["titles"].get(lang_code, "Weekly Catalog")
                catalog_title = f"{market_name.capitalize()} {base_title}"
                if len(catalogs_to_process) > 1:
                      catalog_title += f" ({validity_string})"

                add_catalog_to_firestore(market_name, catalog_title, validity_string, thumbnail_url, storage_urls, lang_code)
                logging.info(f"--- Successfully processed {market_name.upper()} ({lang_code}) - Catalog {i+1}. ---")
            
    logging.info("--- ALL CATALOG AUTOMATION FINISHED ---")
    cleanup_directory(PDF_DOWNLOAD_DIR)
    cleanup_directory(LOCAL_IMAGE_DIR)
    logging.info("All temporary directories have been cleaned up.")

if __name__ == "__main__":
    main()