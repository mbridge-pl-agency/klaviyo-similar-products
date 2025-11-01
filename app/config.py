"""
Application configuration from environment variables.
"""

import os


class Config:
    """Application configuration from environment variables."""

    # Klaviyo
    KLAVIYO_API_KEY: str = os.getenv('KLAVIYO_API_KEY', '')
    KLAVIYO_API_REVISION: str = os.getenv('KLAVIYO_API_REVISION', '2024-10-15')

    # E-commerce Platform
    ECOMMERCE_PLATFORM: str = os.getenv('ECOMMERCE_PLATFORM', 'prestashop')
    ECOMMERCE_URL: str = os.getenv('ECOMMERCE_URL', '')
    ECOMMERCE_API_KEY: str = os.getenv('ECOMMERCE_API_KEY', '')

    # Webhooks
    WEBHOOK_SECRET: str = os.getenv('WEBHOOK_SECRET', '')

    # Application
    SIMILAR_PRODUCTS_LIMIT: int = int(os.getenv('SIMILAR_PRODUCTS_LIMIT', '6'))
    API_TIMEOUT: int = int(os.getenv('API_TIMEOUT', '10'))

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', '/tmp/klaviyo_similar_products.log')

    @classmethod
    def validate(cls) -> None:
        """
        Validate required configuration on startup.

        Raises:
            ValueError: If required variables missing
        """
        required = [
            'KLAVIYO_API_KEY',
            'ECOMMERCE_URL',
            'ECOMMERCE_API_KEY',
            'WEBHOOK_SECRET'
        ]

        missing = [key for key in required if not getattr(cls, key)]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
