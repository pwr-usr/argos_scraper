# ==============================================================================
# Argos JSON Parser to CSV for Google Colab
# ==============================================================================
#
# Description:
# This script reads all the .json files from the 'scraped_data' directory,
# extracts specific product details, and saves them into a single CSV file.
# It is designed to be run in the same Google Colab environment after the
# 'argos_scraper_colab' script has been executed.
#
# How it works:
# 1. Scans the 'scraped_data' directory for all files ending with .json.
# 2. Iterates through each JSON file and loads its content.
# 3. For each product, it extracts the required fields, handling cases where
#    optional data (like a 'was' price) might be missing.
# 4. It constructs the full product URL using the 'partNumber'.
# 5. All the extracted data is collected into a list.
# 6. This list is converted into a Pandas DataFrame for easy handling.
# 7. The DataFrame is saved to 'argos_products.csv'.
#
# Instructions for Google Colab:
# 1. Make sure you have already run the 'argos_scraper_colab' script and that
#    the 'scraped_data' directory with your .json files exists.
# 2. Paste this entire script into a new cell in your Colab notebook.
# 3. Run the cell.
# 4. A file named `argos_products.csv` will be created in the file explorer,
#    containing all the parsed data.
#
# ==============================================================================

import os
import json
import pandas as pd
from datetime import date

# --- Configuration ---
INPUT_DIRECTORY = 'scraped_products'
OUTPUT_CSV_FILE = 'output.csv'


def parse_json_file(file_path, file_name):
    """
    Opens and parses a single JSON file to extract product information.

    Args:
        file_path (str): The full path to the JSON file.
        file_name (str): The name of the JSON file (used to extract search term).

    Returns:
        dict: A dictionary containing the extracted product details, or None on failure.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Navigate to the main product data sections
        product_store = data.get('productStore', {})
        store_data = product_store.get('data', {})
        attributes = store_data.get('attributes', {})

        # The 'prices' object is inside 'store_data' (productStore -> data)
        prices_data = store_data.get('prices', {})
        prices = prices_data.get('attributes', {})
        delivery = prices.get('delivery', {})

        # Extract search term from filename (remove .json extension and convert _ to /)
        search_term = file_name.replace('.json', '').replace('_', '/')

        # --- Data Extraction ---
        part_number = attributes.get('partNumber')

        product_details = {
            'searchTerm': search_term,
            'timestamp': date.today().isoformat(),
            'productName': store_data.get('productName'),
            'description': attributes.get('description'),
            'partNumber': part_number,
            'price_now': prices.get('now'),
            'price_was': prices.get('was'),
            'flashText': prices.get('flashText'),
            'freeDelivery': delivery.get('freeDelivery'),
            'variableDeliveryPrice': delivery.get('variableDeliveryPrice'),
            'deliveryPrice': delivery.get('deliveryPrice'),
            'url': f"https://www.argos.co.uk/product/{part_number}" if part_number else None
        }

        return product_details

    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from file: {file_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while processing {file_path}: {e}")
        return None


def main():
    """
    Main function to find JSON files, parse them, and save to a CSV.
    """
    print("--- Starting JSON to CSV parsing process ---")

    if not os.path.exists(INPUT_DIRECTORY):
        print(f"Error: Input directory '{INPUT_DIRECTORY}' not found.")
        print("Please run the scraping script first to generate the JSON files.")
        return

    # Find all files in the directory that end with .json
    json_files = [f for f in os.listdir(INPUT_DIRECTORY) if f.endswith('.json')]

    if not json_files:
        print(f"No .json files found in the '{INPUT_DIRECTORY}' directory.")
        return

    print(f"Found {len(json_files)} JSON files to process.")

    all_products_data = []

    # Loop through each file path and parse the data
    for file_name in json_files:
        file_path = os.path.join(INPUT_DIRECTORY, file_name)
        extracted_data = parse_json_file(file_path, file_name)

        if extracted_data:
            all_products_data.append(extracted_data)

    if not all_products_data:
        print("No data was successfully extracted. The CSV file will not be created.")
        return

    # Convert the list of dictionaries to a Pandas DataFrame
    df = pd.DataFrame(all_products_data)

    # Reorder columns to ensure searchTerm is first
    column_order = ['searchTerm', 'timestamp', 'productName', 'description',
                    'partNumber', 'price_now', 'price_was', 'flashText',
                    'freeDelivery', 'variableDeliveryPrice', 'deliveryPrice', 'url']

    # Only include columns that exist in the dataframe
    df = df[[col for col in column_order if col in df.columns]]

    # Save the DataFrame to a CSV file
    try:
        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8')
        print(f"\nSuccessfully created CSV file: '{OUTPUT_CSV_FILE}'")
        print(f"It contains data for {len(df)} products.")
    except Exception as e:
        print(f"\nAn error occurred while saving the CSV file: {e}")

    print("\n--- Parsing process finished ---")


if __name__ == "__main__":
    main()