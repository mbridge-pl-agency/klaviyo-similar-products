"""
Flask application factory and service initialization.
"""

from flask import Flask, jsonify
from app.config import Config
from app.adapters.base import EcommerceAdapter
from app.adapters.prestashop import PrestaShopAdapter
from app.clients.klaviyo_client import KlaviyoClient
from app.services.similar_products_service import SimilarProductsService
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global service instance
_similar_products_service = None


def create_app():
    """
    Create and configure Flask application.

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise

    # Initialize clients and service
    global _similar_products_service

    # Select e-commerce adapter based on platform
    if Config.ECOMMERCE_PLATFORM.lower() == 'prestashop':
        ecommerce_adapter = PrestaShopAdapter(
            Config.ECOMMERCE_URL,
            Config.ECOMMERCE_API_KEY,
            Config.API_TIMEOUT
        )
        logger.info("Initialized PrestaShop adapter")
    else:
        raise ValueError(f"Unsupported e-commerce platform: {Config.ECOMMERCE_PLATFORM}")

    # Initialize Klaviyo client
    klaviyo_client = KlaviyoClient(
        Config.KLAVIYO_API_KEY,
        Config.KLAVIYO_API_REVISION,
        Config.API_TIMEOUT
    )
    logger.info("Initialized Klaviyo client")

    # Initialize service
    _similar_products_service = SimilarProductsService(
        ecommerce_adapter,
        klaviyo_client,
        Config.SIMILAR_PRODUCTS_LIMIT
    )
    logger.info("Initialized similar products service")

    # Register blueprints
    from app.webhooks import enrich, cleanup
    app.register_blueprint(enrich.bp)
    app.register_blueprint(cleanup.bp)
    logger.info("Registered webhook blueprints")

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        """
        Health check endpoint.

        Returns:
            200 OK if application is healthy
        """
        return jsonify({"status": "healthy"}), 200

    logger.info("Application initialized successfully")

    return app


def get_service() -> SimilarProductsService:
    """
    Get global service instance.

    Returns:
        SimilarProductsService instance
    """
    return _similar_products_service
