import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize WebDriver (Ensure Edge WebDriver is installed)
driver = webdriver.Edge()

# Search Query
query = "mouse"
driver.get(f"https://www.amazon.in/s?k={query}")

# Wait until elements are loaded
wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
products = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "puis-card-container")))

print(f"{len(products)} items found")

# Ensure "data" directory exists
os.makedirs("data", exist_ok=True)

# Loop through each product and save the HTML
for file, product in enumerate(products):
    html_content = product.get_attribute("outerHTML")
    
    # Save to file
    with open(f"data/{query}_{file}.html", "w", encoding="utf-8") as f:
        f.write(html_content)

print("Scraping completed. Data saved!")

# Close browser
driver.quit()
