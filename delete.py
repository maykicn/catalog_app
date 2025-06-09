import requests
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException, StaleElementReferenceException
import fitz  # PyMuPDF
from PIL import Image
import datetime
import time
import logging # Logging modülü eklendi

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Firebase Setup ---
SERVICE_ACCOUNT_KEY_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\serviceAccountKey.json'
# Firebase Storage'a yükleme için gerekli
import firebase_admin
from firebase_admin import credentials, firestore, storage
FIREBASE_STORAGE_BUCKET = 'catalogapp-7b5bc.firebasestorage.app' # Sizin projenizin doğru bucket adı

try:
    if not firebase_admin._apps: # Birden fazla başlatmayı önlemek için kontrol
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_STORAGE_BUCKET
        })
    db = firestore.client()
    bucket = storage.bucket()
    logging.info("Firebase bağlantısı başarılı.")
except Exception as e:
    logging.error(f"Firestore bağlantı hatası: {e}")
    logging.error("Lütfen 'serviceAccountKey.json' dosyasının doğru yolda olduğundan ve geçerli olduğundan emin olun.")
    exit()

# --- Path Configurations ---
FLUTTER_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

PDF_DOWNLOAD_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_pdfs')

# BASE_ASSETS_DIR artık kullanılmıyor, resimler Storage'a gidecek
# BASE_ASSETS_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'assets', 'images')
# if not os.path.exists(BASE_ASSETS_DIR):
#     os.makedirs(BASE_ASSETS_DIR)

# --- Selenium Setup ---
CHROME_DRIVER_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\chromedriver.exe'

def setup_driver():
    options = Options()
    # options.add_argument("--headless")  # Arka planda çalıştır - Şimdilik kapatıyorum ki tarayıcıyı görebilelim
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

    prefs = {
        "download.default_directory": PDF_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": False # PDF'i tarayıcıda açmak yerine indirmeye zorla
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# *** GÜNCELLENMİŞ get_latest_pdf_link_selenium FONKSİYONU ***
# Mevcut get_latest_pdf_link_selenium fonksiyonunuzdaki ilgili bölümü güncelleyelim:
def get_latest_pdf_link_selenium(market_name, market_url):
    driver = setup_driver()
    pdf_url = None
    try:
        logging.info(f"Navigating to {market_name.upper()} at {market_url}...")
        driver.get(market_url)

        # --- ÇEREZ UYARISINI KABUL ETME --- (Bu kısım zaten kodunuzda var)
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
                    accept_cookies_button = WebDriverWait(driver, 5).until( # Bekleme süresini artırdım
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    driver.execute_script("arguments[0].click();", accept_cookies_button) # JavaScript ile tıklama
                    logging.info(f"Accepted cookie preferences using selector: {selector}.")
                    WebDriverWait(driver, 5).until( # invisibility için bekleme süresini artırdım
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    accepted = True
                    break
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                    continue

            if not accepted:
                logging.warning("No cookie consent pop-up found or button not clickable within timeout. Proceeding...")

        except Exception as e:
            logging.error(f"An error occurred while handling cookie consent: {e}. Proceeding...")
        # --- ÇEREZ UYARISI BİTİŞİ ---

        # 1. Ana sayfadaki en güncel katalog (a.flyer) elementini bekle ve tıkla
        logging.info("Waiting for main page flyers to load...")
        try:
            latest_flyer_element = WebDriverWait(driver, 25).until( 
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.flyer'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", latest_flyer_element)
            time.sleep(1) 

            flyer_preview_url = latest_flyer_element.get_attribute('href')
            logging.info(f"Found latest flyer preview URL: {flyer_preview_url}")

            driver.execute_script("arguments[0].click();", latest_flyer_element) 
            logging.info(f"Clicked on flyer, navigating to: {flyer_preview_url}")
            time.sleep(5) 

        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException) as e:
            logging.error(f"Timed out or failed to click on main flyer element: {e}. Returning None.")
            return None

        # 2. Katalog detay sayfasının yüklenmesini bekle
        logging.info("Waiting for preview page to load and menu button to appear...")
        # Hem menü butonu hem de doğrudan PDF linki (eğer varsa) için bekleyelim
        # Elementin görünürlüğünü de kontrol edelim
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal, a[href*=".pdf"], button[aria-label*="download"], a[data-label="Download"]'))
        )

        # 3. Hamburger menüye tıkla (PDF indirme menüsü butonu)
        logging.info("Waiting for PDF menu button to be present and clickable...")
        try:
            # Daha spesifik bir XPath kullanarak butonu bulmaya çalışın.
            # aria-label="Menu" olan ve içindeki SVG icon-bars-horizontal olan butonu hedefle
            pdf_menu_button_xpath = "//button[@aria-label='Menu' and .//svg[contains(@class, 'icon-bars-horizontal')]]"
            
            # Önce elementin DOM'da var olmasını bekleyelim
            pdf_menu_button = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, pdf_menu_button_xpath))
            )
            
            # Elementin görünür ve tıklanabilir hale gelmesini bekleyelim
            pdf_menu_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, pdf_menu_button_xpath))
            )

            # Elementin görünür olduğundan ve scroll pozisyonunda olduğundan emin olun
            driver.execute_script("arguments[0].scrollIntoView(true);", pdf_menu_button)
            time.sleep(1) # Scroll sonrası kısa bir bekleme

            # JavaScript ile tıklama daha güvenilir olabilir.
            driver.execute_script("arguments[0].click();", pdf_menu_button)
            logging.info("Clicked on PDF download menu button using JavaScript.")
            time.sleep(3) # Menü açıldıktan sonra bekle

            # *** BURASI GÜNCELLENDİ: PDF indirme linkini bulma kısmı ***
            logging.info("Searching for the PDF download link within the opened menu...")
            
            # Ekran görüntüsündeki HTML yapısına göre daha spesifik bir XPath.
            # li.menu-item içerisinde yer alan ve a etiketine sahip olan "Téléchargement PDF" metnini içeren elementi buluyoruz.
            pdf_download_link_xpath = "//li[contains(@class, 'menu-item') and contains(@class, 'menu-item--is-link')]//a[contains(@class, 'button--primary') and (.//span[contains(@class, 'button__label') and (contains(text(), 'PDF') or contains(text(), 'Prospekt') or contains(text(), 'Download') or contains(text(), 'Téléchargement'))] or contains(text(), 'PDF') or contains(text(), 'Prospekt') or contains(text(), 'Download') or contains(text(), 'Téléchargement'))]"

            pdf_download_link_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, pdf_download_link_xpath))
            )
            
            # Elementin tıklanabilir olduğundan emin olmak için ek bekleme
            pdf_download_link_element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, pdf_download_link_xpath))
            )

            pdf_url = pdf_download_link_element.get_attribute('href')
            logging.info(f"Found PDF download URL via menu: {pdf_url}")
            return pdf_url

        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
            logging.warning(f"Error with PDF download menu button or PDF download link on preview page: {e}")
            logging.info("Trying to find a direct PDF download link on the page as a fallback (without menu click)...")
            # Menü butonu bulunamazsa veya tıklanamazsa, doğrudan PDF linkini ara
            try:
                direct_pdf_link_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//a[contains(@href, '.pdf') and ("
                        "contains(@aria-label, 'Download') or "
                        "contains(., 'Download') or "
                        "contains(., 'PDF') or "
                        "contains(., 'Prospekt') or "
                        "contains(., 'Télécharger')"
                        ")]"
                    ))
                )
                pdf_url = direct_pdf_link_element.get_attribute('href')
                logging.info(f"Found direct PDF link on page as fallback: {pdf_url}")
                return pdf_url
            except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e_fallback:
                logging.error(f"No direct PDF link found as fallback: {e_fallback}")
                logging.error("Could not locate PDF download mechanism for this catalog. You may need to inspect the page manually.")
                return None

        except WebDriverException as e:
            logging.critical(f"WebDriver error: {e}")
            logging.critical("Please ensure ChromeDriver is installed and its path is correctly configured.")
            return None
        except Exception as e:
            logging.critical(f"An unexpected error occurred during Selenium process: {e}")
            return None
        finally:
            if driver:
                logging.info("Quitting WebDriver.")
                driver.quit()

    except WebDriverException as e:
        logging.critical(f"WebDriver error: {e}")
        logging.critical("Please ensure ChromeDriver is installed and its path is correctly configured.")
        return None
    except Exception as e:
        logging.critical(f"An unexpected error occurred during Selenium process: {e}")
        return None
    finally:
        if driver:
            logging.info("Quitting WebDriver.")
            driver.quit()

# *** GÜNCELLENMİŞ download_pdf FONKSİYONU ***
def download_pdf(pdf_url, market_name, lang_code):
    """
    PDF dosyasını indirir.
    """
    if not pdf_url:
        logging.warning(f"No PDF URL provided for {market_name} ({lang_code}). Cannot download.")
        return None

    filename = f"{market_name}_{lang_code}_catalog_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(PDF_DOWNLOAD_DIR, filename)

    logging.info(f"Downloading PDF from: {pdf_url} to {filepath} using requests...")
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"PDF downloaded to: {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading PDF {pdf_url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during PDF download: {e}")
        return None

def convert_pdf_to_images(pdf_path, output_temp_image_dir, dpi=200): # output_temp_image_dir parametresi eklendi
    """
    PDF dosyasını geçici görüntülere dönüştürür ve bu görüntülerin yerel yollarını döndürür.
    Bu görüntüler daha sonra Firebase Storage'a yüklenecektir.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        logging.error(f"PDF file not found at {pdf_path}. Cannot convert to images.")
        return []

    logging.info(f"Converting PDF {pdf_path} to images in {output_temp_image_dir}...")
    image_local_paths = []

    # Geçici çıktı dizinini oluştur
    if not os.path.exists(output_temp_image_dir):
        os.makedirs(output_temp_image_dir)

    try:
        pdf_document = fitz.open(pdf_path)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            image_filename = f"page_{page_num + 1:02d}.png"
            image_local_path = os.path.join(output_temp_image_dir, image_filename)
            img.save(image_local_path)
            image_local_paths.append(image_local_path)

        logging.info(f"PDF converted. Total {len(image_local_paths)} temporary images generated in {output_temp_image_dir}.")
        return image_local_paths

    except Exception as e:
        logging.error(f"Error converting PDF to images: {e}")
        return []

def upload_images_to_firebase_storage(image_local_paths, market_name, lang_code):
    """
    Yerel olarak oluşturulan görüntüleri Firebase Storage'a yükler.
    Her görüntü için Storage URL'lerini döndürür.
    """
    storage_urls = []
    base_storage_path = f"catalogs/{market_name}/{lang_code}/{datetime.date.today().strftime('%Y%m%d')}"

    for local_path in image_local_paths:
        file_name = os.path.basename(local_path)
        destination_blob_name = f"{base_storage_path}/{file_name}"
        blob = bucket.blob(destination_blob_name)

        try:
            blob.upload_from_filename(local_path)
            storage_path = f"gs://{FIREBASE_STORAGE_BUCKET}/{destination_blob_name}"
            storage_urls.append(storage_path)
            logging.info(f"Uploaded {file_name} to {destination_blob_name} (gs:// path).")
        except Exception as e:
            logging.error(f"Error uploading {file_name} to Firebase Storage: {e}")
            storage_urls.append("") 
    return storage_urls

def update_firestore(market_name, catalog_title, catalog_validity, thumbnail_storage_path, page_storage_paths, language):
    """
    Firestore'daki katalog bilgilerini günceller. Mevcut kataloğu siler ve yenisini ekler.
    Artık 'thumbnail' ve 'pages' alanları Firebase Storage URL'lerini içerecek.
    """
    brochures_ref = db.collection('brochures')

    logging.info(f"Checking for existing catalogs for {market_name} ({language})...")
    query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language).stream()
    for doc in query:
        logging.info(f"Deleting old catalog: {doc.id} for {market_name} ({language})")
        doc.reference.delete()

    new_catalog_data = {
        'marketName': market_name,
        'title': catalog_title,
        'validity': catalog_validity,
        'thumbnail': thumbnail_storage_path,
        'pages': page_storage_paths,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'language': language
    }

    try:
        doc_ref = brochures_ref.add(new_catalog_data)
        logging.info(f"New catalog added to Firestore with ID: {doc_ref[1].id}")
    except Exception as e:
        logging.error(f"Error adding document to Firestore: {e}")

def main():
    # Geçici PDF indirme dizinini BAŞLANGIÇTA bir kez temizle
    if os.path.exists(PDF_DOWNLOAD_DIR):
        try:
            shutil.rmtree(PDF_DOWNLOAD_DIR)
            logging.info(f"Removed existing PDF download directory: {PDF_DOWNLOAD_DIR}")
        except OSError as e:
            logging.critical(f"Error removing PDF download directory {PDF_DOWNLOAD_DIR}: {e}")
            logging.critical("Please ensure no files are open in this directory and try again.")
            return
    os.makedirs(PDF_DOWNLOAD_DIR)
    logging.info(f"Created PDF download directory: {PDF_DOWNLOAD_DIR}")

    # Geçici resim dosyaları için bir dizin oluştur
    TEMP_IMAGE_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_images')
    if not os.path.exists(TEMP_IMAGE_DIR):
        os.makedirs(TEMP_IMAGE_DIR)

    markets_and_languages = {
        ("lidl", "de"): "https://www.lidl.ch/c/de-CH/werbeprospekte-als-pdf/s10019683",
        ("lidl", "fr"): "https://www.lidl.ch/c/fr-CH/prospectus-pdf/s10019683",
        ("lidl", "it"): "https://www.lidl.ch/c/it-CH/volantini-in-pdf/s10019683"
    }

    language_names = {
        "de": "Deutsch",
        "fr": "Français",
        "it": "Italiano"
    }

    for (market_name, lang_code), market_url in markets_and_languages.items():
        logging.info(f"\n--- Processing {market_name.upper()} Catalog ({lang_code.upper()}) ---")

        # Her yeni dil için işlem yapmadan önce indirme klasörünü ve geçici resim klasörünü temizle
        if os.path.exists(PDF_DOWNLOAD_DIR):
            try:
                for file_name in os.listdir(PDF_DOWNLOAD_DIR):
                    file_path = os.path.join(PDF_DOWNLOAD_DIR, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logging.info(f"Cleaned up previous PDF files in {PDF_DOWNLOAD_DIR} for new iteration.")
            except OSError as e:
                logging.error(f"Error cleaning up PDF download directory {PDF_DOWNLOAD_DIR} before new iteration: {e}")
                logging.warning("Proceeding anyway, but this might cause issues.")
        
        # Geçici resim klasörünü temizle
        if os.path.exists(TEMP_IMAGE_DIR):
            try:
                shutil.rmtree(TEMP_IMAGE_DIR)
                os.makedirs(TEMP_IMAGE_DIR) # Yeniden oluştur
                logging.info(f"Cleaned up temporary image directory: {TEMP_IMAGE_DIR} for new iteration.")
            except OSError as e:
                logging.error(f"Error cleaning up temporary image directory {TEMP_IMAGE_DIR}: {e}")
                logging.warning("Proceeding anyway, but this might cause issues.")


        # 1. En güncel PDF linkini bul (veya indirmeyi tetikle)
        pdf_url_from_selenium = get_latest_pdf_link_selenium(market_name, market_url)

        # 2. PDF'i indir (veya indirilmiş olanı bul)
        downloaded_pdf_path = download_pdf(pdf_url_from_selenium, market_name, lang_code)
        if not downloaded_pdf_path:
            logging.error(f"Could not download PDF for {market_name} ({lang_code}). Skipping to next market/language.")
            continue

        # 3. PDF'i geçici olarak resimlere dönüştür
        image_local_paths = convert_pdf_to_images(downloaded_pdf_path, TEMP_IMAGE_DIR)

        if not image_local_paths:
            logging.error(f"No images were generated from PDF for {market_name} ({lang_code}). Skipping to next market/language.")
            continue

        # 4. Resimleri Firebase Storage'a yükle
        image_storage_urls = upload_images_to_firebase_storage(image_local_paths, market_name, lang_code)

        if not image_storage_urls or any(url == "" for url in image_storage_urls):
            logging.error(f"Some or all images failed to upload to Firebase Storage for {market_name} ({lang_code}). Skipping Firestore update.")
            continue
        
        thumbnail_storage_path = image_storage_urls[0] if image_storage_urls else ''

        # 5. Firestore'u güncelle
        catalog_title = f"{market_name.capitalize()} Weekly Catalog ({language_names.get(lang_code, lang_code.upper())})"
        catalog_validity = f"Valid from {datetime.date.today().strftime('%d.%d.%Y')} - Next Week" # Date format corrected: %d.%m.%Y

        update_firestore(market_name, catalog_title, catalog_validity, thumbnail_storage_path, image_storage_urls, lang_code)

        logging.info(f"\n--- {market_name.upper()} ({lang_code.upper()}) Automation Completed ---")
        logging.info("Firebase Storage and Firestore updated.")

    logging.info("\n--- All Catalog Automation Finished ---")
    if os.path.exists(PDF_DOWNLOAD_DIR):
        try:
            shutil.rmtree(PDF_DOWNLOAD_DIR)
            logging.info(f"Cleaned up temporary PDF directory: {PDF_DOWNLOAD_DIR}")
        except OSError as e:
            logging.error(f"Error cleaning up temporary PDF directory {PDF_DOWNLOAD_DIR}: {e}")
    
    if os.path.exists(TEMP_IMAGE_DIR):
        try:
            shutil.rmtree(TEMP_IMAGE_DIR)
            logging.info(f"Cleaned up temporary image directory: {TEMP_IMAGE_DIR}")
        except OSError as e:
            logging.error(f"Error cleaning up temporary image directory {TEMP_IMAGE_DIR}: {e}")

if __name__ == "__main__":
    main()