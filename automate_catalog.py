import os
import shutil
import datetime
import time
import logging
import re

# =========================================================================================
# !!! PROFESSIONAL LOGGING SETUP - MOVED TO TOP !!!
# =========================================================================================
def setup_logging():
    """Configures the logging for the script to provide detailed, professional output."""
    log_formatter = logging.Formatter(
        '%(asctime)s - [%(funcName)s:%(lineno)d] - %(levelname)s - %(message)s'
    )
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO) 
    file_handler = logging.FileHandler('catalog_automation.log', mode='w')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

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


# --- Firebase Configuration ---
SERVICE_ACCOUNT_KEY_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\serviceAccountKey.json'
FIREBASE_STORAGE_BUCKET = 'catalogapp-7b5bc.firebasestorage.app'

# --- Initialize Firebase Admin SDK ---
try:
    logging.info("Initializing Firebase Admin SDK...")
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_STORAGE_BUCKET
        })
    db = firestore.client()
    bucket = storage.bucket()
    logging.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    logging.critical(f"Firebase Admin SDK initialization error: {e}")
    exit()

# --- Path Configurations ---
FLUTTER_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
PDF_DOWNLOAD_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_pdfs')
LOCAL_IMAGE_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_images')

# --- Selenium Setup ---
CHROME_DRIVER_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\chromedriver.exe'

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

# =========================================================================================
# --- SCRAPER FOR LIDL (RELIABLE VERSION) ---
# =========================================================================================
def scrape_lidl_ch(market_name, lang_code, market_url):
    logging.info(f"Starting Lidl scraper for language: {lang_code}")
    driver = setup_driver()
    processed_catalogs = []
    try:
        driver.get(market_url)
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            logging.info("Accepted Lidl cookie banner.")
        except:
            logging.info("Lidl cookie banner not found or already accepted.")

        flyer_elements = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.flyer')))
        logging.info(f"Found {len(flyer_elements)} potential Lidl flyers.")
        
        flyer_links = [flyer.get_attribute('href') for flyer in flyer_elements if "wochen" in flyer.get_attribute('href') or "semaine" in flyer.get_attribute('href') or "settimana" in flyer.get_attribute('href')]

        for pdf_page_url in flyer_links:
            try:
                logging.info(f"Navigating to Lidl flyer page: {pdf_page_url}")
                driver.get(pdf_page_url)
                
                validity_text = "Validity not found"
                try:
                    validity_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.publication-date")))
                    validity_text = validity_element.text
                except:
                    logging.warning("Could not find validity date on detail page.")

                pdf_url = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*=".pdf"]'))).get_attribute('href')
                logging.info(f"Found Lidl PDF URL: {pdf_url}")
                processed_catalogs.append((pdf_url, validity_text))
            except Exception as e:
                logging.error(f"Failed to process a Lidl flyer page. Error: {e}")
                continue
        
        logging.info(f"Successfully scraped {len(processed_catalogs)} catalog(s) for Lidl ({lang_code}).")
        return processed_catalogs
        
    except Exception as e:
        logging.error(f"An error occurred during Lidl scrape for {lang_code}: {e}")
        return []
    finally:
        if driver:
            driver.quit()


# =========================================================================================
# --- SCRAPER FOR ALDI (RELIABLE VERSION) ---
# =========================================================================================
def scrape_aldi_ch(market_name, lang_code, direct_url):
    """(CORRECTED) Scrapes all available weekly catalogs for Aldi Suisse."""
    logging.info(f"Starting Aldi scraper for language: {lang_code}")
    driver = setup_driver()
    found_catalogs = []
    try:
        driver.get(direct_url)
        logging.info(f"Navigated directly to Aldi brochures page: {direct_url}")
        
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            logging.info("Accepted main cookie preferences for Aldi.")
        except:
            logging.info("Aldi main cookie banner not found or already accepted.")
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close-modal"))).click()
            logging.info("Closed the WhatsApp promotion pop-up.")
        except:
            logging.info("WhatsApp pop-up not found, proceeding...")

        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.wrapper")))
        all_catalog_elements = driver.find_elements(By.CSS_SELECTOR, "article.wrapper")
        
        validity_keywords = ["gültig", "valables", "valide"]

        for element in all_catalog_elements:
            try:
                validity_text_element = element.find_element(By.CSS_SELECTOR, ".card_leaflet__content p")
                validity_text = validity_text_element.text.lower()
                
                # RELIABLE FILTER: Check if the validity text contains a keyword like "gültig" or "valables"
                if any(keyword in validity_text for keyword in validity_keywords):
                    pdf_url = element.find_element(By.CSS_SELECTOR, "a[href*='s7g10']").get_attribute("href")
                    found_catalogs.append((pdf_url, validity_text_element.text))
                    logging.info(f"Found valid Aldi weekly catalog. Validity: '{validity_text_element.text}'")
            except NoSuchElementException:
                continue
        
        logging.info(f"Scraping finished. Found a total of {len(found_catalogs)} valid weekly catalogs for Aldi.")
        return found_catalogs
    except Exception as e:
        logging.error(f"An error occurred during Aldi scrape for {lang_code}: {e}")
        return []
    finally:
        if driver:
            driver.quit()

# --- Generic Helper Functions ---
def download_pdf(pdf_url, market_name, lang_code, catalog_index):
    if not pdf_url: return None
    filename = f"{market_name}_{lang_code}_catalog_{catalog_index}.pdf"
    filepath = os.path.join(PDF_DOWNLOAD_DIR, filename)
    logging.info(f"Downloading PDF from: {pdf_url}...")
    try:
        response = requests.get(pdf_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(filepath, 'wb') as f: f.write(response.content)
        logging.info(f"PDF downloaded to: {filepath}")
        return filepath
    except:
        logging.exception(f"Error downloading PDF from {pdf_url}")
        return None

def convert_pdf_to_images(pdf_path, output_image_dir):
    if not pdf_path or not os.path.exists(pdf_path): return []
    local_image_paths = []
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_filename = f"page_{page_num + 1:02d}.png"
            image_path = os.path.join(output_image_dir, image_filename)
            img.save(image_path)
            local_image_paths.append(image_path)
        logging.info(f"PDF converted. Total {len(local_image_paths)} images generated.")
        return local_image_paths
    except Exception:
        logging.exception(f"Error converting PDF to images: {pdf_path}")
        return []

def upload_images_to_storage(local_image_paths, market_name, lang_code, catalog_id):
    if not local_image_paths: return []
    public_urls = []
    for local_path in local_image_paths:
        try:
            file_name = os.path.basename(local_path)
            destination_blob_name = f"catalogs/{market_name}/{lang_code}/{catalog_id}/{file_name}"
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_path)
            blob.make_public()
            public_urls.append(blob.public_url)
        except Exception:
            logging.exception(f"Failed to upload {os.path.basename(local_path)} to Firebase Storage.")
    logging.info(f"Finished uploading {len(public_urls)} images.")
    return public_urls

def add_catalog_to_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, page_urls, language):
    if not page_urls: return
    brochures_ref = db.collection('brochures')
    try:
        new_catalog_data = {
            'marketName': market_name, 'title': catalog_title, 'validity': catalog_validity,
            'thumbnail': thumbnail_url, 'pages': page_urls, 'timestamp': firestore.SERVER_TIMESTAMP,
            'language': language
        }
        doc_ref = brochures_ref.add(new_catalog_data)
        logging.info(f"New catalog added to Firestore with ID: {doc_ref[1].id}")
    except Exception:
        logging.exception(f"Error adding document to Firestore.")

def clear_old_catalogs(market_name, language):
    logging.info(f"Clearing old Firestore entries for {market_name} ({language})...")
    brochures_ref = db.collection('brochures')
    try:
        query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language)
        docs = query.stream()
        for doc in docs:
            logging.info(f"  - Deleting old catalog: {doc.id}")
            doc.reference.delete()
        logging.info("Old entries cleared successfully.")
    except Exception:
        logging.exception("Error clearing old Firestore entries.")

def cleanup_directory(dir_path):
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            logging.error(f"Error removing directory {dir_path}: {e}")
            return False
    os.makedirs(dir_path, exist_ok=True)
    return True

# --- MAIN CONTROLLER ---
def main():
    logging.info("--- Starting Catalog Automation Script ---")
    if not cleanup_directory(PDF_DOWNLOAD_DIR) or not cleanup_directory(LOCAL_IMAGE_DIR):
        return
    logging.info(f"Created temporary directories.")

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
            "titles": {"de": "Aktionen", "fr": "Actions", "it": "Azioni"}
        }
    }
    
    for market_name, config in markets.items():
        logging.info(f"===== Processing Market: {market_name.upper()} =====")
        scraper_function = config["scraper"]
        
        for lang_code, direct_url in config["languages"].items():
            logging.info(f"--- Processing Language: {lang_code.upper()} ---")
            
            all_found_catalogs = scraper_function(market_name, lang_code, direct_url)
            if not all_found_catalogs:
                logging.error(f"No valid catalogs found for {market_name} ({lang_code}). Skipping.")
                continue

            clear_old_catalogs(market_name, lang_code)
            
            # Take up to the 2 most recent catalogs
            catalogs_to_process = sorted(all_found_catalogs, key=lambda x: x[0], reverse=True)[:2]

            for i, (pdf_url, validity_string) in enumerate(catalogs_to_process):
                catalog_id = f"catalog_{market_name}_{lang_code}_{i}"
                logging.info(f"Processing catalog {i+1}/{len(catalogs_to_process)} with validity: {validity_string}")

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
                if len(all_found_catalogs) > 1:
                     catalog_title += f" ({validity_string})"

                add_catalog_to_firestore(market_name, catalog_title, validity_string, thumbnail_url, storage_urls, lang_code)
                logging.info(f"--- Successfully processed catalog {i+1}. ---")
        
    logging.info("--- All Catalog Automation Finished ---")
    cleanup_directory(PDF_DOWNLOAD_DIR)
    cleanup_directory(LOCAL_IMAGE_DIR)
    logging.info("Cleaned up all temporary directories.")

if __name__ == "__main__":
    main()
