import logging
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException

# Import the shared WebDriver setup function from utils
from .utils import setup_driver

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