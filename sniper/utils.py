import re

BULK_RE = re.compile(r'data\-product\-id="(\d+)".+?data\-expected\-price="(\d+)".+?data\-expected\-seller-id="(\d+)".+?data\-lowest\-private\-sale\-userasset\-id="(\d+)"', re.DOTALL)

def parse_item_page(data):
    match = BULK_RE.search(data)
    product_id = int(match.group(1))
    price = int(match.group(2))
    seller_id = int(match.group(3))
    userasset_id = int(match.group(4))
    return product_id, price, seller_id, userasset_id