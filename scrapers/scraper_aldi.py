import logging
import time 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Import the shared WebDriver setup function from utils
from .utils import setup_driver

def scrape_aldi_ch(market_name, lang_code, market_url):
    """
    (REVISED FOR STABILITY)
    Scrapes all available weekly catalogs for Aldi Suisse with a more robust wait strategy.
    """
    logging.info(f"Starting Aldi scraper for language: {lang_code}")
    driver = setup_driver()
    found_catalogs = []
    try:
        driver.get(market_url)
        logging.info(f"Navigated to Aldi brochures page: {market_url}")

        # Handle Cookies and Pop-ups
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            logging.info("Accepted Aldi main cookie preferences.")
        except:
            logging.info("Aldi main cookie banner not found or already handled.")
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close-modal"))).click()
            logging.info("Closed promotion pop-up.")
        except:
            logging.info("Promotion pop-up not found or already handled.")

        # --- NEW, MORE STABLE WAIT STRATEGY ---
        try:
            # 1. Wait specifically for the INNER CONTENT (the validity text) to be present.
            # This is much more reliable than waiting for just the outer container.
            logging.info("Waiting for catalog content to fully load...")
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.wrapper .card_leaflet__content p")))
            
            # 2. Add a small, static pause as a final safety net for any slow JS rendering.
            time.sleep(2)
            logging.info("Catalog content loaded.")

        except TimeoutException:
            logging.error("Timeout: The main catalog content did not load in time. The page might be empty or changed.")
            # Close the driver and return an empty list to prevent further errors
            driver.quit()
            return []
        
        # Now that we're sure the content is loaded, we can safely find all elements.
        all_catalog_elements = driver.find_elements(By.CSS_SELECTOR, "article.wrapper")
        logging.info(f"Found {len(all_catalog_elements)} potential Aldi flyers.")

        keyword_map = {
            "de": ["gültig", "woche", "aktionen", "montag", "donnerstag"],
            "fr": ["valables", "semaine", "actions", "lundi", "jeudi"],
            "it": ["valide", "settimana", "azioni", "lunedì", "giovedì"]
        }
        validity_keywords = keyword_map.get(lang_code, [])

        for element in all_catalog_elements:
            try:
                content_element = element.find_element(By.CSS_SELECTOR, ".card_leaflet__content")
                content_text = content_element.text.lower()
                
                if any(keyword in content_text for keyword in validity_keywords):
                    validity_text_element = content_element.find_element(By.CSS_SELECTOR, "p")
                    pdf_url = element.find_element(By.CSS_SELECTOR, "a[href*='s7g10']").get_attribute("href")
                    
                    found_catalogs.append((pdf_url, validity_text_element.text))
                    logging.info(f"Found valid Aldi catalog. Validity: '{validity_text_element.text}'")
            except NoSuchElementException:
                continue

        logging.info(f"Scraping finished. Found a total of {len(found_catalogs)} valid catalogs for Aldi.")
        return found_catalogs
    except Exception as e:
        logging.error(f"An unexpected error occurred during Aldi scrape for {lang_code}: {e}")
        return []
    finally:
        if driver:
            driver.quit()