import os
import shutil
import logging
import firebase_admin
from firebase_admin import credentials, firestore, storage
import requests
from PIL import Image
import fitz  # PyMuPDF
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import datetime
import re

# =========================================================================================
# GLOBAL CONFIGURATION
# =========================================================================================

# --- Firebase Configuration ---
SERVICE_ACCOUNT_KEY_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\serviceAccountKey.json'
FIREBASE_STORAGE_BUCKET = 'catalogapp-7b5bc.firebasestorage.app'

# --- Selenium WebDriver Path ---
CHROME_DRIVER_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\chromedriver.exe'

# --- Directory Paths ---
# Note: PROJECT_ROOT is now one level up from this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PDF_DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, 'temp_pdfs')
LOCAL_IMAGE_DIR = os.path.join(PROJECT_ROOT, 'temp_images')

# =========================================================================================
# INITIALIZATION FUNCTIONS
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
    file_handler = logging.FileHandler('catalog_automation.log', mode='w', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

def initialize_firebase():
    """Initializes the Firebase Admin SDK and returns db and bucket clients."""
    try:
        logging.info("Initializing Firebase Admin SDK...")
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'storageBucket': FIREBASE_STORAGE_BUCKET})
        db = firestore.client()
        bucket = storage.bucket()
        logging.info("Firebase Admin SDK initialized successfully.")
        return db, bucket
    except Exception as e:
        logging.critical(f"Firebase Admin SDK initialization error: {e}")
        exit()

# Initialize Firebase and get clients
db, bucket = initialize_firebase()


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
# HELPER FUNCTIONS
# =========================================================================================

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

def download_pdf(pdf_url, market_name, lang_code, catalog_index):
    """Downloads a PDF from the given URL."""
    if not pdf_url: return None
    filename = f"{market_name}_{lang_code}_catalog_{catalog_index}.pdf"
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

def add_catalog_to_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, page_urls, language, week_type):
    """Adds a new catalog to Firestore, including its week type ('current' or 'next')."""
    if not page_urls:
        logging.warning("No page URLs to upload, skipping Firestore update.")
        return
    logging.info(f"Adding new catalog to Firestore: '{catalog_title}' (Type: {week_type})")
    brochures_ref = db.collection('brochures')
    try:
        new_catalog_data = {
            'marketName': market_name,
            'title': catalog_title,
            'validity': catalog_validity,
            'thumbnail': thumbnail_url,
            'pages': page_urls,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'language': language,
            'weekType': week_type  # NEW FIELD FOR THE UI
        }
        doc_ref = brochures_ref.add(new_catalog_data)
        logging.info(f"New catalog added to Firestore with ID: {doc_ref[1].id}")
    except Exception as e:
        logging.exception(f"Error adding document to Firestore: {e}")

def extract_start_date(validity_string):
    """
    Extracts the first DD.MM date from a string and returns a date object.
    Handles the year-end transition correctly.
    """
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.?', validity_string)
    if not match:
        return None

    day = int(match.group(1))
    month = int(match.group(2))
    today = datetime.date.today()
    
    # Handle year-end case (e.g., in December, a catalog for January is for next year)
    year = today.year
    if month < today.month:
        year += 1
        
    try:
        return datetime.date(year, month, day)
    except ValueError:
        # Handles invalid dates like 31.02
        return None
    

def get_stored_validity_strings(market_name, language):
    """
    Fetches only the 'validity' strings of currently stored brochures from Firestore
    for a specific market and language.
    """
    try:
        brochures_ref = db.collection('brochures')
        query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language)
        docs = query.stream()
        # Create a list of all validity strings found in the database
        return [doc.to_dict().get('validity', '') for doc in docs]
    except Exception as e:
        logging.error(f"Could not fetch stored validity strings for {market_name} ({language}). Error: {e}")
        return []