from dotenv import load_dotenv
load_dotenv()

import logging
from extract import extract

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

if __name__ == "__main__":
    raw_path, source = extract()
    print(f"Done. Data saved to {raw_path} (source: {source})")
