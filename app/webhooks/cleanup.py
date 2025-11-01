"""
Webhook endpoint for cleaning up profile data after email sent.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.utils.validators import validate_webhook_secret
from app.utils.logger import get_logger, log_with_context, hash_email

bp = Blueprint('cleanup', __name__)
logger = get_logger(__name__)


@bp.route('/webhook/cleanup', methods=['POST'])
def cleanup_profile():
    """
    Remove similar products data from user profile.

    Expected payload:
    {
        "email": "user@example.com",
        "ProductID": "4422"  // Optional - if omitted, removes entire array
    }

    Returns:
    {
        "status": "success",
        "timestamp": "2025-10-30T12:34:56Z"
    }
    """
    try:
        # Validate webhook secret
        token = request.headers.get('X-Webhook-Token')
        if not validate_webhook_secret(token):
            log_with_context(
                logger, "WARNING",
                "Unauthorized cleanup attempt",
                ip=request.remote_addr
            )
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        # Parse request
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400

        email = data.get('email')
        if not email:
            return jsonify({
                "status": "error",
                "message": "Missing email"
            }), 400

        product_id = data.get('ProductID')  # Optional

        # Get service
        from app import get_service
        service = get_service()

        # Cleanup profile
        success = service.cleanup_profile(email, product_id)

        if success:
            log_with_context(
                logger, "INFO",
                "Profile cleaned up",
                user_hash=hash_email(email),
                product_id=product_id or "all"
            )

            return jsonify({
                "status": "success",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }), 200
        else:
            log_with_context(
                logger, "ERROR",
                "Cleanup failed",
                user_hash=hash_email(email),
                product_id=product_id or "all"
            )

            return jsonify({
                "status": "error",
                "message": "Cleanup failed",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }), 500

    except Exception as e:
        logger.exception("Unexpected error in cleanup webhook")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500
