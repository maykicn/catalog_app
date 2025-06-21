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
    extract_start_date,
    get_stored_validity_strings, # <<< ADD THIS NEW IMPORT
    PDF_DOWNLOAD_DIR,
    LOCAL_IMAGE_DIR
)

# --- SETUP LOGGING IMMEDIATELY ---
setup_logging()

# =========================================================================================
# MAIN CONTROLLER
# =========================================================================================
def main():
    """Main execution function with logic to check for updates before processing."""
    logging.info("--- STARTING CATALOG AUTOMATION SCRIPT ---")

    # This initial cleanup can still happen if you want a clean slate for downloads
    if not cleanup_directory(PDF_DOWNLOAD_DIR) or not cleanup_directory(LOCAL_IMAGE_DIR):
        logging.critical("Could not create/clean temporary directories. Exiting script.")
        return
    logging.info("Temporary directories created/cleaned successfully.")

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

            # --- NEW UPDATE CHECKING LOGIC ---
            
            # 1. Scrape live data from the website to see what's currently available
            live_catalogs = scraper_function(market_name, lang_code, direct_url)
            if not live_catalogs:
                logging.error(f"No catalogs found on the website for {market_name.upper()} ({lang_code}). Skipping.")
                continue
            
            live_validity_strings = sorted([cat[1] for cat in live_catalogs])

            # 2. Fetch currently stored data from Firestore
            stored_validity_strings = sorted(get_stored_validity_strings(market_name, lang_code))
            
            # 3. Compare the live data with the stored data
            if live_validity_strings == stored_validity_strings:
                logging.info(f"Catalogs for {market_name.upper()} ({lang_code}) are already up-to-date. No action needed.")
                continue # Skip to the next language/market
            
            # --- IF WE REACH HERE, AN UPDATE IS REQUIRED ---
            logging.info(f"New catalogs found for {market_name.upper()} ({lang_code}). Starting update process...")

            # The rest of the logic is the same as before, but now it only runs when needed.
            dated_catalogs = []
            for pdf_url, validity_string in live_catalogs: # Use live_catalogs we already scraped
                start_date = extract_start_date(validity_string)
                if start_date:
                    dated_catalogs.append({
                        'url': pdf_url, 'validity': validity_string, 'start_date': start_date
                    })
            
            sorted_catalogs = sorted(dated_catalogs, key=lambda x: x['start_date'])

            current_week_catalog = None
            next_week_catalog = None

            for cat in reversed(sorted_catalogs):
                if cat['start_date'] <= today:
                    current_week_catalog = cat
                    break

            for cat in sorted_catalogs:
                if cat['start_date'] > today:
                    next_week_catalog = cat
                    break
            
            catalogs_to_process = []
            if current_week_catalog:
                current_week_catalog['week_type'] = 'current'
                catalogs_to_process.append(current_week_catalog)
            if next_week_catalog and (not current_week_catalog or next_week_catalog['url'] != current_week_catalog['url']):
                next_week_catalog['week_type'] = 'next'
                catalogs_to_process.append(next_week_catalog)

            if not catalogs_to_process:
                logging.warning(f"Update required, but could not identify a clear current/next week catalog.")
                continue

            clear_old_catalogs(market_name, lang_code)
            
            for i, catalog_data in enumerate(catalogs_to_process):
                pdf_url = catalog_data['url']
                validity_string = catalog_data['validity']
                week_type = catalog_data['week_type']
                
                catalog_id = f"{week_type}_catalog_{i+1}"
                logging.info(f"Processing {week_type.upper()} catalog. Validity: {validity_string}")

                downloaded_pdf_path = download_pdf(pdf_url, market_name, lang_code, i)
                if not downloaded_pdf_path: continue
                
                image_output_dir = os.path.join(LOCAL_IMAGE_DIR, market_name, lang_code, catalog_id)
                os.makedirs(image_output_dir, exist_ok=True)
                local_image_paths = convert_pdf_to_images(downloaded_pdf_path, image_output_dir)
                if not local_image_paths: continue

                storage_urls = upload_images_to_storage(local_image_paths, market_name, lang_code, catalog_id)
                if not storage_urls: continue

                thumbnail_url = storage_urls[0] if storage_urls else ''
                base_title = config["titles"].get(lang_code, "Weekly Catalog")
                catalog_title = f"{market_name.capitalize()} {base_title}"

                add_catalog_to_firestore(market_name, catalog_title, validity_string, thumbnail_url, storage_urls, lang_code, week_type)
                logging.info(f"--- Successfully processed {week_type.upper()} catalog for {market_name.upper()} ({lang_code}). ---")

    logging.info("--- ALL CATALOG AUTOMATION FINISHED ---")
    # You may choose to leave the final cleanup or remove it depending on your needs
    # cleanup_directory(PDF_DOWNLOAD_DIR)
    # cleanup_directory(LOCAL_IMAGE_DIR)
    # logging.info("All temporary directories have been cleaned up.")

if __name__ == "__main__":
    main()