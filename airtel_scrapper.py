from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
import logging

# --- Setup logging ---
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_rendered_html(url, timeout=15):
    """Fetch the fully rendered HTML from a dynamic website using Selenium."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    logging.info("Launching headless browser...")
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # Wait until tab content is present
        logging.info("Waiting for content to load...")
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".tabs-single-content"))
        )
        html = driver.page_source
    except Exception as e:
        logging.error(f"Failed to load content: {e}")
        html = ""
    finally:
        driver.quit()
        logging.info("Browser closed.")

    return html

def parse_plans(html):
    """Parse the HTML content to extract recharge plan details."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".recharge-online-container .tabs-container .tabs-content")

    if not container:
        logging.warning("Could not locate the tabs content.")
        return []

    plans = []

    for tab in container.select(".tabs-single-content"):
        category = tab.get("data-tab-name", "Unknown")
        for pack in tab.select(".pack-card-container"):
            details = pack.select(".pack-card-detail")
            if len(details) < 3:
                continue

            try:
                plan_name = details[0].select_one(".pack-card-heading").get_text(strip=True)
                price = plan_name
                data_amt = details[1].select_one(".pack-card-heading").get_text(strip=True)
                data_unit_elem = details[1].select_one(".pack-card-sub-heading")
                data_unit = data_unit_elem.get_text(strip=True) if data_unit_elem else ""
                validity = details[2].select_one(".pack-card-heading").get_text(strip=True)
                benefits = [b.get_text(strip=True) for b in pack.select(".pack-card-benefit label")]

                plans.append({
                    "Category": category,
                    "Plan Name": plan_name,
                    "Price": price,
                    "Data": f"{data_amt} {data_unit}".strip(),
                    "Validity": validity,
                    "Additional Benefits": "; ".join(benefits)
                })
            except Exception as e:
                logging.warning(f"Error parsing a plan card: {e}")
                continue

    return plans

def save_to_csv(plans, filename="airtel_plans.csv"):
    """Save the extracted plans to a CSV file."""
    if not plans:
        logging.warning("No plans available to save.")
        return

    try:
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=plans[0].keys())
            writer.writeheader()
            writer.writerows(plans)
        logging.info(f"{len(plans)} plans saved to '{filename}'.")
    except Exception as e:
        logging.error(f"Failed to save CSV: {e}")

def main():
    url = "https://www.airtel.in/recharge-online?icid=header"
    logging.info("Fetching Airtel recharge plans...")
    html = get_rendered_html(url)

    if not html:
        logging.error("No HTML content retrieved. Exiting.")
        return

    logging.info("Parsing recharge plans...")
    plans = parse_plans(html)
    save_to_csv(plans)

if __name__ == "__main__":
    main()
