import requests
from bs4 import BeautifulSoup
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
import fitz  # PyMuPDF
from PIL import Image
import datetime
import time

# --- Firebase Admin SDK Setup ---
# Make sure to install the firebase-admin library: pip install firebase-admin
import firebase_admin
from firebase_admin import credentials, firestore, storage

# --- Firebase Configuration ---
# IMPORTANT: Replace with the actual path to your service account key file
SERVICE_ACCOUNT_KEY_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\serviceAccountKey.json'

# =========================================================================================
# !!! IMPORTANT FIX FOR FIREBASE STORAGE ERROR !!!
# The bucket name has been corrected based on your screenshot.
# The original script had ".appspot.com", but your bucket uses ".firebasestorage.app".
# =========================================================================================
FIREBASE_STORAGE_BUCKET = 'catalogapp-7b5bc.firebasestorage.app' # <-- CORRECTED BUCKET NAME

# --- Initialize Firebase Admin SDK ---
try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': FIREBASE_STORAGE_BUCKET
    })
    db = firestore.client()
    bucket = storage.bucket()
    print("Firebase Admin SDK initialized successfully. Firestore and Storage are connected.")
except Exception as e:
    print(f"Firebase Admin SDK initialization error: {e}")
    print("Please ensure 'serviceAccountKey.json' is valid and the path is correct.")
    print("Most importantly, verify the FIREBASE_STORAGE_BUCKET name above.")
    exit()

# --- Path Configurations ---
FLUTTER_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
PDF_DOWNLOAD_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_pdfs')
LOCAL_IMAGE_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_images') # For temporary local storage before upload

# --- Selenium Setup ---
# IMPORTANT: Replace with the actual path to your chromedriver.exe
CHROME_DRIVER_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\chromedriver.exe'

def setup_driver():
    """(USER'S ORIGINAL SCRIPT) Configures and returns a Selenium WebDriver instance."""
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

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
    """(USER'S ORIGINAL SCRIPT) Uses Selenium to find the URL for the latest PDF catalog."""
    driver = setup_driver()
    pdf_url = None
    try:
        print(f"Navigating to {market_name.upper()} at {market_url}...")
        driver.get(market_url)

        # --- Handle Cookie Consent ---
        try:
            accept_cookies_selectors = [
                "button.uc-btn[data-accept-action='all']",
                "button.accept-all-button",
                "#onetrust-accept-btn-handler",
                "button.button--secondary.cookie-button",
                "button[id^='onetrust-accept-btn']",
                "div.cookie-banner button"
            ]
            accepted = False
            for selector in accept_cookies_selectors:
                try:
                    accept_cookies_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    accept_cookies_button.click()
                    print(f"Accepted cookie preferences using selector: {selector}.")
                    WebDriverWait(driver, 3).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    accepted = True
                    break
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                    continue
            if not accepted:
                print("No cookie consent pop-up found or button not clickable within timeout. Proceeding...")
        except Exception as e:
            print(f"An error occurred while handling cookie consent: {e}. Proceeding...")

        # 1. Click the main page flyer
        print("Waiting for main page flyers to load...")
        latest_flyer_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.flyer'))
        )
        flyer_preview_url = latest_flyer_element.get_attribute('href')
        print(f"Found latest flyer preview URL: {flyer_preview_url}")

        try:
            latest_flyer_element.click()
            print(f"Clicked on flyer, navigating to: {flyer_preview_url}")
        except ElementClickInterceptedException:
            print("Click intercepted on flyer element. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", latest_flyer_element)
            print(f"Clicked on flyer via JavaScript, navigating to: {flyer_preview_url}")
        except TimeoutException:
            print("Timed out waiting for flyer to be clickable.")
            return None

        # 2. Wait for preview page to load
        print("Waiting for preview page to load and menu button to appear...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal, a[href*=".pdf"], button[aria-label*="download"], a[data-label="Download"]'))
        )

        # 3. Click menu and find download link
        try:
            menu_button_icon = driver.find_element(By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal')
            menu_button = menu_button_icon.find_element(By.XPATH, './ancestor::button')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(menu_button))
            menu_button.click()
            print("Clicked on menu button.")
            
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
            print(f"Found PDF download URL: {pdf_url}")
            return pdf_url
        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as e:
            print(f"Error with menu button or PDF download link: {e}")
            print("Trying to find a direct PDF download link as a fallback...")
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
                print(f"Found direct PDF link on page as fallback: {pdf_url}")
                return pdf_url
            except (TimeoutException, NoSuchElementException) as e_fallback:
                print(f"No direct PDF link found as fallback: {e_fallback}")
                print("Could not locate PDF download mechanism. You may need to inspect the page manually.")
                return None
                
    except WebDriverException as e:
        print(f"WebDriver error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during the Selenium process: {e}")
        driver.save_screenshot(f"error_screenshot_{market_name}_{int(time.time())}.png")
        print("Saved an error screenshot for debugging.")
        return None
    finally:
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

def download_pdf(pdf_url, market_name, lang_code):
    """(USER'S ORIGINAL SCRIPT) Downloads a PDF from a URL or finds the latest downloaded file."""
    filename = f"{market_name}_{lang_code}_catalog_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(PDF_DOWNLOAD_DIR, filename)

    if pdf_url:
        print(f"Downloading PDF from: {pdf_url} to {filepath} using requests...")
        try:
            response = requests.get(pdf_url, stream=True, timeout=60)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"PDF downloaded to: {filepath}")
            return filepath
        except requests.exceptions.RequestException as e:
            print(f"Error downloading PDF {pdf_url}: {e}")
            return None
    else:
        print(f"No direct PDF URL provided. Checking for downloaded file in {PDF_DOWNLOAD_DIR}...")
        time.sleep(5)
        
        pdf_files = [f for f in os.listdir(PDF_DOWNLOAD_DIR) if f.endswith('.pdf')]
        if not pdf_files:
            print(f"No PDF found in {PDF_DOWNLOAD_DIR} after Selenium operation.")
            return None
        
        latest_pdf_file = max(pdf_files, key=lambda f: os.path.getmtime(os.path.join(PDF_DOWNLOAD_DIR, f)))
        found_filepath = os.path.join(PDF_DOWNLOAD_DIR, latest_pdf_file)
        
        if os.path.basename(found_filepath) != filename:
            try:
                print(f"Found recently downloaded PDF: {found_filepath}. Renaming to: {filename}")
                shutil.move(found_filepath, filepath)
                return filepath
            except Exception as e:
                print(f"Error renaming downloaded PDF: {e}. Returning original path: {found_filepath}")
                return found_filepath
        else:
            print(f"Found recently downloaded PDF: {found_filepath} (already named correctly).")
            return found_filepath

def convert_pdf_to_images(pdf_path, output_image_dir, dpi=200):
    """Converts a PDF file into a series of PNG images."""
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"PDF file not found at {pdf_path}. Cannot convert.")
        return []

    print(f"Converting PDF {pdf_path} to images...")
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
            
        print(f"PDF converted. Total {len(local_image_paths)} images generated in {output_image_dir}.")
        return local_image_paths
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []

def upload_images_to_storage(local_image_paths, market_name, lang_code):
    """Uploads local images to Firebase Storage and returns their public URLs."""
    if not local_image_paths: return []

    print(f"Uploading {len(local_image_paths)} images to Firebase Storage...")
    public_urls = []
    for local_path in local_image_paths:
        try:
            file_name = os.path.basename(local_path)
            destination_blob_name = f"catalogs/{market_name}/{lang_code}/{file_name}"
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_path)
            blob.make_public()
            public_urls.append(blob.public_url)
            print(f"  - Uploaded {file_name} to {destination_blob_name}")
        except Exception as e:
            print(f"Failed to upload {os.path.basename(local_path)} to Firebase Storage: {e}")
            print("  - PLEASE CHECK YOUR FIREBASE_STORAGE_BUCKET NAME AT THE TOP OF THE SCRIPT.")
    
    print(f"Finished uploading. {len(public_urls)} of {len(local_image_paths)} images are now public.")
    return public_urls

def update_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, page_urls, language):
    """Deletes old catalogs and adds a new one to Firestore with public Storage URLs."""
    if not page_urls:
        print("No storage URLs provided to update_firestore. Skipping database update.")
        return
        
    brochures_ref = db.collection('brochures')
    
    print(f"Updating Firestore for {market_name} ({language})...")
    query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language)
    for doc in query.stream():
        print(f"  - Deleting old catalog: {doc.id}")
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
    
    try:
        doc_ref = brochures_ref.add(new_catalog_data)
        print(f"New catalog added to Firestore with ID: {doc_ref[1].id}")
    except Exception as e:
        print(f"Error adding document to Firestore: {e}")

def cleanup_directory(dir_path):
    """Removes and recreates a directory."""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            print(f"Error removing directory {dir_path}: {e}. Please check file permissions.")
            return False
    os.makedirs(dir_path, exist_ok=True)
    return True

def main():
    """Main execution function."""
    print("--- Starting Catalog Automation Script ---")
    
    if not cleanup_directory(PDF_DOWNLOAD_DIR) or not cleanup_directory(LOCAL_IMAGE_DIR):
        return
    print(f"Created temporary directories: {PDF_DOWNLOAD_DIR} and {LOCAL_IMAGE_DIR}")

    markets_and_languages = {
        ("lidl", "de"): "https://www.lidl.ch/c/de-CH/werbeprospekte-als-pdf/s10019683",
        ("lidl", "fr"): "https://www.lidl.ch/c/fr-CH/prospectus-pdf/s10019683",
        ("lidl", "it"): "https://www.lidl.ch/c/it-CH/volantini-in-pdf/s10019683"
    }
    language_names = {"de": "Deutsch", "fr": "Français", "it": "Italiano"}

    for (market_name, lang_code), market_url in markets_and_languages.items():
        print(f"\n{'='*20} Processing {market_name.upper()} ({lang_code.upper()}) {'='*20}")

        # Clean temp PDF dir before each run to avoid picking up old files
        if os.path.exists(PDF_DOWNLOAD_DIR):
            for file_name in os.listdir(PDF_DOWNLOAD_DIR):
                os.remove(os.path.join(PDF_DOWNLOAD_DIR, file_name))

        pdf_url_from_selenium = get_latest_pdf_link_selenium(market_name, market_url)
        downloaded_pdf_path = download_pdf(pdf_url_from_selenium, market_name, lang_code)
        if not downloaded_pdf_path:
            print(f"Could not download or find PDF for {market_name} ({lang_code}). Skipping.")
            continue
            
        current_image_output_dir = os.path.join(LOCAL_IMAGE_DIR, market_name, lang_code)
        os.makedirs(current_image_output_dir, exist_ok=True)
        local_image_paths = convert_pdf_to_images(downloaded_pdf_path, current_image_output_dir)
        if not local_image_paths:
            print(f"No images were generated for {market_name} ({lang_code}). Skipping.")
            continue

        storage_urls = upload_images_to_storage(local_image_paths, market_name, lang_code)
        if not storage_urls:
            print(f"Failed to upload any images for {market_name} ({lang_code}). Skipping Firestore update.")
            continue
            
        thumbnail_url = storage_urls[0] if storage_urls else ''
        catalog_title = f"{market_name.capitalize()} Weekly Catalog ({language_names.get(lang_code, lang_code.upper())})"
        catalog_validity = f"Valid from {datetime.date.today().strftime('%d.%m.%Y')} - Next Week"
        
        update_firestore(market_name, catalog_title, catalog_validity, thumbnail_url, storage_urls, lang_code)
        print(f"--- Successfully processed {market_name.upper()} ({lang_code.upper()}) ---")
        
    print("\n--- All Catalog Automation Finished ---")
    
    cleanup_directory(PDF_DOWNLOAD_DIR)
    cleanup_directory(LOCAL_IMAGE_DIR)
    print("Cleaned up all temporary directories.")

if __name__ == "__main__":
    main()
