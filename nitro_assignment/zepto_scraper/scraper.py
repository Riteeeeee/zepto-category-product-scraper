import requests
import json
import time

STORE_ID = "5eb1e899-1cb8-4374-a4de-69cf86cc36cc"
LAT, LON = 17.32310, 78.46610
API_URL = "https://bff-gateway.zepto.com/lms/api/v2/get_page"
OUTPUT_FILE = "output.json"

SUBCATEGORIES = [
    {"catId": "f1316a4d-01fe-4653-aeb0-c7406ed0ae10", "subCatId": "18122408-ce1e-424a-b5a7-336f55659717"},
    {"catId": "947a72ae-b371-45cb-ad3a-778c05b64399", "subCatId": "dff3658b-c351-4e7f-8196-e98d0c66d99e"},
    {"catId": "fd1438dc-e1a8-49f9-87a3-2645a613ceeb", "subCatId": "9cd558a2-5ef6-45e9-8198-c06b83d42377"}
]

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "app_sub_platform": "WEB",
    "platform": "WEB",
    "tenant": "ZEPTO",
    "device_id": "1824cfca-7cd5-4019-a322-cc12cb5370cc",
    "store_id": STORE_ID,
    "x-store-id": STORE_ID,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "app_version": "14.28.1",

    # ==========================================================================
    # AUTHENTICATION OVERRIDE (Optional)
    # --------------------------------------------------------------------------
    # For full inventory access, provide fresh tokens below.
    # ==========================================================================
    # "auth_from_cookie": "true",
    # "cookie": "accessToken=REPLACE_WITH_YOUR_TOKEN;", 
    # "request-signature": "REPLACE_WITH_YOUR_SIGNATURE",
    # "x-xsrf-token": "REPLACE_WITH_YOUR_XSRF"
    
}

def extract_product_nodes(node, items_list):
    """Recursively traverses the JSON tree to find product objects."""
    if isinstance(node, dict):
        if "product" in node and "productVariant" in node:
            items_list.append(node)
        for key, value in node.items():
            extract_product_nodes(value, items_list)
    elif isinstance(node, list):
        for item in node:
            extract_product_nodes(item, items_list)

def fetch_subcategory_products(cat_id, sub_id):
    all_items = []
    seen_product_ids = set()
    page_number = 1
    atlas_offset = 0
    infinite_feed_widget_id = None

    while True:
        payload = {
            "page_type": "SUBCATEGORY",
            "version": "v2",
            "latitude": LAT,
            "longitude": LON,
            "category_id": cat_id,
            "subcategory_id": sub_id,
            "page_identifier": "browse_category_product",
            "page_number": page_number,
            "page_size": 10,
            "disable_labs": True,
            "is_continuous_load": page_number > 1
        }
        
        if page_number > 1:
            payload["atlas_offset"] = atlas_offset
            if infinite_feed_widget_id:
                payload["infinite_feed_widget_id"] = infinite_feed_widget_id
                payload["last_widget_id"] = infinite_feed_widget_id

        print(f"  -> Fetching SubCat {sub_id} | Page {page_number}...")
        
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
            if response.status_code != 200:
                break
                
            data = response.json()
            raw_items = []
            extract_product_nodes(data, raw_items)
            
            if not raw_items:
                break

            new_items_found = 0
            for item in raw_items:
                prod = item.get("product", {})
                variant = item.get("productVariant", {})
                
                p_id = variant.get("id") or prod.get("name")
                
                if p_id and p_id not in seen_product_ids:
                    seen_product_ids.add(p_id)
                    new_items_found += 1
                    
                    raw_img_path = variant.get("images", [{}])[0].get("path") if variant.get("images") else None
                    final_img_url = f"https://cdn.zeptonow.com/{raw_img_path}" if raw_img_path else None

                    all_items.append({
                        "Product Name": prod.get("name"),
                        "Price": variant.get("mrp", 0) / 100, 
                        "Discounted Price": item.get("sellingPrice", variant.get("mrp", 0)) / 100,
                        "Image URL": final_img_url
                    })

            if new_items_found == 0:
                print(f"    [!] No new products on page {page_number}. Stopping to avoid loop.")
                break

            next_params = data.get("nextPageParams") or data.get("next_page_params")
            if not next_params:
                break
                
            page_number = next_params.get("page_number", page_number + 1)
            atlas_offset = next_params.get("atlas_offset", atlas_offset)
            infinite_feed_widget_id = next_params.get("infinite_feed_widget_id")
            
            time.sleep(1.2) 

        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"Completed SubCat {sub_id}. Total unique products: {len(all_items)}\n")
    return all_items

def main():
    final_catalog = []
    
    for sc in SUBCATEGORIES:
        products = fetch_subcategory_products(sc['catId'], sc['subCatId'])
        final_catalog.append({
            "category_id": sc["catId"],
            "subcategory_id": sc["subCatId"],
            "products": products
        })
        
    if final_catalog:
        total_products = sum(len(c.get("products", [])) for c in final_catalog)
        output = {
            "store_id": STORE_ID,
            "location": {
                "latitude": LAT,
                "longitude": LON
            },
            "categories": final_catalog
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4)
        print(
            f"Success! Saved {total_products} products across {len(final_catalog)} subcategories to {OUTPUT_FILE}"
        )
    else:
        print("No products found. Please verify the Store ID coordinates and refresh auth headers.")

if __name__ == "__main__":
    main()