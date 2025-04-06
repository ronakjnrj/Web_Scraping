import os
import csv
from bs4 import BeautifulSoup

# Directory where scraped HTML files are stored
data_dir = "data"
output_file = "scraped_data.csv"

# Ensure data directory exists
if not os.path.exists(data_dir):
    print("Data directory not found!")
    exit()

# Open CSV file for writing
with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["title", "price", "link"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Loop through all saved HTML files
    for filename in os.listdir(data_dir):
        if filename.endswith(".html"):
            file_path = os.path.join(data_dir, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

                # Extract product title
                title_tag = soup.find("h2", class_="a-size-medium")
                title = title_tag.text.strip() if title_tag else "N/A"

                # Extract product price
                price_tag = soup.find("span", class_="a-price-whole")
                price = price_tag.text.strip() if price_tag else "N/A"

                # Extract product link
                link_tag = soup.find("a", class_="a-link-normal")
                link = f"https://www.amazon.in{link_tag['href']}" if link_tag else "N/A"

                # Write to CSV
                writer.writerow({
                    "Name": title,
                    "Price": price,
                    "Link": link
                })

print(f"CSV file created successfully: {output_file}")
