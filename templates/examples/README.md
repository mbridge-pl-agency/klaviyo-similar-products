# Klaviyo Email Templates

This directory contains email template examples for Klaviyo integration.

## klaviyo_similar_products_email.liquid

Email template for displaying similar product recommendations in back-in-stock notifications.

### Features

- Displays 6 similar products in a 2-column grid (3 rows)
- Responsive design that works on desktop and mobile
- Styled to match brand guidelines

### Template Specifications

- **Font**: Helvetica 16px (no bold, except heading)
- **Button Color**: #6BBF59 (green) with white text
- **Image Height**: Max 125px
- **Product Name**: Black text with underline
- **Price**: Formatted with currency symbol

### Klaviyo-Specific Syntax

This template uses Klaviyo's `lookup` notation to access nested data:

```liquid
{% catalog person.bis_similar_products|lookup:'0'|lookup:'similar_ids'|lookup:'0' integration='prestashop' catalog_id="1:2" %}
```

**Important**: Klaviyo Liquid doesn't support:
- Array bracket notation (`person.data[0]` ❌)
- `assign` statements with counters
- Standard Liquid for loops with complex logic

Use `lookup` filter instead: `person.bis_similar_products|lookup:'0'|lookup:'product_id'` ✅

### Data Structure Expected

The template expects profile property `bis_similar_products` with this structure:

```json
[
  {
    "product_id": "309",
    "similar_ids": ["483", "290", "466", "1284", "1410", "1536"],
    "enriched_at": "2025-11-03T12:33:25.672921Z"
  }
]
```

### How to Use in Klaviyo

1. Copy the content from `klaviyo_similar_products_email.liquid`
2. In Klaviyo, edit your back-in-stock email template
3. Paste the code where you want similar products to appear
4. Update `catalog_id="1:2"` to match your PrestaShop integration ID
5. Preview and test with a profile that has `bis_similar_products` data

### Integration with Webhooks

This template works with the ENRICH webhook that populates the `bis_similar_products` profile property:
- ENRICH webhook runs before back-in-stock email is sent
- Adds similar products to user profile
- Email template reads from profile property
- CLEANUP webhook removes data after email is sent
