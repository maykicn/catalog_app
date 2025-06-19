# scrapers/scraper_aldi.py

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Import the shared WebDriver setup function from utils
from .utils import setup_driver

def scrape_aldi_ch(market_name, lang_code, market_url):
    """
    (REVISED LOGIC)
    Scrapes all available weekly catalogs for Aldi Suisse with a more robust filter.
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

        # --- NEW: More flexible keywords for each language ---
        keyword_map = {
            "de": ["gültig", "woche", "aktionen", "montag", "donnerstag"], # "week", "promotions", "monday", "thursday"
            "fr": ["valables", "semaine", "actions", "lundi", "jeudi"],   # "week", "actions", "monday", "thursday"
            "it": ["valide", "settimana", "azioni", "lunedì", "giovedì"]   # "week", "actions", "monday", "thursday"
        }
        validity_keywords = keyword_map.get(lang_code, [])

        for element in all_catalog_elements:
            try:
                # Find the container for the text content
                content_element = element.find_element(By.CSS_SELECTOR, ".card_leaflet__content")
                content_text = content_element.text.lower()
                
                # Check if any of the new keywords are in the flyer's text
                if any(keyword in content_text for keyword in validity_keywords):
                    # If it's a valid weekly flyer, get the precise validity text and URL
                    validity_text_element = content_element.find_element(By.CSS_SELECTOR, "p")
                    pdf_url = element.find_element(By.CSS_SELECTOR, "a[href*='s7g10']").get_attribute("href")
                    
                    found_catalogs.append((pdf_url, validity_text_element.text))
                    logging.info(f"Found valid Aldi catalog. Validity: '{validity_text_element.text}'")
            except NoSuchElementException:
                # This flyer might not have the expected text structure, just skip it.
                continue

        logging.info(f"Scraping finished. Found a total of {len(found_catalogs)} valid catalogs for Aldi.")
        return found_catalogs
    except Exception as e:
        logging.error(f"An error occurred during Aldi scrape for {lang_code}: {e}")
        return []
    finally:
        if driver:
            driver.quit()