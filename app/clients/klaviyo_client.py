"""
Klaviyo REST API client.
"""

import requests
from typing import Optional, List


class KlaviyoAPIError(Exception):
    """Klaviyo API error."""
    pass


class KlaviyoClient:
    """Klaviyo REST API client with array of objects support."""

    BASE_URL = "https://a.klaviyo.com/api"

    def __init__(self, api_key: str, revision: str = "2024-10-15", timeout: int = 10):
        """
        Initialize Klaviyo client.

        Args:
            api_key: Klaviyo private API key (pk_xxx)
            revision: API revision date
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.revision = revision
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "revision": revision
        })

    def get_profile_id_by_email(self, email: str) -> Optional[str]:
        """
        Find profile ID by email address.

        GET /profiles/?filter=equals(email,"{email}")

        Args:
            email: User email address

        Returns:
            Profile ID or None if not found

        Raises:
            KlaviyoAPIError: If API request fails
        """
        try:
            url = f"{self.BASE_URL}/profiles/"
            params = {"filter": f'equals(email,"{email}")'}

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                return data['data'][0]['id']

            return None

        except requests.RequestException as e:
            raise KlaviyoAPIError(f"Failed to get profile: {str(e)}")

    def update_profile_properties(
        self,
        profile_id: str,
        properties: dict
    ) -> bool:
        """
        Update profile custom properties.

        PATCH /profiles/{profile_id}/

        Args:
            profile_id: Klaviyo profile ID
            properties: Dictionary of properties to update

        Returns:
            True if successful

        Raises:
            KlaviyoAPIError: If API request fails
        """
        try:
            url = f"{self.BASE_URL}/profiles/{profile_id}/"
            payload = {
                "data": {
                    "type": "profile",
                    "id": profile_id,
                    "attributes": {
                        "properties": properties
                    }
                }
            }

            response = self.session.patch(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            return True

        except requests.RequestException as e:
            raise KlaviyoAPIError(f"Failed to update profile: {str(e)}")

    def add_similar_products(
        self,
        email: str,
        product_id: str,
        similar_product_ids: List[str],
        enriched_at: str
    ) -> bool:
        """
        Add similar products to profile using array of objects structure.

        Handles multiple product subscriptions correctly by maintaining
        separate entries for each product.

        Structure:
        {
          "bis_similar_products": [
            {
              "product_id": "4422",
              "similar_ids": ["15655", "11773", ...],
              "enriched_at": "2025-10-30T12:34:56Z"
            },
            ...
          ]
        }

        Args:
            email: User email
            product_id: Product user subscribed to
            similar_product_ids: List of similar product IDs
            enriched_at: ISO timestamp

        Returns:
            True if successful

        Raises:
            KlaviyoAPIError: If profile not found or update fails
        """
        profile_id = self.get_profile_id_by_email(email)
        if not profile_id:
            raise KlaviyoAPIError(f"Profile not found for email: {email}")

        # Get existing similar products array
        existing_array = self._get_similar_products_array(profile_id)

        # Remove old entry for same product_id if exists
        existing_array = [
            item for item in existing_array
            if item.get('product_id') != product_id
        ]

        # Add new entry
        new_entry = {
            "product_id": product_id,
            "similar_ids": similar_product_ids,
            "enriched_at": enriched_at
        }
        existing_array.append(new_entry)

        # Update profile
        return self.update_profile_properties(profile_id, {
            "bis_similar_products": existing_array
        })

    def remove_similar_products(
        self,
        email: str,
        product_id: Optional[str] = None
    ) -> bool:
        """
        Remove similar products from profile.

        Args:
            email: User email
            product_id: If provided, remove only this product's data.
                       If None, remove entire array.

        Returns:
            True if successful
        """
        profile_id = self.get_profile_id_by_email(email)
        if not profile_id:
            return False

        if product_id is None:
            # Remove entire array
            return self.update_profile_properties(profile_id, {
                "bis_similar_products": None
            })
        else:
            # Remove specific product entry
            existing_array = self._get_similar_products_array(profile_id)
            filtered_array = [
                item for item in existing_array
                if item.get('product_id') != product_id
            ]

            if len(filtered_array) == 0:
                # If array empty, set to None
                return self.update_profile_properties(profile_id, {
                    "bis_similar_products": None
                })
            else:
                return self.update_profile_properties(profile_id, {
                    "bis_similar_products": filtered_array
                })

    def _get_similar_products_array(self, profile_id: str) -> List[dict]:
        """
        Get existing bis_similar_products array from profile.

        Fetches current profile data to properly merge multiple subscriptions.

        Args:
            profile_id: Klaviyo profile ID

        Returns:
            List of existing similar product entries
        """
        try:
            url = f"{self.BASE_URL}/profiles/{profile_id}/"
            params = {
                "additional-fields[profile]": "properties"
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            properties = data.get('data', {}).get('attributes', {}).get('properties', {})
            existing = properties.get('bis_similar_products', [])

            # Ensure it's a list
            if isinstance(existing, list):
                return existing
            return []

        except Exception:
            # If GET fails, return empty array (fail gracefully)
            return []
