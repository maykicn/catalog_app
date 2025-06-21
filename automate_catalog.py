# catalog_automation.py

import logging
import os
import datetime

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
    extract_start_date, # ADD THIS
    PDF_DOWNLOAD_DIR,
    LOCAL_IMAGE_DIR
)

# --- SETUP LOGGING IMMEDIATELY ---
setup_logging()

# =========================================================================================
# MAIN CONTROLLER
# =========================================================================================
def main():
    """Main execution function with logic to identify current/next week catalogs."""
    logging.info("--- STARTING CATALOG AUTOMATION SCRIPT ---")

    if not cleanup_directory(PDF_DOWNLOAD_DIR) or not cleanup_directory(LOCAL_IMAGE_DIR):
        logging.critical("Could not create/clean temporary directories. Exiting script.")
        return
    logging.info("Temporary directories created/cleaned successfully.")

    # Market configuration remains the same
    markets = {
        "lidl": {
            "scraper": scrape_lidl_ch,
            "languages": {
                "de": "https://www.lidl.ch/c/de-CH/werbeprospekte-als-pdf/s10019683",
                "fr": "https://www.lidl.ch/c/fr-CH/prospectus-pdf/s10019683",
                "it": "https://www.lidl.ch/c/it-CH/volantini-in-pdf/s10019683"
            },
            "titles": {
                "de": "Wöchentlicher Katalog", "fr": "Catalogue de la semaine", "it": "Catalogo della settimana"
            }
        },
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

    today = datetime.date.today()

    for market_name, config in markets.items():
        logging.info(f"===== PROCESSING MARKET: {market_name.upper()} =====")
        scraper_function = config["scraper"]

        for lang_code, direct_url in config["languages"].items():
            logging.info(f"--- Processing Language: {lang_code.upper()} ---")

            all_found_catalogs = scraper_function(market_name, lang_code, direct_url)
            if not all_found_catalogs:
                logging.error(f"No valid catalogs found for {market_name.upper()} ({lang_code}). Skipping.")
                continue

            # --- NEW LOGIC TO IDENTIFY AND LABEL CATALOGS ---
            # 1. Parse dates from all found catalogs
            dated_catalogs = []
            for pdf_url, validity_string in all_found_catalogs:
                start_date = extract_start_date(validity_string)
                if start_date:
                    dated_catalogs.append({
                        'url': pdf_url,
                        'validity': validity_string,
                        'start_date': start_date
                    })
            
            # Sort catalogs by date, oldest first
            sorted_catalogs = sorted(dated_catalogs, key=lambda x: x['start_date'])

            # 2. Find the single most relevant "current" and "next" week catalogs
            current_week_catalog = None
            next_week_catalog = None

            # Find the most recent catalog that has already started (Current)
            for cat in reversed(sorted_catalogs):
                if cat['start_date'] <= today:
                    current_week_catalog = cat
                    break

            # Find the first catalog that starts in the future (Next)
            for cat in sorted_catalogs:
                if cat['start_date'] > today:
                    next_week_catalog = cat
                    break
            
            # 3. Prepare the final list for processing, ensuring no duplicates
            catalogs_to_process = []
            if current_week_catalog:
                current_week_catalog['week_type'] = 'current'
                catalogs_to_process.append(current_week_catalog)
            
            # Ensure the "next" catalog is not the same as the "current" one
            if next_week_catalog and (not current_week_catalog or next_week_catalog['url'] != current_week_catalog['url']):
                next_week_catalog['week_type'] = 'next'
                catalogs_to_process.append(next_week_catalog)
            # --- END OF NEW LOGIC ---

            if not catalogs_to_process:
                logging.warning(f"Could not identify a clear current/next week catalog for {market_name.upper()} ({lang_code}).")
                continue

            # 4. Clear old Firestore data and process the identified catalogs
            clear_old_catalogs(market_name, lang_code)
            
            for i, catalog_data in enumerate(catalogs_to_process):
                # Extract data from the processed dictionary
                pdf_url = catalog_data['url']
                validity_string = catalog_data['validity']
                week_type = catalog_data['week_type']
                
                catalog_id = f"{week_type}_catalog_{i+1}"
                logging.info(f"Processing {week_type.upper()} catalog. Validity: {validity_string}")

                # Download, convert, and upload steps remain the same
                downloaded_pdf_path = download_pdf(pdf_url, market_name, lang_code, i)
                if not downloaded_pdf_path: continue
                
                image_output_dir = os.path.join(LOCAL_IMAGE_DIR, market_name, lang_code, catalog_id)
                os.makedirs(image_output_dir, exist_ok=True)
                local_image_paths = convert_pdf_to_images(downloaded_pdf_path, image_output_dir)
                if not local_image_paths: continue

                storage_urls = upload_images_to_storage(local_image_paths, market_name, lang_code, catalog_id)
                if not storage_urls: continue

                # Create the catalog title without extra suffixes
                thumbnail_url = storage_urls[0] if storage_urls else ''
                base_title = config["titles"].get(lang_code, "Weekly Catalog")
                catalog_title = f"{market_name.capitalize()} {base_title}" # Suffix removed

                # Add to Firestore with the new week_type field
                add_catalog_to_firestore(market_name, catalog_title, validity_string, thumbnail_url, storage_urls, lang_code, week_type)
                logging.info(f"--- Successfully processed {week_type.upper()} catalog for {market_name.upper()} ({lang_code}). ---")

    logging.info("--- ALL CATALOG AUTOMATION FINISHED ---")
    cleanup_directory(PDF_DOWNLOAD_DIR)
    cleanup_directory(LOCAL_IMAGE_DIR)
    logging.info("All temporary directories have been cleaned up.")

if __name__ == "__main__":
    main()