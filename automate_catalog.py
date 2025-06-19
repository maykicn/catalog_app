# -*- coding: utf-8 -*-

import os
import shutil
import datetime
import time
import logging
import re

# =========================================================================================
# !!! 1. PROFESSIONAL LOGGING SETUP (AT THE TOP) !!!
# The logging module is configured here, at the very beginning of the script,
# to ensure our custom formatting is applied BEFORE any other imported library
# can set up its own basic logging.
# =========================================================================================
def setup_logging():
    """Configures logging for the script to provide detailed, professional output."""
    log_formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - [%(funcName)s:%(lineno)d] - %(message)s'
    )
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    
    # File handler to save logs to 'catalog_automation.log'
    file_handler = logging.FileHandler('catalog_automation.log', mode='w', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler to display logs in the terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

# --- SETUP LOGGING IMMEDIATELY ---
setup_logging()

# --- NOW, IMPORT ALL OTHER LIBRARIES ---
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
import fitz  # PyMuPDF
from PIL import Image
import firebase_admin
from firebase_admin import credentials, firestore, storage

# =========================================================================================
# !!! 2. GLOBAL CONFIGURATION (COMMON FOR THE ENTIRE SCRIPT) !!!
# =========================================================================================

# --- Firebase Configuration ---
SERVICE_ACCOUNT_KEY_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\serviceAccountKey.json'
FIREBASE_STORAGE_BUCKET = 'catalogapp-7b5bc.firebasestorage.app'

# --- Selenium WebDriver Path ---
CHROME_DRIVER_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\chromedriver.exe'

# --- Temporary Directory Paths ---
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
PDF_DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, 'temp_pdfs')
LOCAL_IMAGE_DIR = os.path.join(PROJECT_ROOT, 'temp_images')

# =========================================================================================
# !!! 3. INITIALIZATION & HELPER FUNCTIONS (COMMON) !!!
# =========================================================================================

# --- Initialize Firebase Admin SDK ---
try:
    logging.info("Initializing Firebase Admin SDK...")
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {'storageBucket': FIREBASE_STORAGE_BUCKET})
    db = firestore.client()
    bucket = storage.bucket()
    logging.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    logging.critical(f"Firebase Admin SDK initialization error: {e}")
    exit()

def setup_driver():
    """Configures and returns a Selenium WebDriver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    prefs = {
        "download.default_directory": PDF_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def cleanup_directory(dir_path):
    """Removes and recreates a directory."""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            logging.error(f"Error removing directory {dir_path}: {e}.")
            return False
    os.makedirs(dir_path, exist_ok=True)
    return True

# =========================================================================================
# !!! 4. MARKET-SPECIFIC SCRAPER FUNCTIONS !!!
# Each market's unique logic is contained here.
# =========================================================================================

def scrape_lidl_ch(market_name, lang_code, market_url):
    """
    (RELIABLE LOGIC FROM FILE 1)
    Scrapes the PDF link and validity date for Lidl.
    Returns a list containing a single tuple: [(pdf_url, validity_string)]
    """
    logging.info(f"Starting Lidl scraper for language: {lang_code}")
    driver = setup_driver()
    try:
        logging.info(f"Navigating to {market_name.upper()} at {market_url}...")
        driver.get(market_url)

        # --- Handle Cookie Consent ---
        try:
            accept_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-accept-btn-handler")))
            accept_button.click()
            logging.info("Accepted Lidl cookie preferences.")
            WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "#onetrust-accept-btn-handler")))
        except:
            logging.info("Lidl cookie banner not found or timed out.")

        # 1. Find the flyer and extract info
        logging.info("Waiting for main page flyers to load...")
        latest_flyer_element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.flyer')))
        
        # --- Scrape Validity Date ---
        validity_text = "Valid this week"
        try:
            flyer_full_text = latest_flyer_element.text
            match = re.search(r'(\d{1,2}\.\d{1,2}\.?\s*[–-]\s*\d{1,2}\.\d{1,2}\.?)', flyer_full_text)
            if match:
                validity_text = match.group(0).replace("–", "-").strip()
                logging.info(f"Successfully scraped validity date: '{validity_text}'")
            else:
                logging.warning("Could not find a date pattern in the flyer text.")
        except:
            logging.warning("An error occurred during date scraping.")

        flyer_preview_url = latest_flyer_element.get_attribute('href')
        logging.info(f"Found latest flyer preview URL: {flyer_preview_url}")

        try:
            latest_flyer_element.click()
        except ElementClickInterceptedException:
            logging.warning("Click on flyer element was intercepted. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", latest_flyer_element)

        # 2. Wait for preview page to load menu button
        logging.info("Waiting for preview page and menu button to appear...")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal, a[href*=".pdf"]')))

        # 3. Click menu and find download link
        try:
            menu_button_icon = driver.find_element(By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal')
            menu_button = menu_button_icon.find_element(By.XPATH, './ancestor::button')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(menu_button)).click()
            logging.info("Clicked on menu button.")
            
            pdf_download_link_xpath = "//a[contains(@class, 'button--primary') and (contains(., 'PDF') or contains(., 'herunterladen') or contains(., 'prospectus') or contains(., 'volantino'))]"
            pdf_download_link = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, pdf_download_link_xpath)))
            pdf_url = pdf_download_link.get_attribute('href')
            logging.info(f"Found PDF download URL in menu: {pdf_url}")
            # Return in list format to be consistent with other scrapers
            return [(pdf_url, validity_text)]
        except Exception as e:
            logging.error(f"Could not find PDF download link via menu. Error: {e}")
            return []
    except Exception as e:
        logging.exception(f"An unexpected error occurred during the Selenium process for Lidl: {e}")
        return []
    finally:
        if driver:
            logging.info("Quitting WebDriver.")
            driver.quit()

def scrape_aldi_ch(market_name, lang_code, market_url):
    """
    (RELIABLE LOGIC FROM FILE 2)
    Scrapes all available weekly catalogs for Aldi Suisse.
    Returns a list of tuples: [(pdf_url, validity_string), ...]
    """
    logging.info(f"Starting Aldi scraper for language: {lang_code}")
    driver = setup_driver()
    found_catalogs = []
    try:
        driver.get(market_url)
        logging.info(f"Navigated to Aldi brochures page: {market_url}")
        
        # --- Handle Cookies and Pop-ups ---
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            logging.info("Accepted Aldi main cookie preferences.")
        except:
            logging.info("Aldi main cookie banner not found.")
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close-modal"))).click()
            logging.info("Closed promotion pop-up.")
        except:
            logging.info("Promotion pop-up not found.")

        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.wrapper")))
        all_catalog_elements = driver.find_elements(By.CSS_SELECTOR, "article.wrapper")
        logging.info(f"Found {len(all_catalog_elements)} potential Aldi flyers.")
        
        validity_keywords = ["gültig", "valables", "valide"]

        for element in all_catalog_elements:
            try:
                validity_text_element = element.find_element(By.CSS_SELECTOR, ".card_leaflet__content p")
                validity_text_content = validity_text_element.text.lower()
                
                if any(keyword in validity_text_content for keyword in validity_keywords):
                    pdf_url = element.find_element(By.CSS_SELECTOR, "a[href*='s7g10']").get_attribute("href")
                    found_catalogs.append((pdf_url, validity_text_element.text))
                    logging.info(f"Found valid Aldi catalog. Validity: '{validity_text_element.text}'")
            except NoSuchElementException:
                continue
        
        logging.info(f"Scraping finished. Found a total of {len(found_catalogs)} valid catalogs for Aldi.")
        return found_catalogs
    except Exception as e:
        logging.error(f"An error occurred during Aldi scrape for {lang_code}: {e}")
        return []
    finally:
        if driver:
            driver.quit()

# =========================================================================================
# !!! 5. DATA PROCESSING FUNCTIONS (COMMON) !!!
# PDF download, image conversion, and Firebase upload operations.
# =========================================================================================

def download_pdf(pdf_url, market_name, lang_code, catalog_index):
    """Downloads a PDF from the given URL."""
    if not pdf_url: return None
    filename = f"{market_name}_{lang_code}_catalog_{catalog_index}_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(PDF_DOWNLOAD_DIR, filename)
    logging.info(f"Downloading PDF from: {pdf_url}")
    try:
        response = requests.get(pdf_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        logging.info(f"PDF downloaded successfully to: {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        logging.exception(f"Error downloading PDF from {pdf_url}. Error: {e}")
        return None

def convert_pdf_to_images(pdf_path, output_image_dir, dpi=200):
    """Converts a PDF file into a series of PNG images."""
    if not pdf_path or not os.path.exists(pdf_path): return []
    logging.info(f"Converting PDF {os.path.basename(pdf_path)} to images...")
    local_image_paths = []
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_filename = f"page_{page_num + 1:02d}.png"
            image_path = os.path.join(output_image_dir, image_filename)
            img.save(image_path)
            local_image_paths.append(image_path)
        logging.info(f"PDF conversion complete. {len(local_image_paths)} images generated.")
        return local_image_paths
    except Exception as e:
        logging.exception(f"Error converting PDF to images: {e}")
        return []

def upload_images_to_storage(local_image_paths, market_name, lang_code, catalog_id):
    """Uploads local images to Firebase Storage and returns their public URLs."""
    if not local_image_paths: return []
    logging.info(f"Uploading {len(local_image_paths)} images to Firebase Storage...")
    public_urls = []
    for local_path in local_image_paths:
        try:
            file_name = os.path.basename(local_path)
            destination_blob_name = f"catalogs/{market_name}/{lang_code}/{catalog_id}/{file_name}"
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_path)
            blob.make_public()
            public_urls.append(blob.public_url)
        except Exception as e:
            logging.exception(f"Failed to upload {file_name}. Error: {e}")
    logging.info(f"Upload complete. {len(public_urls)} images are now public.")
    return public_urls

def clear_old_catalogs(market_name, language):
    """Clears old Firestore entries for a specific market and language."""
    logging.info(f"Clearing old Firestore entries for {market_name.upper()} ({language})...")
    brochures_ref = db.collection('brochures')
    try:
        query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language)
        docs = query.stream()
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        logging.info(f"{deleted_count} old entries cleared successfully.")
    except Exception as e:
        logging.exception(f"Error clearing old Firestore entries: {e}")

def add_catalog_to_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, page_urls, language):
    """Adds a new catalog to Firestore."""
    if not page_urls:
        logging.warning("No page URLs to upload, skipping Firestore update.")
        return
    logging.info(f"Adding new catalog to Firestore: '{catalog_title}'")
    brochures_ref = db.collection('brochures')
    try:
        new_catalog_data = {
            'marketName': market_name,
            'title': catalog_title,
            'validity': catalog_validity,
            'thumbnail': thumbnail_url,
            'pages': page_urls,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'language': language
        }
        doc_ref = brochures_ref.add(new_catalog_data)
        logging.info(f"New catalog added to Firestore with ID: {doc_ref[1].id}")
    except Exception as e:
        logging.exception(f"Error adding document to Firestore: {e}")


# =========================================================================================
# !!! 6. MAIN CONTROLLER !!!
# The main function that orchestrates the entire process.
# =========================================================================================
def main():
    """Main execution function."""
    logging.info("--- STARTING CATALOG AUTOMATION SCRIPT ---")

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
            
            # For Aldi, there might be multiple catalogs; let's take up to 2
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
                # If there's more than one catalog, add validity to the title to differentiate
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