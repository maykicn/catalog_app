import os
import shutil
import datetime
import time
import logging

# =========================================================================================
# !!! PROFESSIONAL LOGGING SETUP - MOVED TO TOP !!!
# The logging module is configured here, at the very beginning of the script.
# This ensures our custom formatting is applied BEFORE any other imported library
# can set up its own basic logging, which would prevent our format from working.
# =========================================================================================
def setup_logging():
    """Configures the logging for the script to provide detailed, professional output."""
    # This professional format includes the function name and line number for precise debugging.
    log_formatter = logging.Formatter(
        '%(asctime)s - [%(funcName)s:%(lineno)d] - %(levelname)s - %(message)s'
    )
    
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to prevent duplicate log messages
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    # Set the logging level (INFO is a good default, DEBUG is more verbose)
    root_logger.setLevel(logging.INFO) 
    
    # Create and add a file handler to save logs to 'catalog_automation.log'
    file_handler = logging.FileHandler('catalog_automation.log', mode='w') # 'w' overwrites the log each run
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    
    # Create and add a console handler to display logs in the terminal
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
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    # Suppress most of the verbose console output from ChromeDriver/Selenium itself
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

def get_latest_pdf_link_selenium(market_name, market_url):
    """(USER'S PROVEN LOGIC RESTORED) Uses Selenium to find the URL for the latest PDF catalog."""
    driver = setup_driver()
    pdf_url = None
    try:
        logging.info(f"Navigating to {market_name.upper()} at {market_url}...")
        driver.get(market_url)

        # --- Handle Cookie Consent ---
        try:
            accept_cookies_selectors = [
                "#onetrust-accept-btn-handler",
                "button.uc-btn[data-accept-action='all']",
                "button[id^='onetrust-accept-btn']",
            ]
            accepted = False
            for selector in accept_cookies_selectors:
                try:
                    accept_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    accept_button.click()
                    logging.info(f"Accepted cookie preferences using selector: {selector}.")
                    WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
                    accepted = True
                    break
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                    continue
            if not accepted:
                logging.warning("No cookie consent pop-up found or handled. Proceeding...")
        except Exception:
            logging.exception("An error occurred while handling cookie consent. Proceeding...")

        # 1. Click the main page flyer
        logging.info("Waiting for main page flyers to load...")
        latest_flyer_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.flyer'))
        )
        flyer_preview_url = latest_flyer_element.get_attribute('href')
        logging.info(f"Found latest flyer preview URL: {flyer_preview_url}")

        try:
            latest_flyer_element.click()
            logging.info(f"Clicked on flyer, navigating to: {flyer_preview_url}")
        except ElementClickInterceptedException:
            logging.warning("Click intercepted on flyer element. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", latest_flyer_element)
        except TimeoutException:
            logging.error("Timed out waiting for flyer to be clickable.")
            return None

        # 2. Wait for preview page to load
        logging.info("Waiting for preview page to load and menu button to appear...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal, a[href*=".pdf"], button[aria-label*="download"], a[data-label="Download"]'))
        )

        # 3. Click menu and find download link (USER'S ORIGINAL LOGIC)
        try:
            menu_button_icon = driver.find_element(By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal')
            menu_button = menu_button_icon.find_element(By.XPATH, './ancestor::button')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(menu_button))
            menu_button.click()
            logging.info("Clicked on menu button.")
            
            pdf_download_link_xpath = (
                "//a[contains(@class, 'button--primary') and contains(@class, 'menu-item__button') and ("
                "contains(., 'PDF Download') or "
                "contains(., 'Prospekt herunterladen') or "
                "contains(., 'Télécharger le prospectus') or "
                "contains(., 'Scarica il volantino') or "
                "contains(@href, '.pdf') or "
                "@data-label='Download' or "
                "contains(@aria-label, 'Download')"
                ")]"
            )
            pdf_download_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, pdf_download_link_xpath))
            )
            pdf_url = pdf_download_link.get_attribute('href')
            logging.info(f"Found PDF download URL in menu: {pdf_url}")
            return pdf_url
        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as e:
            logging.warning(f"Error with menu button, trying fallback. Error: {e}")
            try:
                direct_link_xpath = (
                    "//a[contains(@href, '.pdf') and ("
                    "contains(., 'PDF Download') or "
                    "contains(., 'Prospekt herunterladen') or "
                    "contains(., 'Télécharger le prospectus') or "
                    "contains(., 'Scarica il volantino') or "
                    "@data-label='Download' or "
                    "contains(@aria-label, 'Download')"
                    ")]"
                )
                direct_pdf_link_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, direct_link_xpath))
                )
                pdf_url = direct_pdf_link_element.get_attribute('href')
                logging.info(f"Found direct PDF link on page as fallback: {pdf_url}")
                return pdf_url
            except (TimeoutException, NoSuchElementException) as e_fallback:
                logging.error(f"No direct PDF link found as fallback: {e_fallback}")
                return None
                
    except WebDriverException:
        logging.exception("WebDriver error. Ensure chromedriver is installed and path is correct.")
        return None
    except Exception:
        logging.exception(f"An unexpected error occurred during the Selenium process for {market_name}.")
        try:
            screenshot_path = f"error_screenshot_{market_name}_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logging.info(f"Saved an error screenshot for debugging: {screenshot_path}")
        except Exception as e:
            logging.error(f"Could not even save a screenshot: {e}")
        return None
    finally:
        if driver:
            logging.info("Quitting WebDriver.")
            driver.quit()

def download_pdf(pdf_url, market_name, lang_code):
    """Downloads a PDF from a URL."""
    if not pdf_url:
        logging.error("No PDF URL provided to download_pdf function.")
        return None

    filename = f"{market_name}_{lang_code}_catalog_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(PDF_DOWNLOAD_DIR, filename)
    
    logging.info(f"Downloading PDF from: {pdf_url} to {filepath}...")
    try:
        response = requests.get(pdf_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"PDF downloaded to: {filepath}")
        return filepath
    except requests.exceptions.RequestException:
        logging.exception(f"Error downloading PDF from {pdf_url}")
        return None

def convert_pdf_to_images(pdf_path, output_image_dir, dpi=200):
    """Converts a PDF file into a series of PNG images."""
    if not pdf_path or not os.path.exists(pdf_path):
        logging.error(f"PDF file not found at {pdf_path}. Cannot convert.")
        return []

    logging.info(f"Converting PDF {pdf_path} to images...")
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
            
        logging.info(f"PDF converted. Total {len(local_image_paths)} images generated in {output_image_dir}.")
        return local_image_paths
    except Exception:
        logging.exception(f"Error converting PDF to images: {pdf_path}")
        return []

def upload_images_to_storage(local_image_paths, market_name, lang_code):
    """Uploads local images to Firebase Storage and returns their public URLs."""
    if not local_image_paths: return []

    logging.info(f"Uploading {len(local_image_paths)} images to Firebase Storage...")
    public_urls = []
    for local_path in local_image_paths:
        try:
            file_name = os.path.basename(local_path)
            destination_blob_name = f"catalogs/{market_name}/{lang_code}/{file_name}"
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_path)
            blob.make_public()
            public_urls.append(blob.public_url)
            logging.info(f"  - Uploaded {file_name}")
        except Exception:
            logging.exception(f"Failed to upload {os.path.basename(local_path)} to Firebase Storage.")
    
    logging.info(f"Finished uploading. {len(public_urls)} of {len(local_image_paths)} images are now public.")
    return public_urls

def update_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, page_urls, language):
    """Deletes old catalogs and adds a new one to Firestore with public Storage URLs."""
    if not page_urls:
        logging.warning("No storage URLs provided to update_firestore. Skipping database update.")
        return
        
    brochures_ref = db.collection('brochures')
    
    logging.info(f"Updating Firestore for {market_name} ({language})...")
    try:
        query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language)
        docs = query.stream()
        for doc in docs:
            logging.info(f"  - Deleting old catalog: {doc.id}")
            doc.reference.delete()
            
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
    except Exception:
        logging.exception(f"Error updating Firestore for {market_name} ({language})")

def cleanup_directory(dir_path):
    """Removes and recreates a directory."""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            logging.error(f"Error removing directory {dir_path}: {e}. Please check file permissions.")
            return False
    os.makedirs(dir_path, exist_ok=True)
    return True

def main():
    """Main execution function."""
    logging.info("--- Starting Catalog Automation Script ---")

    if not cleanup_directory(PDF_DOWNLOAD_DIR) or not cleanup_directory(LOCAL_IMAGE_DIR):
        return
    logging.info(f"Created temporary directories: {PDF_DOWNLOAD_DIR} and {LOCAL_IMAGE_DIR}")

    markets_and_languages = {
        ("lidl", "de"): "https://www.lidl.ch/c/de-CH/werbeprospekte-als-pdf/s10019683",
        ("lidl", "fr"): "https://www.lidl.ch/c/fr-CH/prospectus-pdf/s10019683",
        ("lidl", "it"): "https://www.lidl.ch/c/it-CH/volantini-in-pdf/s10019683"
    }

    # =========================================================================================
    # !!! TITLE LOCALIZATION IMPLEMENTED HERE !!!
    # This dictionary provides the correct title for each language.
    # =========================================================================================
    catalog_titles = {
        "de": "Wöchentlicher Katalog",
        "fr": "Catalogue de la semaine",
        "it": "Catalogo della settimana"
    }
    
    for (market_name, lang_code), market_url in markets_and_languages.items():
        logging.info(f"--- Processing {market_name.upper()} ({lang_code.upper()}) ---")

        if os.path.exists(PDF_DOWNLOAD_DIR):
            for file_name in os.listdir(PDF_DOWNLOAD_DIR):
                os.remove(os.path.join(PDF_DOWNLOAD_DIR, file_name))

        pdf_url_from_selenium = get_latest_pdf_link_selenium(market_name, market_url)
        if not pdf_url_from_selenium:
            logging.error(f"Failed to find PDF URL for {market_name} ({lang_code}). Skipping.")
            continue
            
        downloaded_pdf_path = download_pdf(pdf_url_from_selenium, market_name, lang_code)
        if not downloaded_pdf_path:
            logging.error(f"Could not download PDF for {market_name} ({lang_code}). Skipping.")
            continue
            
        current_image_output_dir = os.path.join(LOCAL_IMAGE_DIR, market_name, lang_code)
        os.makedirs(current_image_output_dir, exist_ok=True)
        local_image_paths = convert_pdf_to_images(downloaded_pdf_path, current_image_output_dir)
        if not local_image_paths:
            logging.error(f"No images were generated for {market_name} ({lang_code}). Skipping.")
            continue

        storage_urls = upload_images_to_storage(local_image_paths, market_name, lang_code)
        if not storage_urls:
            logging.error(f"Failed to upload any images for {market_name} ({lang_code}). Skipping Firestore update.")
            continue
            
        thumbnail_url = storage_urls[0] if storage_urls else ''
        
        # Get the localized title from the dictionary, with a default fallback
        base_title = catalog_titles.get(lang_code, "Weekly Catalog")
        catalog_title = f"{market_name.capitalize()} {base_title}"
        
        catalog_validity = f"Valid from {datetime.date.today().strftime('%d.%m.%Y')} - Next Week"
        
        update_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, storage_urls, lang_code)
        logging.info(f"--- Successfully processed {market_name.upper()} ({lang_code.upper()}) ---")
        
    logging.info("--- All Catalog Automation Finished ---")
    
    cleanup_directory(PDF_DOWNLOAD_DIR)
    cleanup_directory(LOCAL_IMAGE_DIR)
    logging.info("Cleaned up all temporary directories.")

if __name__ == "__main__":
    main()
