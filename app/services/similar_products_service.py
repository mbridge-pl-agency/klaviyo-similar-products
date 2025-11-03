"""
Core business logic for similar products recommendation.
"""

from typing import List, Dict
from datetime import datetime
from app.adapters.base import EcommerceAdapter, Product
from app.clients.klaviyo_client import KlaviyoClient
from app.services.product_similarity import calculate_similarity_with_context
from app.utils.logger import get_logger, log_with_context, hash_email

logger = get_logger(__name__)


class SimilarProductsService:
    """
    Similar products recommendation service.

    Orchestrates:
    1. Fetching products from e-commerce platform
    2. Finding similar products using text similarity
    3. Updating Klaviyo profiles with recommendations
    """

    def __init__(
        self,
        ecommerce_adapter: EcommerceAdapter,
        klaviyo_client: KlaviyoClient,
        limit: int = 6
    ):
        """
        Initialize service with clients.

        Args:
            ecommerce_adapter: E-commerce platform adapter
            klaviyo_client: Klaviyo API client
            limit: Maximum number of similar products to return
        """
        self.ecommerce_adapter = ecommerce_adapter
        self.klaviyo_client = klaviyo_client
        self.limit = limit

    def enrich_profile(self, email: str, product_id: str) -> Dict:
        """
        Main orchestration method: enrich profile with similar products.

        Steps:
        1. Get original product from e-commerce platform
        2. Find similar products
        3. Update Klaviyo profile with product IDs

        Args:
            email: User email address
            product_id: Product ID user subscribed to

        Returns:
            {
                "success": bool,
                "similar_count": int,
                "error": str or None
            }
        """
        try:
            # 1. Get original product
            original_product = self.ecommerce_adapter.get_product(product_id)
            if not original_product:
                log_with_context(
                    logger, "WARNING",
                    "Product not found",
                    product_id=product_id
                )
                return {
                    "success": False,
                    "similar_count": 0,
                    "error": "Product not found"
                }

            log_with_context(
                logger, "INFO",
                "Product found",
                product_id=product_id,
                product_name=original_product.name,
                category_id=original_product.category_id
            )

            # 2. Find similar products
            similar_product_ids = self.find_similar_products(original_product)

            log_with_context(
                logger, "INFO",
                "Similar products found",
                product_id=product_id,
                similar_count=len(similar_product_ids)
            )

            # 3. Update Klaviyo profile (only if we have similar products)
            if len(similar_product_ids) > 0:
                self.klaviyo_client.add_similar_products(
                    email=email,
                    product_id=product_id,
                    similar_product_ids=similar_product_ids,
                    enriched_at=datetime.utcnow().isoformat() + "Z"
                )

                log_with_context(
                    logger, "INFO",
                    "Profile enriched successfully",
                    user_hash=hash_email(email),
                    product_id=product_id,
                    similar_count=len(similar_product_ids)
                )
            else:
                log_with_context(
                    logger, "INFO",
                    "No similar products to add - skipping Klaviyo update",
                    user_hash=hash_email(email),
                    product_id=product_id
                )

            return {
                "success": True,
                "similar_count": len(similar_product_ids),
                "error": None
            }

        except Exception as e:
            log_with_context(
                logger, "ERROR",
                "Error enriching profile",
                user_hash=hash_email(email),
                product_id=product_id,
                error=str(e)
            )
            return {
                "success": False,
                "similar_count": 0,
                "error": str(e)
            }

    def find_similar_products(self, original_product: Product) -> List[str]:
        """
        Find similar products and return their IDs using intelligent scoring.

        Algorithm:
        1. Fetch products from same category (limit 100 for better BM25 IDF)
        2. Filter: exclude original, only in-stock products (quantity > 0)
        3. Score each candidate using multi-factor algorithm:
           - 60% Name similarity (BM25 with saturation + length normalization)
           - 30% Price proximity (similar price point)
           - 10% Manufacturer match (nice bonus)
        4. Sort by score descending
        5. Return top N product IDs

        Note: Larger corpus (100 products) = better BM25 IDF scores for unique words.

        Args:
            original_product: The product user subscribed to

        Returns:
            List of product IDs (strings), max self.limit items
        """
        try:
            # Fetch candidates from same category (larger corpus = better BM25 IDF)
            candidates = self.ecommerce_adapter.get_products_by_category(
                original_product.category_id,
                limit=100
            )

            log_with_context(
                logger, "INFO",
                "Fetched category products",
                product_id=original_product.id,
                category_id=original_product.category_id,
                total_fetched=len(candidates)
            )

            # Filter: not original, in stock only
            candidates = [
                p for p in candidates
                if p.id != original_product.id and p.quantity > 0
            ]

            if not candidates:
                log_with_context(
                    logger, "WARNING",
                    "No in-stock candidates found",
                    product_id=original_product.id,
                    category_id=original_product.category_id
                )
                return []

            log_with_context(
                logger, "INFO",
                "Filtered in-stock candidates",
                product_id=original_product.id,
                in_stock_count=len(candidates)
            )

            # Score each candidate using comprehensive similarity algorithm
            scored = []
            for candidate in candidates:
                score = calculate_similarity_with_context(
                    original_product,
                    candidate,
                    all_products=candidates  # Full corpus for BM25 IDF calculation
                )
                scored.append((score, candidate))

            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)

            # Log top matches for debugging
            if scored:
                top_3 = scored[:3]
                log_with_context(
                    logger, "INFO",
                    "Top similar products",
                    product_id=original_product.id,
                    top_matches=[
                        {
                            "id": p.id,
                            "name": p.name[:50],
                            "score": round(score, 3)
                        }
                        for score, p in top_3
                    ]
                )

            # Return top N IDs
            return [product.id for _, product in scored[:self.limit]]

        except Exception as e:
            log_with_context(
                logger, "ERROR",
                "Error finding similar products",
                product_id=original_product.id,
                error=str(e)
            )
            return []

    def cleanup_profile(self, email: str, product_id: str = None) -> bool:
        """
        Remove similar products data from profile.

        Args:
            email: User email address
            product_id: If provided, remove only this product's data.
                       If None, remove entire array.

        Returns:
            True if successful
        """
        try:
            self.klaviyo_client.remove_similar_products(email, product_id)

            log_with_context(
                logger, "INFO",
                "Profile cleaned up",
                user_hash=hash_email(email),
                product_id=product_id or "all"
            )

            return True

        except Exception as e:
            log_with_context(
                logger, "ERROR",
                "Error cleaning up profile",
                user_hash=hash_email(email),
                product_id=product_id or "all",
                error=str(e)
            )
            return False
