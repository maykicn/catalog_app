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
from google.cloud import firestore
import datetime
import time

# --- Firebase Setup ---
SERVICE_ACCOUNT_KEY_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\serviceAccountKey.json'

try:
    db = firestore.Client.from_service_account_json(SERVICE_ACCOUNT_KEY_PATH)
    print("Firestore bağlantısı başarılı.")
except Exception as e:
    print(f"Firestore bağlantı hatası: {e}")
    print("Lütfen 'serviceAccountKey.json' dosyasının doğru yolda olduğundan ve geçerli olduğundan emin olun.")
    exit()

# --- Path Configurations ---
FLUTTER_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

PDF_DOWNLOAD_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'temp_pdfs')

BASE_ASSETS_DIR = os.path.join(FLUTTER_PROJECT_ROOT, 'assets', 'images')
if not os.path.exists(BASE_ASSETS_DIR):
    os.makedirs(BASE_ASSETS_DIR)

# --- Selenium Setup ---
CHROME_DRIVER_PATH = 'C:\\Users\\TAACAMU4\\Work\\Projects\\PORTFOLIO\\catalog_app\\chromedriver.exe'

def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Arka planda çalıştır - Şimdilik kapatıyorum ki tarayıcıyı görebilelim
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

# *** GÜNCELLENMİŞ get_latest_pdf_link_selenium FONKSİYONU ***
def get_latest_pdf_link_selenium(market_name, market_url):
    driver = setup_driver()
    pdf_url = None
    try:
        print(f"Navigating to {market_name.upper()} at {market_url}...")
        driver.get(market_url)

        # --- ÇEREZ UYARISINI KABUL ETME ---
        try:
            accept_cookies_selectors = [
                "button.uc-btn[data-accept-action='all']",
                "button.accept-all-button",
                "#onetrust-accept-btn-handler", # En son çıktıda bu çalışmış
                "button.button--secondary.cookie-button",
                "button[id^='onetrust-accept-btn']", # ID'si onetrust-accept-btn ile başlayan herhangi bir buton
                "div.cookie-banner button" # Genel bir yaklaşım
            ]
            
            accepted = False
            for selector in accept_cookies_selectors:
                try:
                    accept_cookies_button = WebDriverWait(driver, 3).until( # Bekleme süresini düşürdüm
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
        # --- ÇEREZ UYARISI BİTİŞİ ---

        # 1. Ana sayfadaki en güncel katalog (a.flyer) elementini bekle ve tıkla
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
        
        # 2. Katalog detay sayfasının yüklenmesini bekle
        print("Waiting for preview page to load and menu button to appear...")
        # Hem menü butonu hem de doğrudan PDF linki (eğer varsa) için bekleyelim
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal, a[href*=".pdf"], button[aria-label*="download"], a[data-label="Download"]'))
        )

        # 3. Hamburger menüye tıkla ve PDF indirme linkini bul
        try:
            menu_button_icon = driver.find_element(By.CSS_SELECTOR, 'span.button__icon svg.icon-bars-horizontal')
            menu_button = menu_button_icon.find_element(By.XPATH, './ancestor::button')

            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(menu_button))
            menu_button.click()
            print("Clicked on menu button.")
            
            # Menü açıldıktan sonra PDF indirme linkini bekle
            # Tüm olası dillerdeki metinleri ve genel öznitelikleri kapsayan XPath
            pdf_download_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, 
                    "//a[contains(@class, 'button--primary') and contains(@class, 'menu-item__button') and ("
                    "contains(., 'PDF Download') or "
                    "contains(., 'Prospekt herunterladen') or "
                    "contains(., 'Télécharger le prospectus') or "
                    "contains(., 'Scarica il volantino') or "
                    "contains(@href, '.pdf') or " # Sadece .pdf içeren linkler
                    "@data-label='Download' or " # data-label="Download" olanlar
                    "contains(@aria-label, 'Download')" # aria-label'ında Download geçenler
                    ")]"
                ))
            )

            pdf_url = pdf_download_link.get_attribute('href')
            print(f"Found PDF download URL: {pdf_url}")
            return pdf_url

        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as e:
            print(f"Error with menu button or PDF download link on preview page (attempting menu click): {e}")
            print("Trying to find a direct PDF download link on the page as a fallback (without menu click)...")
            # Menü butonu bulunamazsa veya tıklanamazsa, doğrudan PDF linkini ara
            try:
                direct_pdf_link_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//a[contains(@href, '.pdf') and ("
                        "contains(., 'PDF Download') or "
                        "contains(., 'Prospekt herunterladen') or "
                        "contains(., 'Télécharger le prospectus') or "
                        "contains(., 'Scarica il volantino') or "
                        "@data-label='Download' or "
                        "contains(@aria-label, 'Download')"
                        ")]"
                    ))
                )
                pdf_url = direct_pdf_link_element.get_attribute('href')
                print(f"Found direct PDF link on page as fallback: {pdf_url}")
                return pdf_url
            except (TimeoutException, NoSuchElementException) as e_fallback:
                print(f"No direct PDF link found as fallback: {e_fallback}")
                print("Could not locate PDF download mechanism for this catalog. You may need to inspect the page manually.")
                return None

    except WebDriverException as e:
        print(f"WebDriver error: {e}")
        print("Please ensure ChromeDriver is installed and its path is correctly configured.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Selenium process: {e}")
        return None
    finally:
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

# *** GÜNCELLENMİŞ download_pdf FONKSİYONU ***
def download_pdf(pdf_url, market_name, lang_code):
    """
    PDF dosyasını indirir. Eğer pdf_url yoksa (Selenium doğrudan indirdiyse),
    temp_pdfs klasöründeki en yeni dosyayı alır.
    """
    filename = f"{market_name}_{lang_code}_catalog_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(PDF_DOWNLOAD_DIR, filename)

    if pdf_url:
        print(f"Downloading PDF from: {pdf_url} to {filepath} using requests...")
        try:
            response = requests.get(pdf_url, stream=True)
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
        # Eğer pdf_url yoksa, Selenium'un indirmeyi başlatmış olabileceği varsayılır.
        # Bu durumda, download.default_directory ayarı sayesinde PDF_DOWNLOAD_DIR'e indirilmiştir.
        print(f"No direct PDF URL provided from Selenium. Checking for downloaded files in {PDF_DOWNLOAD_DIR}...")
        
        # İndirmenin tamamlanması için kısa bir bekleme süresi
        time.sleep(5) 
        
        list_of_files = os.listdir(PDF_DOWNLOAD_DIR)
        
        # Sadece bu işlemden sonra indirilen dosyaları filtrelememiz lazım.
        # Bunu yapmanın en sağlam yolu, her dil için download_pdf'e girmeden önce temp_pdfs'i temizlemektir.
        # Veya dosya adında ilgili market_name ve lang_code içeren bir dosya olup olmadığını kontrol edelim.
        # Ancak Selenium'un indirdiği dosyanın adı her zaman tahmin edilebilir olmayabilir.
        # Bu yüzden en güncel dosya bulma mantığını burada kullanmaya devam edelim, ama dikkatli olalım.
        
        # Yalnızca ".pdf" uzantılı dosyaları al
        pdf_files = [f for f in list_of_files if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF found in {PDF_DOWNLOAD_DIR} after Selenium operation for {market_name} ({lang_code}).")
            return None
        
        # En yeni değiştirilmiş PDF dosyasını bul
        latest_pdf_file = max(pdf_files, key=lambda f: os.path.getmtime(os.path.join(PDF_DOWNLOAD_DIR, f)))
        found_filepath = os.path.join(PDF_DOWNLOAD_DIR, latest_pdf_file)
        
        # Eğer bulunan dosyanın adı beklenenden farklıysa yeniden adlandır
        if os.path.basename(found_filepath) != filename:
            try:
                # Önceki dilden kalan dosyayı sil. Bu sorun oluyordu.
                # Her iterasyon başında temp_pdfs temizlenmeli.
                # Veya, `download_pdf` her çağrıldığında o klasörü temizlesin.
                # Daha iyisi, main fonksiyonunda her yeni dil için işlem yapmadan önce temp_pdfs'i temizlemek.
                # Şimdiki haliyle, main'deki tek temizlik yeterli değil.
                # `temp_pdfs`'i her iterasyon başında temizlemek en güvenli yol.
                
                # Bu durumda, download_pdf'in başına ek bir temizlik ekleyebiliriz,
                # ancak bu, Selenium'un başlatıp henüz bitirmediği indirmeyi silebilir.
                # En mantıklısı, get_latest_pdf_link_selenium fonksiyonunun gerçekten bir URL döndürmesini sağlamak.
                # Eğer döndüremiyorsa, o dil için atlamak.

                # Bu yüzden burada `shutil.move` yerine, sadece `found_filepath`'i döndüreceğiz.
                # Ve ana döngüde `download_pdf` None döndürdüğünde atlayacağız.
                # Bu fonksiyonun görevi ya URL'den indirmek ya da indirilmiş bir dosyayı bulmak.
                print(f"Found recently downloaded PDF: {found_filepath}. Renaming to: {filename}")
                shutil.move(found_filepath, filepath) # Yeniden adlandır
                return filepath
            except Exception as e:
                print(f"Error renaming downloaded PDF: {e}. Returning original path: {found_filepath}")
                return found_filepath
        else:
            print(f"Found recently downloaded PDF: {found_filepath} (already named correctly).")
            return found_filepath

def convert_pdf_to_images(pdf_path, output_image_dir, dpi=200):
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"PDF file not found at {pdf_path}. Cannot convert to images.")
        return []

    print(f"Converting PDF {pdf_path} to images in {output_image_dir}...")
    image_paths = []

    try:
        pdf_document = fitz.open(pdf_path)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            image_filename = f"page_{page_num + 1:02d}.png"
            image_path = os.path.join(output_image_dir, image_filename)
            img.save(image_path)
            
            relative_path_segments = [
                'assets', 'images',
                os.path.basename(os.path.dirname(os.path.dirname(output_image_dir))), # market_name
                os.path.basename(os.path.dirname(output_image_dir)), # lang_code
                os.path.basename(image_path)
            ]
            image_paths.append(os.path.join(*relative_path_segments).replace("\\", "/"))

        print(f"PDF converted. Total {len(image_paths)} images generated in {output_image_dir}.")
        return image_paths

    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []

def update_firestore(market_name, catalog_title, catalog_validity, thumbnail_asset_path, page_image_paths, language):
    brochures_ref = db.collection('brochures')

    print(f"Checking for existing catalogs for {market_name} ({language})...")
    query = brochures_ref.where('marketName', '==', market_name).where('language', '==', language).stream()
    for doc in query:
        print(f"Deleting old catalog: {doc.id} for {market_name} ({language})")
        doc.reference.delete()

    new_catalog_data = {
        'marketName': market_name,
        'title': catalog_title,
        'validity': catalog_validity,
        'thumbnail': thumbnail_asset_path,
        'pages': page_image_paths,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'language': language
    }

    try:
        doc_ref = brochures_ref.add(new_catalog_data)
        print(f"New catalog added to Firestore with ID: {doc_ref[1].id}")
    except Exception as e:
        print(f"Error adding document to Firestore: {e}")

def main():
    # Geçici PDF indirme dizinini BAŞLANGIÇTA bir kez temizle
    if os.path.exists(PDF_DOWNLOAD_DIR):
        try:
            shutil.rmtree(PDF_DOWNLOAD_DIR)
            print(f"Removed existing PDF download directory: {PDF_DOWNLOAD_DIR}")
        except OSError as e:
            print(f"Error removing PDF download directory {PDF_DOWNLOAD_DIR}: {e}")
            print("Please ensure no files are open in this directory and try again.")
            return
    os.makedirs(PDF_DOWNLOAD_DIR)
    print(f"Created PDF download directory: {PDF_DOWNLOAD_DIR}")

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
        print(f"\n--- Processing {market_name.upper()} Catalog ({lang_code.upper()}) ---")

        # Her yeni dil için işlem yapmadan önce indirme klasörünü temizle
        # Bu, bir önceki dilden kalan PDF'in yanlışlıkla işlenmesini önler.
        if os.path.exists(PDF_DOWNLOAD_DIR):
            try:
                for file_name in os.listdir(PDF_DOWNLOAD_DIR):
                    file_path = os.path.join(PDF_DOWNLOAD_DIR, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                print(f"Cleaned up previous PDF files in {PDF_DOWNLOAD_DIR} for new iteration.")
            except OSError as e:
                print(f"Error cleaning up PDF download directory {PDF_DOWNLOAD_DIR} before new iteration: {e}")
                print("Proceeding anyway, but this might cause issues.")


        # 1. En güncel PDF linkini bul (veya indirmeyi tetikle)
        pdf_url_from_selenium = get_latest_pdf_link_selenium(market_name, market_url)

        # 2. PDF'i indir (veya indirilmiş olanı bul)
        downloaded_pdf_path = download_pdf(pdf_url_from_selenium, market_name, lang_code)
        if not downloaded_pdf_path:
            print(f"Could not download or find PDF for {market_name} ({lang_code}). Skipping to next market/language.")
            continue

        # 3. Katalog için assets klasörünü temizle ve PDF'i resimlere dönüştür
        current_catalog_assets_dir = os.path.join(BASE_ASSETS_DIR, market_name, lang_code)

        if os.path.exists(current_catalog_assets_dir):
            try:
                shutil.rmtree(current_catalog_assets_dir)
                print(f"Removed existing directory: {current_catalog_assets_dir}")
            except OSError as e:
                print(f"Error removing directory {current_catalog_assets_dir}: {e}")
                print("Please ensure no files are open in this directory and try again.")
                if os.path.exists(PDF_DOWNLOAD_DIR): shutil.rmtree(PDF_DOWNLOAD_DIR)
                return
        os.makedirs(current_catalog_assets_dir)
        print(f"Created assets directory: {current_catalog_assets_dir}")

        image_asset_paths = convert_pdf_to_images(downloaded_pdf_path, current_catalog_assets_dir)

        if not image_asset_paths:
            print(f"No images were generated from PDF for {market_name} ({lang_code}). Skipping to next market/language.")
            continue

        thumbnail_asset_path = image_asset_paths[0] if image_asset_paths else ''

        # 4. Firestore'u güncelle
        catalog_title = f"{market_name.capitalize()} Weekly Catalog ({language_names.get(lang_code, lang_code.upper())})"
        catalog_validity = f"Valid from {datetime.date.today().strftime('%d.%m.%Y')} - Next Week"

        update_firestore(market_name, catalog_title, catalog_validity, thumbnail_asset_path, image_asset_paths, lang_code)

        print(f"\n--- {market_name.upper()} ({lang_code.upper()}) Automation Completed ---")
        print(f"Catalog images saved to: {current_catalog_assets_dir}")
        print("Firestore updated. Remember to run 'flutter pub get' and update 'pubspec.yaml' for new asset paths.")

    print("\n--- All Catalog Automation Finished ---")
    if os.path.exists(PDF_DOWNLOAD_DIR):
        try:
            shutil.rmtree(PDF_DOWNLOAD_DIR)
            print(f"Cleaned up temporary PDF directory: {PDF_DOWNLOAD_DIR}")
        except OSError as e:
            print(f"Error cleaning up temporary PDF directory {PDF_DOWNLOAD_DIR}: {e}")

if __name__ == "__main__":
    main()