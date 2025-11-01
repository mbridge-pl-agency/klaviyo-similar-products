"""
PrestaShop 1.7+ WebService API adapter.

NOTE: This adapter is tested with PrestaShop 1.7.x WebService API.
      Newer versions (1.8+, 8.x) may have different API structures.
"""

import requests
from typing import List, Optional
from app.adapters.base import EcommerceAdapter, Product, EcommerceAPIError


class PrestaShopAdapter(EcommerceAdapter):
    """
    PrestaShop 1.7+ WebService adapter implementation.

    Tested with PrestaShop 1.7.x API. Newer versions may require adjustments.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        """
        Initialize PrestaShop adapter.

        Args:
            base_url: PrestaShop store URL (e.g., https://your-store.com)
            api_key: PrestaShop WebService API key
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

        # Use Session for connection pooling (reuses TCP connections)
        # Speeds up batch requests in get_products_by_category() by ~50-200ms
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Klaviyo-PrestaShop-Similar-Products/1.0'
        })

    def get_product(self, product_id: str) -> Optional[Product]:
        """
        Fetch product from PrestaShop.

        GET /api/products/{id}?output_format=JSON&display=full

        Args:
            product_id: PrestaShop product ID

        Returns:
            Product object or None if not found

        Raises:
            EcommerceAPIError: If API request fails
        """
        try:
            url = f"{self.base_url}/api/products/{product_id}"
            params = {
                "ws_key": self.api_key,
                "output_format": "JSON",
                "display": "full"
            }

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            # PrestaShop API can return either {"product": {...}} or {"products": [{...}]}
            # depending on authentication method and parameters
            if 'product' in data:
                return self._parse_product(data['product'])
            elif 'products' in data and isinstance(data['products'], list) and len(data['products']) > 0:
                return self._parse_product(data['products'][0])
            else:
                return None

        except requests.RequestException as e:
            raise EcommerceAPIError(f"PrestaShop API error: {str(e)}")

    def get_products_by_category(
        self,
        category_id: str,
        limit: int = 50
    ) -> List[Product]:
        """
        Fetch products from category using batch fetching for performance.

        Strategy:
        1. GET /api/products?filter[id_category_default]=[{id}] → get list of IDs
        2. GET /api/products?filter[id]=[ID1|ID2|ID3...] → batch fetch product data
        3. GET /api/stock_availables?filter[id_product]=[ID1|ID2|...] → batch fetch stock

        Note: PrestaShop may have stock in separate endpoint if disabled in products.

        Args:
            category_id: PrestaShop category ID
            limit: Maximum number of products to return

        Returns:
            List of Product objects

        Raises:
            EcommerceAPIError: If API request fails
        """
        try:
            # Step 1: Get product IDs from category
            url = f"{self.base_url}/api/products"
            params = {
                "ws_key": self.api_key,
                "output_format": "JSON",
                "filter[id_category_default]": f"[{category_id}]",
                "limit": limit
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Extract product IDs
            product_ids = []
            for item in data.get('products', []):
                if isinstance(item, dict) and 'id' in item:
                    product_ids.append(str(item['id']))

            if not product_ids:
                return []

            # Step 2: Batch fetch product data
            ids_filter = "|".join(product_ids)

            params = {
                "ws_key": self.api_key,
                "output_format": "JSON",
                "filter[id]": f"[{ids_filter}]",
                # Only fetch fields we need (reduces bandwidth)
                "display": "[id,name,id_category_default,price,manufacturer_name]"
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse products (without quantity yet)
            products_dict = {}
            for product_data in data.get('products', []):
                try:
                    product = self._parse_product(product_data)
                    if product:
                        products_dict[product.id] = product
                except Exception:
                    continue

            # Step 3: Batch fetch stock quantities from stock_availables
            stock_url = f"{self.base_url}/api/stock_availables"
            params = {
                "ws_key": self.api_key,
                "output_format": "JSON",
                "filter[id_product]": f"[{ids_filter}]",
                "display": "[id_product,quantity]"
            }

            response = self.session.get(stock_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            stock_data = response.json()

            # Update products with stock quantities
            for stock_item in stock_data.get('stock_availables', []):
                product_id = str(stock_item.get('id_product', ''))
                if product_id in products_dict:
                    try:
                        quantity = int(stock_item.get('quantity', 0))
                        products_dict[product_id].quantity = quantity
                    except (ValueError, TypeError):
                        pass

            return list(products_dict.values())

        except requests.RequestException as e:
            raise EcommerceAPIError(f"PrestaShop API error: {str(e)}")

    def health_check(self) -> bool:
        """
        Test PrestaShop API connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api"
            response = self.session.head(url, timeout=5)
            # 200 = OK, 401 = API exists but requires auth (expected for HEAD)
            return response.status_code in [200, 401]
        except Exception:
            return False

    def _parse_product(self, data: dict) -> Optional[Product]:
        """
        Parse PrestaShop product response into universal Product.

        Handles multi-language fields and varying response structures.

        Args:
            data: Product data from PrestaShop API

        Returns:
            Product object or None if parsing fails
        """
        if not data:
            return None

        try:
            # Extract product ID
            product_id = str(data.get('id', ''))

            # Extract names (multi-language support)
            name_primary = self._extract_multilang_field(data.get('name', ''), lang_id='1')
            name_secondary = self._extract_multilang_field(data.get('name', ''), lang_id='2')

            # Use primary if available, fallback to any name
            if not name_primary:
                name_primary = self._extract_multilang_field(data.get('name', ''))

            # Extract category (prefer id_category_default)
            category_id = str(data.get('id_category_default', ''))

            # Extract quantity (direct field or from associations)
            quantity = 0
            if 'associations' in data and 'stock_availables' in data['associations']:
                stock_data = data['associations']['stock_availables']
                if isinstance(stock_data, list) and len(stock_data) > 0:
                    quantity = int(stock_data[0].get('quantity', 0))
            elif 'quantity' in data:
                quantity = int(data.get('quantity', 0))

            # Extract price
            price = None
            if 'price' in data:
                try:
                    price = float(data.get('price', 0))
                except (ValueError, TypeError):
                    price = None

            # Extract manufacturer
            manufacturer_name = data.get('manufacturer_name', None)

            if not product_id or not name_primary:
                return None

            return Product(
                id=product_id,
                name=name_primary,
                name_secondary=name_secondary if name_secondary else None,
                category_id=category_id,
                quantity=quantity,
                price=price,
                manufacturer_name=manufacturer_name
            )

        except Exception:
            return None

    def _extract_multilang_field(self, field, lang_id: str = None) -> str:
        """
        Extract value from PrestaShop multi-language field.

        Input can be:
        - String: "Product Name"
        - Array: [{"id": "1", "value": "Polish"}, {"id": "2", "value": "English"}]
        - Dict: {"language": [...], "value": "Product Name"}

        Args:
            field: Multi-language field from PrestaShop
            lang_id: Specific language ID to extract (e.g., '1' for Polish, '2' for English)
                    If None, takes first available language.

        Returns:
            Extracted string value
        """
        if isinstance(field, str):
            return field

        if isinstance(field, list) and len(field) > 0:
            # If specific language requested
            if lang_id:
                for item in field:
                    if isinstance(item, dict) and item.get('id') == lang_id:
                        return item.get('value', '')

            # Fallback: take first language entry
            if isinstance(field[0], dict):
                return field[0].get('value', '')

        if isinstance(field, dict):
            return field.get('value', '')

        return ''
