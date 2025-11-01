"""
Tests for similar products service.
"""

from app.adapters.base import Product


def test_find_similar_products(similar_products_service, mock_ecommerce_adapter, sample_product, sample_products):
    """Test finding similar products."""
    # Mock adapter to return sample products
    mock_ecommerce_adapter.get_products_by_category.return_value = sample_products

    # Find similar products
    result = similar_products_service.find_similar_products(sample_product)

    # Should return list of IDs
    assert isinstance(result, list)
    assert all(isinstance(id, str) for id in result)

    # Should not include original product
    assert sample_product.id not in result

    # Should be limited to service.limit
    assert len(result) <= similar_products_service.limit


def test_find_similar_products_filters_out_of_stock(similar_products_service, mock_ecommerce_adapter, sample_product):
    """Test that out of stock products are filtered."""
    products = [
        Product(id="1", name="Similar Product 1", category_id="5", quantity=0),  # Out of stock
        Product(id="2", name="Similar Product 2", category_id="5", quantity=5),  # In stock
    ]
    mock_ecommerce_adapter.get_products_by_category.return_value = products

    result = similar_products_service.find_similar_products(sample_product)

    # Should only include in-stock product
    assert "1" not in result
    assert "2" in result


def test_find_similar_products_empty_category(similar_products_service, mock_ecommerce_adapter, sample_product):
    """Test handling of empty category."""
    mock_ecommerce_adapter.get_products_by_category.return_value = []

    result = similar_products_service.find_similar_products(sample_product)

    assert result == []


def test_enrich_profile_success(similar_products_service, mock_ecommerce_adapter, mock_klaviyo_client, sample_product):
    """Test successful profile enrichment."""
    # Mock getting product
    mock_ecommerce_adapter.get_product.return_value = sample_product

    # Mock finding similar products
    mock_ecommerce_adapter.get_products_by_category.return_value = [
        Product(id="1", name="Similar 1", category_id="5", quantity=10),
        Product(id="2", name="Similar 2", category_id="5", quantity=5),
    ]

    # Mock Klaviyo update
    mock_klaviyo_client.add_similar_products.return_value = True

    result = similar_products_service.enrich_profile("test@example.com", "4422")

    assert result['success'] is True
    assert result['similar_count'] > 0
    assert result['error'] is None

    # Verify Klaviyo was called
    mock_klaviyo_client.add_similar_products.assert_called_once()


def test_enrich_profile_product_not_found(similar_products_service, mock_ecommerce_adapter):
    """Test enrichment when product not found."""
    mock_ecommerce_adapter.get_product.return_value = None

    result = similar_products_service.enrich_profile("test@example.com", "9999")

    assert result['success'] is False
    assert result['similar_count'] == 0
    assert result['error'] == "Product not found"


def test_cleanup_profile(similar_products_service, mock_klaviyo_client):
    """Test profile cleanup."""
    mock_klaviyo_client.remove_similar_products.return_value = True

    result = similar_products_service.cleanup_profile("test@example.com", "4422")

    assert result is True
    mock_klaviyo_client.remove_similar_products.assert_called_once_with("test@example.com", "4422")
