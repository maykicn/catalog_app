import requests
from bs4 import BeautifulSoup
import fitz # PyMuPDF
import os
import shutil
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException

# --- AYARLAR ---
FLUTTER_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# Resimlerin kopyalanacağı ana assets klasörü (assets/images)
BASE_ASSETS_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'assets', 'images')
PDF_DOWNLOAD_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_pdfs') # Geçici PDF indirme klasörü

# Firestore koleksiyon adı
FIRESTORE_COLLECTION_NAME = 'brochures'

# Firebase Hizmet Hesabı Anahtarınızın yolu (daha önce indirdiğiniz serviceAccountKey.json)
# Bu dosyayı asla Git'e yüklemeyin!
SERVICE_ACCOUNT_KEY_PATH = os.path.join(FLUTTER_PROJECT_ROOT, 'serviceAccountKey.json')

# WebDriver servis yolu (eğer PATH'e eklemediyseniz chromedriver.exe'nin tam yolu)
CHROMEDRIVER_PATH = None # PATH'e eklediyseniz None bırakın, aksi halde tam yolunu yazın

# --- Firebase Admin SDK Başlatma ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")
        print("Please ensure 'serviceAccountKey.json' is in the correct path and valid.")
        exit() # Hata durumunda betiği sonlandır

db = firestore.client()

def get_latest_pdf_link_selenium(market_url):
    """
    Selenium kullanarak web sayfasından en güncel PDF broşür linkini bulur.
    Belirli bir marketin URL'sine göre çalışır.
    """
    print(f"Initializing WebDriver for {market_url}...")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = None
    try:
        if CHROMEDRIVER_PATH:
            service = Service(executable_path=CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        driver.get(market_url)
        print(f"Navigated to: {market_url}")

        # --- ÇEREZ UYARISINI KABUL ETME ---
        try:
            accept_cookies_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.uc-btn[data-accept-action='all']"))
            )
            accept_cookies_button.click()
            print("Accepted cookie preferences.")
            WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "button.uc-btn[data-accept-action='all']"))
            )
            print("Cookie pop-up closed successfully.")
        except TimeoutException:
            print("No cookie consent pop-up found or button not clickable within timeout. Proceeding...")
        except NoSuchElementException:
            print("Cookie consent button element not found. Proceeding...")
        except Exception as e:
            print(f"An error occurred while handling cookie consent: {e}. Proceeding...")
        # --- ÇEREZ UYARISI BİTİŞİ ---

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a.flyer'))
        )
        print("Main page flyers loaded.")

        latest_flyer_element = driver.find_element(By.CSS_SELECTOR, 'a.flyer')
        flyer_preview_url = latest_flyer_element.get_attribute('href')
        print(f"Found latest flyer preview URL: {flyer_preview_url}")

        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(latest_flyer_element))
            latest_flyer_element.click()
            print(f"Clicked on flyer, navigating to: {flyer_preview_url}")
        except ElementClickInterceptedException:
            print("Click intercepted on flyer element. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", latest_flyer_element)
            print(f"Clicked on flyer via JavaScript, navigating to: {flyer_preview_url}")
        except TimeoutException:
            print("Timed out waiting for flyer to be clickable.")
            return None

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal'))
        )
        print("Preview page loaded. Looking for menu button...")

        try:
            menu_button_icon = driver.find_element(By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal')
            menu_button = menu_button_icon.find_element(By.XPATH, './ancestor::button')

            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(menu_button))
            menu_button.click()
            print("Clicked on menu button.")

            pdf_download_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'button--primary') and contains(@class, 'menu-item__button') and contains(., 'PDF Download')]"))
            )

            pdf_url = pdf_download_link.get_attribute('href')
            print(f"Found PDF download URL: {pdf_url}")
            return pdf_url

        except NoSuchElementException:
            print("Menu button or PDF download link not found on preview page as expected.")
            return None
        except TimeoutException:
            print("Timed out waiting for menu button or PDF download link to appear.")
            return None
        except ElementClickInterceptedException:
            print("Click intercepted on menu button. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", menu_button)
            print("Clicked on menu button via JavaScript.")
            pdf_download_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'button--primary') and contains(@class, 'menu-item__button') and contains(., 'PDF Download')]"))
            )
            pdf_url = pdf_download_link.get_attribute('href')
            print(f"Found PDF download URL: {pdf_url}")
            return pdf_url

    except WebDriverException as e:
        print(f"WebDriver error: {e}")
        print("Please ensure ChromeDriver is installed and its path is correctly configured in system PATH or CHROMEDRIVER_PATH variable.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Selenium process: {e}")
        return None
    finally:
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

def download_pdf(pdf_url, download_path):
    """PDF dosyasını indirir."""
    print(f"Downloading PDF from: {pdf_url}")
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"PDF downloaded to: {download_path}")
        return download_path
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF {pdf_url}: {e}")
        return None

def convert_pdf_to_images(pdf_path, output_image_dir):
    """PDF'i resimlere dönüştürür ve belirlenen dizine kaydeder."""
    print(f"Converting PDF {pdf_path} to images...")
    # output_image_dir zaten assets/images olmalı, bu klasörü oluşturmak gerekli
    if not os.path.exists(output_image_dir):
        os.makedirs(output_image_dir)

    doc = None
    image_paths = []
    try:
        doc = fitz.open(pdf_path)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=200)
            img_filename = f"page_{i+1:02d}.png" # Dosya adını belirle
            img_path = os.path.join(output_image_dir, img_filename) # assets/images/page_XX.png
            pix.save(img_path)

            # Flutter için doğru yol formatı: 'assets/images/page_01.png'
            # relpath kullanarak FLUTTER_PROJECT_ROOT'a göre göreceli yolu alıyoruz
            # Ardından os.sep'i '/' ile değiştiriyoruz çünkü Flutter asset yolları '/' kullanır.
            relative_image_path = os.path.relpath(img_path, FLUTTER_PROJECT_ROOT).replace(os.sep, '/')
            image_paths.append(relative_image_path)

            print(f"  Saved {img_path}")
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []
    finally:
        if doc:
            doc.close()
    print(f"PDF converted. Total {len(image_paths)} images generated in {output_image_dir}.")
    return image_paths

def update_firestore(market_name, title, validity, thumbnail_path, page_image_paths):
        """Firestore'daki 'brochures' koleksiyonunu günceller."""
        print("Updating Firestore...")
        try:
            doc_ref = db.collection(FIRESTORE_COLLECTION_NAME).add({
                'marketName': market_name,
                'title': title,
                'validity': validity,
                'thumbnailUrl': page_image_paths[0],
                'catalogPageImages': page_image_paths,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            print(f"New brochure added to Firestore. Document ID: {doc_ref[1].id}")
            # Eğer belge ID'sini gerçekten görmek istiyorsanız ve sunucu zaman damgasını beklemek istemiyorsanız:
            # doc_id = doc_ref.id
            # print(f"New brochure added to Firestore with ID: {doc_id}")

        except Exception as e:
            print(f"Error updating Firestore: {e}")

def main():
    # Geçici PDF klasörünü temizle/oluştur
    if os.path.exists(PDF_DOWNLOAD_DIR):
        try:
            shutil.rmtree(PDF_DOWNLOAD_DIR)
        except OSError as e:
            print(f"Error removing temporary PDF directory {PDF_DOWNLOAD_DIR}: {e}")
            print("Please ensure no files are open in this directory and try again.")
            return
    os.makedirs(PDF_DOWNLOAD_DIR)

    current_market_name = "lidl"
    current_market_url = "https://www.lidl.ch/c/de-CH/werbeprospekte-als-pdf/s10019683"

    print(f"\n--- Processing {current_market_name.upper()} Catalog ---")

    pdf_url = get_latest_pdf_link_selenium(current_market_url)
    if not pdf_url:
        print(f"Failed to get PDF URL for {current_market_name}. Exiting.")
        if os.path.exists(PDF_DOWNLOAD_DIR): shutil.rmtree(PDF_DOWNLOAD_DIR)
        return

    pdf_filename = f"{current_market_name}_catalog_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    pdf_local_path = os.path.join(PDF_DOWNLOAD_DIR, pdf_filename)
    downloaded_pdf_path = download_pdf(pdf_url, pdf_local_path)
    if not downloaded_pdf_path:
        print(f"Failed to download PDF for {current_market_name}. Exiting.")
        if os.path.exists(PDF_DOWNLOAD_DIR): shutil.rmtree(PDF_DOWNLOAD_DIR)
        return

    # --- BURADAKİ KLASÖR OLUŞTURMA VE YOL AYARLAMASI TAMAMEN DÜZLEŞTİRİLDİ ---
    # output_assets_dir direkt 'assets/images' olacak
    output_assets_dir = BASE_ASSETS_DIR

    # assets/images altındaki mevcut tüm page_XX.png dosyalarını temizle
    print(f"Cleaning up existing page_XX.png files in {output_assets_dir}...")
    # Klasörün varlığını kontrol et ve gerekirse oluştur
    if not os.path.exists(output_assets_dir):
        try:
            os.makedirs(output_assets_dir)
            print(f"Created assets directory: {output_assets_dir}")
        except OSError as e:
            print(f"Error creating assets directory {output_assets_dir}: {e}")
            if os.path.exists(PDF_DOWNLOAD_DIR): shutil.rmtree(PDF_DOWNLOAD_DIR)
            return

    for filename in os.listdir(output_assets_dir):
        if filename.startswith('page_') and filename.endswith('.png'):
            try:
                os.remove(os.path.join(output_assets_dir, filename))
                print(f"  Removed existing {filename}")
            except OSError as e:
                print(f"Error removing {filename}: {e}")

    # convert_pdf_to_images fonksiyonuna sadece ana varlık dizinini gönderiyoruz
    image_asset_paths = convert_pdf_to_images(downloaded_pdf_path, output_assets_dir)

    if not image_asset_paths:
        print(f"No images were generated from PDF for {current_market_name}. Exiting.")
        if os.path.exists(PDF_DOWNLOAD_DIR): shutil.rmtree(PDF_DOWNLOAD_DIR)
        return

    thumbnail_asset_path = image_asset_paths[0] if image_asset_paths else ''

    # 4. Firestore'u güncelle
    catalog_title = f"{current_market_name.capitalize()} Weekly Catalog ({datetime.date.today().strftime('%d.%m.%Y')})"
    catalog_validity = f"Valid from {datetime.date.today().strftime('%d.%m.%Y')} - Next Week"

    update_firestore(current_market_name, catalog_title, catalog_validity, thumbnail_asset_path, image_asset_paths)

    print(f"\n--- {current_market_name.upper()} Automation Completed ---")
    print(f"Catalog images saved to: {output_assets_dir}")
    print("Firestore updated. You may need to run 'flutter pub get' if new assets paths were added.")
    print("Remember to manually update pubspec.yaml to include new market asset folders if you haven't used the general assets/images/ entry.")

    if os.path.exists(PDF_DOWNLOAD_DIR):
        try:
            shutil.rmtree(PDF_DOWNLOAD_DIR)
            print(f"Cleaned up temporary PDF directory: {PDF_DOWNLOAD_DIR}")
        except OSError as e:
            print(f"Error during final cleanup of temporary PDF directory {PDF_DOWNLOAD_DIR}: {e}")

if __name__ == '__main__':
    main()