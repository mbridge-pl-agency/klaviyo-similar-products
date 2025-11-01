"""
Webhook endpoint for profile enrichment with similar products.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.utils.validators import validate_webhook_secret
from app.utils.logger import get_logger, log_with_context, hash_email

bp = Blueprint('enrich', __name__)
logger = get_logger(__name__)


@bp.route('/webhook/enrich', methods=['POST'])
def enrich_profile():
    """
    Enrich user profile with similar product IDs.

    Expected payload from Klaviyo:
    {
        "email": "user@example.com",
        "ProductID": "4422",
        "ProductName": "...",
        ...
    }

    Returns:
    {
        "status": "success",
        "similar_products_count": 6,
        "timestamp": "2025-10-30T12:34:56Z",
        "duration_ms": 850
    }
    """
    start_time = datetime.utcnow()

    try:
        # Validate webhook secret
        token = request.headers.get('X-Webhook-Token')
        if not validate_webhook_secret(token):
            log_with_context(
                logger, "WARNING",
                "Unauthorized webhook attempt",
                ip=request.remote_addr
            )
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        # Parse request
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400

        email = data.get('email')
        product_id = data.get('ProductID')

        if not email or not product_id:
            return jsonify({
                "status": "error",
                "message": "Missing email or ProductID"
            }), 400

        # Get service
        from app import get_service
        service = get_service()

        # Process enrichment
        result = service.enrich_profile(email, product_id)

        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        if result['success']:
            log_with_context(
                logger, "INFO",
                "Profile enriched successfully",
                user_hash=hash_email(email),
                product_id=product_id,
                similar_count=result['similar_count'],
                duration_ms=duration_ms
            )

            return jsonify({
                "status": "success",
                "similar_products_count": result['similar_count'],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms
            }), 200
        else:
            log_with_context(
                logger, "ERROR",
                "Enrichment failed",
                user_hash=hash_email(email),
                product_id=product_id,
                error=result['error']
            )

            return jsonify({
                "status": "error",
                "message": result['error'],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }), 500

    except Exception as e:
        logger.exception("Unexpected error in enrich webhook")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500
