"""
Abstract base classes for e-commerce platform adapters.

Uses Adapter Pattern to allow future integration with multiple platforms
(PrestaShop, WooCommerce, Shopify, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Product:
    """
    Universal product representation across all e-commerce platforms.

    Contains fields required for intelligent similarity matching.
    Full product data (images, URLs) retrieved from Klaviyo Catalog.
    """

    id: str
    name: str  # Primary name (first language)
    category_id: str
    quantity: int = 0

    # Enhanced similarity matching fields
    price: Optional[float] = None
    manufacturer_name: Optional[str] = None
    name_secondary: Optional[str] = None  # Second language name (if available)
    sku: Optional[str] = None


class EcommerceAdapter(ABC):
    """Abstract base class for e-commerce platform adapters."""

    @abstractmethod
    def get_product(self, product_id: str) -> Optional[Product]:
        """
        Retrieve single product by ID.

        Args:
            product_id: Platform-specific product identifier

        Returns:
            Product object or None if not found

        Raises:
            EcommerceAPIError: If API request fails
        """
        pass

    @abstractmethod
    def get_products_by_category(
        self,
        category_id: str,
        limit: int = 50
    ) -> List[Product]:
        """
        Retrieve products from specific category.

        Args:
            category_id: Platform-specific category identifier
            limit: Maximum number of products to return

        Returns:
            List of Product objects

        Raises:
            EcommerceAPIError: If API request fails
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify API connection and credentials.

        Returns:
            True if connection successful, False otherwise
        """
        pass


class EcommerceAPIError(Exception):
    """Base exception for e-commerce API errors."""
    pass
