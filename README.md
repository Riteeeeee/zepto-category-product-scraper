# Zepto Category-Wise Product Scraper

Backend Python script that extracts product data from Zepto for a given **Store (Merchant)** and **Location**, iterating through the provided sub-categories and saving a single consolidated `output.json`.

## Test inputs (as per assignment)

- **Store ID**: `5eb1e899-1cb8-4374-a4de-69cf86cc36cc`
- **Location**: Lat `17.32310`, Lon `78.46610`
- **SubCategories**:
  - `catId`: `f1316a4d-01fe-4653-aeb0-c7406ed0ae10`, `subCatId`: `18122408-ce1e-424a-b5a7-336f55659717`
  - `catId`: `947a72ae-b371-45cb-ad3a-778c05b64399`, `subCatId`: `dff3658b-c351-4e7f-8196-e98d0c66d99e`
  - `catId`: `fd1438dc-e1a8-49f9-87a3-2645a613ceeb`, `subCatId`: `9cd558a2-5ef6-45e9-8198-c06b83d42377`

These are already wired into `scraper.py` as constants (`STORE_ID`, `LAT/LON`, `SUBCATEGORIES`) for easy testing.

## Setup

```bash
cd nitro_assignment/zepto_scraper
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python scraper.py
```

On success it writes `output.json` in the same folder.

## Approach (Automation + Anti-bot)

The script calls Zepto’s internal BFF endpoint (`/lms/api/v2/get_page`) using `requests` while mimicking a browser request via headers such as:

- `user-agent`
- `platform`, `tenant`
- `store_id` / `x-store-id`

If the API starts returning **401/403** or **empty products**, Zepto likely requires fresher session headers. You can optionally populate these in `HEADERS`:

- `cookie` (e.g. `accessToken=...`)
- `x-xsrf-token`
- `request-signature`

## Pagination (high volume subcategories)

Zepto uses cursor-style “infinite feed” pagination. For each subcategory, the script:

- Extracts product nodes via a **recursive JSON traversal** (`extract_product_nodes`) to avoid brittle hardcoded paths.
- Reads `nextPageParams` and feeds back `page_number`, `atlas_offset`, and `infinite_feed_widget_id` until no more pages are available.
- Uses a `seen_product_ids` set to dedupe and stop safely if a page repeats items (prevents loops).

## Rate limiting / politeness

Between page requests the script sleeps (`time.sleep(1.2)`) to reduce the chance of HTTP 429 / throttling. This can be tuned up/down depending on stability.

## Output (single structured JSON)

`output.json` is one consolidated JSON object:

- `store_id`
- `location`
- `categories[]` where each element contains:
  - `category_id`
  - `subcategory_id`
  - `products[]` with:
    - `Product Name`
    - `Price`
    - `Discounted Price`
    - `Image URL`
