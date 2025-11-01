"""
Pytest fixtures and test configuration.
"""

import pytest
from unittest.mock import Mock
from app.adapters.base import Product
from app.adapters.prestashop import PrestaShopAdapter
from app.clients.klaviyo_client import KlaviyoClient
from app.services.similar_products_service import SimilarProductsService


@pytest.fixture
def mock_ecommerce_adapter():
    """Mock e-commerce adapter."""
    return Mock(spec=PrestaShopAdapter)


@pytest.fixture
def mock_klaviyo_client():
    """Mock Klaviyo client."""
    return Mock(spec=KlaviyoClient)


@pytest.fixture
def similar_products_service(mock_ecommerce_adapter, mock_klaviyo_client):
    """Similar products service with mocked dependencies."""
    return SimilarProductsService(
        mock_ecommerce_adapter,
        mock_klaviyo_client,
        limit=6
    )


@pytest.fixture
def sample_product():
    """Sample product for testing."""
    return Product(
        id="4422",
        name="Gluten-Free Cookie Mix",
        category_id="5",
        quantity=0
    )


@pytest.fixture
def sample_products():
    """Sample list of products for testing."""
    return [
        Product(id="1", name="Gluten-Free Cookie Mix", category_id="5", quantity=10),
        Product(id="2", name="Gluten-Free Cake Mix", category_id="5", quantity=5),
        Product(id="3", name="Sugar Cookie Mix", category_id="5", quantity=3),
        Product(id="4", name="Chocolate Cake Mix", category_id="5", quantity=15),
    ]
