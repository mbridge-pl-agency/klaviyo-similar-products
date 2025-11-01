# Klaviyo Similar Products Recommendation

> Boost conversion rates by recommending similar products in "Back in Stock" email campaigns.

A Flask-based webhook service that enriches Klaviyo "Back in Stock" emails with intelligent product recommendations from PrestaShop 1.7.x, automatically selected using industry-standard BM25 algorithm.
There is a possibility of simple expansion with other e-commerce engines/platforms by creating additional adapters.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [The Hack](#the-hack)
- [Features](#features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Scaling to Enterprise](#scaling-to-enterprise)
- [Klaviyo Setup](#klaviyo-setup)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## The Problem

When customers subscribe to "Back in Stock" notifications for out-of-stock products, they receive a confirmation email without any alternative product suggestions. This represents a **lost sales opportunity**.

**The bigger challenge:** Klaviyo doesn't allow editing events after they're sent. Once your PrestaShop/WooCommerce/Shopify integration creates a "Back in Stock" event, it's immutable. How do you enrich emails without modifying official integration code?

---

## The Solution

This service automatically:
1. Intercepts Klaviyo "Back in Stock" event webhooks
2. Finds 6 similar products from PrestaShop 1.7.x (same category + BM25 name similarity)
3. Temporarily stores product IDs in Klaviyo user profiles
4. Email templates render products directly from Klaviyo Product Catalog
5. Cleans up profile data after email is sent

**Result:** Customers see relevant alternatives immediately, increasing conversion rates even when products are out of stock.

---

## The Hack

**Instead of modifying immutable events, we use Klaviyo user profiles as a temporary database.**

```
Traditional Approach (❌ Not Possible):
┌─────────────────────────────────────────────────────┐
│ Modify "Back in Stock" event to include             │
│ similar_products: [1234, 5678, 9012]                │
└─────────────────────────────────────────────────────┘
Problem: Can't modify events sent by official integrations!

Our Approach (✅ Works):
┌─────────────────────────────────────────────────────┐
│ User Profile (temporary storage):                   │
│ {                                                   │
│   "email": "user@example.com",                      │
│   "bis_similar_products": [                         │
│     {"product_id": "4422", "similar_ids": [...]}    │
│   ]                                                 │
│ }                                                   │
└─────────────────────────────────────────────────────┘
✅ No modifications to official integrations
✅ No changes to existing events
✅ Webhooks handle enrichment + cleanup
```

### Why This Pattern Matters

This **profile-as-temporary-database** pattern transforms Klaviyo profiles from static user data into **dynamic, flow-specific context** without touching any existing integrations.

**The Pattern:**
```
1. Flow Webhook (Enrich) → Fetch external data → Store in profile
2. Email sends → Template reads profile data → Renders dynamic content
3. Flow Webhook (Cleanup) → Remove temporary data → Keep profiles clean
```

**Reusable for other use cases:** Abandoned cart recovery with "frequently bought together" items, price drop alerts with competitor prices, dynamic discount codes, personalized onboarding steps, and more.

---

## Features

- **Smart Product Matching** - BM25 algorithm (industry standard: 60% name, 30% price, 10% manufacturer) finds optimal substitutes
- **Klaviyo Catalog Integration** - Leverages existing product catalog (no duplicate data)
- **Multiple Subscriptions** - Handles users subscribed to multiple products correctly
- **In-Stock Filtering** - Only recommends available products
- **Platform Agnostic** - Adapter pattern allows future WooCommerce/Shopify integration
- **Zero Dependencies** - Pure Python (math, collections only), works on shared hosting
- **Production Ready** - GDPR-compliant logging, error handling, security

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
- `KLAVIYO_API_KEY` - Your Klaviyo private API key
- `ECOMMERCE_URL` - PrestaShop 1.7.x store URL
- `ECOMMERCE_API_KEY` - PrestaShop 1.7.x WebService API key
- `WEBHOOK_SECRET` - Secret token for webhook authentication

### 3. Run Application

```bash
python run.py
```

Application starts on `http://localhost:5000`

### 4. Verify Health

```bash
curl http://localhost:5000/health
# Expected: {"status": "healthy"}
```

---

## How It Works

### Architecture

```
┌─────────────┐      Webhook        ┌──────────────────┐
│   Klaviyo   │ ──────────────────> │  Flask App       │
│   Back in   │                     │  (Enrich)        │
│   Stock     │                     └────────┬─────────┘
└─────────────┘                              │
                                             ▼
                                   ┌──────────────────┐
                                   │  PrestaShop 1.7  │
                                   │  WebService API  │
                                   │  - Get Product   │
                                   │  - Category      │
                                   └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │  BM25 Algorithm  │
                                   │  Smart Matching  │
                                   └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │  Klaviyo API     │
                                   │  (Update Profile)│
                                   └──────────────────┘
```

### Data Structure

Similar products stored in Klaviyo profile:
```json
{
  "bis_similar_products": [
    {
      "product_id": "4422",
      "similar_ids": ["15655", "11773", "9012", "3456", "7890", "1122"],
      "enriched_at": "2025-10-30T12:34:56Z"
    }
  ]
}
```

### The Algorithm: BM25

This service uses **BM25 (Best Matching 25)** - the industry-standard ranking algorithm used by Elasticsearch, Lucene, and major search engines worldwide.

**Why BM25?**
- **Industry Standard** - Used by Elasticsearch, Lucene, Apache Solr
- **Zero Dependencies** - Pure Python (only `math` and `collections`)
- **Fast Performance** - Processes 100 products in ~100ms
- **Better Accuracy** - 10-15% improvement over TF-IDF
- **Saturation Function** - Realistic diminishing returns for repeated words (prevents "spam")
- **Length Normalization** - Fair comparison between short/long product names
- **Multi-Language Support** - Handles Polish + English product names
- **Shared Hosting Compatible** - Works on resource-limited environments

**Scoring Formula:**
- **60% Name Similarity** - BM25 with saturation + length normalization
- **30% Price Proximity** - Threshold-based scoring (0-20% diff = 1.0, 20-50% = 0.5, >50% = 0.2)
- **10% Manufacturer Match** - Bonus for same brand, but not decisive

**Algorithm Comparison:**

| Algorithm | Accuracy | Dependencies | Speed | Recommended For |
|-----------|----------|--------------|-------|-----------------|
| **BM25** ✅ **(Current)** | Excellent | None | Fast (~100ms) | All catalog sizes, shared hosting |
| **TF-IDF + Cosine** | Good | None | Fast | Small catalogs (<1k products) |
| **Jaccard Similarity** | Basic | None | Very Fast | Prototyping only |
| **Word2Vec / GloVe** | Very Good | gensim (~350MB) | Medium | Large catalogs (>10k), dedicated server |
| **BERT / Sentence Transformers** | Best | transformers (~500MB) | Slow (CPU) / Fast (GPU) | Enterprise, GPU, >50k products |

---

## Scaling to Enterprise

**For large e-commerce shops (>10,000 products), Sentence Transformers with pre-computed embeddings offer the best accuracy**, but require significant infrastructure changes.

### Enterprise Architecture

Instead of computing similarity on-the-fly during webhook requests, pre-compute product embeddings nightly and store them in your e-commerce database:

```
┌─────────────────────────────────────────────────────────────┐
│  PrestaShop / WooCommerce / Shopify Database                │
│  ┌────────────────┐  ┌─────────────────────────────────┐    │
│  │ products       │  │ product_embeddings (NEW TABLE)  │    │
│  │ - id           │  │ - product_id                    │    │
│  │ - name         │  │ - embedding_vector (768D)       │    │
│  │ - price        │  │ - updated_at                    │    │
│  │ - quantity     │  │ - name_hash (detect changes)    │    │
│  └────────────────┘  └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Pre-compute embeddings (nightly job)
                              │
                    ┌─────────────────────┐
                    │  Embedding Service  │
                    │  (GPU/CPU Server)   │
                    │  - Sentence BERT    │
                    │  - Batch processing │
                    └─────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Klaviyo Webhook (Real-time)                                 │
│  1. Receive "Back in Stock" event                            │
│  2. Query: SELECT embedding FROM product_embeddings          │
│     WHERE product_id = 4422                                  │
│  3. Calculate cosine similarity with ALL embeddings          │
│     (fast vector operation, ~10ms for 100k products)         │
│  4. Filter: JOIN products WHERE quantity > 0 AND price > 0   │
│  5. Return top 6 most similar in-stock products              │
└──────────────────────────────────────────────────────────────┘
```

### Key Benefits

1. **No Category Limitation** - Find similar products across entire catalog, not just same category
2. **Real-time Performance** - Webhook responds in ~50-100ms even with 100,000 products
3. **Separation of Concerns:**
   - **Embedding Generation** (compute-intensive) - Nightly background job
   - **Stock/Price Sync** (lightweight) - API poll every 1-6 hours
   - **Similarity Search** (real-time) - Fast vector operations during webhook
4. **Best Semantic Understanding:**
   - "Ciastka czekoladowe" ≈ "Chocolate cookies" (cross-language)
   - "Keto cookies" ≈ "Low-carb biscuits" (semantic equivalence)
   - "Wegańskie ciasteczka" ≈ "Vegan snacks" (category similarity)

### When to Use Enterprise Architecture

✅ **Use if:**
- You have >10,000 products
- Cross-category recommendations are valuable ("chocolate cookies" → "chocolate bars")
- You have dedicated server infrastructure
- Matching accuracy is business-critical

❌ **Don't use if:**
- You have <5,000 products (BM25 is sufficient)
- Shared hosting environment
- Limited budget for infrastructure
- Products are well-organized in categories

### Implementation Options

**Embeddings:** Instead of self-hosting Sentence Transformers (requires GPU/dedicated server), you can use embedding APIs like OpenAI `text-embedding-3-large`, Cohere `embed-multilingual-v3.0`, or Google Vertex AI. These offer excellent accuracy with minimal infrastructure (~$0.02-0.20/month for 10k products) and work well on shared hosting.

**Database:** Add `product_embeddings` table with vector support (PostgreSQL `pgvector`, MySQL 9.0+). Pre-compute embeddings nightly, query via cosine similarity during webhooks (~10ms for 100k products).

**Current implementation (BM25) is optimal for small/medium shops (<10k products).**

---

## Klaviyo Setup

### 1. Configure Enrich Webhook

In your Klaviyo "Back in Stock" Flow, add a Webhook action:

**URL:** `https://your-domain.com/webhook/enrich`
**Method:** POST
**Headers:**
```
X-Webhook-Token: your-webhook-secret
Content-Type: application/json
```

**Body:**
```json
{
  "email": "{{ person.email }}",
  "ProductID": "{{ event.ProductID }}",
  "ProductName": "{{ event.ProductName }}"
}
```

### 2. Email Template

Use this template in your email:

```liquid
{% if person.bis_similar_products %}
  {% for item in person.bis_similar_products %}
    {% if item.product_id == event.ProductID %}

      <h3>While you wait, check these alternatives:</h3>

      {% for product_id in item.similar_ids %}
        {% catalog product_id integration='prestashop' %}
          <div style="padding: 15px; border: 1px solid #ddd;">
            <img src="{{ catalog_item.featured_image.full.src }}" />
            <h4>{{ catalog_item.title }}</h4>
            <p>£{{ catalog_item.price }}</p>
            <a href="{{ catalog_item.url }}">View Product</a>
          </div>
        {% endcatalog %}
      {% endfor %}

    {% endif %}
  {% endfor %}
{% endif %}
```

**Important:** If no similar products are found, the `bis_similar_products` property is **not added** to the profile, so this section won't render. This prevents showing empty "alternatives" sections.

### 3. Configure Cleanup Webhook

After sending the email, add another Webhook action:

**URL:** `https://your-domain.com/webhook/cleanup`
**Method:** POST
**Headers:** Same as enrich
**Body:**
```json
{
  "email": "{{ person.email }}",
  "ProductID": "{{ event.ProductID }}"
}
```

---

## API Reference

### POST /webhook/enrich

Enrich user profile with similar product recommendations.

**Request:**
```json
{
  "email": "user@example.com",
  "ProductID": "4422"
}
```

**Response:**
```json
{
  "status": "success",
  "similar_products_count": 6,
  "timestamp": "2025-10-30T12:34:56Z",
  "duration_ms": 850
}
```

### POST /webhook/cleanup

Remove similar products data from profile.

**Request:**
```json
{
  "email": "user@example.com",
  "ProductID": "4422"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `KLAVIYO_API_KEY` | Klaviyo private API key | *required* |
| `ECOMMERCE_URL` | PrestaShop 1.7.x store URL | *required* |
| `ECOMMERCE_API_KEY` | PrestaShop 1.7.x WebService API key | *required* |
| `WEBHOOK_SECRET` | Webhook authentication token | *required* |
| `SIMILAR_PRODUCTS_LIMIT` | Max similar products | `6` |
| `API_TIMEOUT` | HTTP timeout (seconds) | `10` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## Deployment

### Production Deployment

Use gunicorn for production:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 run:app
```

### Requirements

- Python 3.9+
- Public HTTPS endpoint (for Klaviyo webhooks)
- **PrestaShop 1.7.x** with WebService enabled
  - ⚠️ **Note:** Tested with PrestaShop 1.7.x only. Newer versions (1.8+, 8.x) may require adapter modifications.
- Klaviyo Product Catalog synchronized with PrestaShop

### Security

- **Webhook Authentication:** Constant-time secret comparison prevents timing attacks
- **GDPR Compliant:** Email addresses hashed in logs
- **No Secrets in Logs:** API keys never logged
- **HTTPS Required:** Production deployment requires HTTPS

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

---

## Troubleshooting

### No Similar Products

- Verify product exists in PrestaShop 1.7.x
- Check product has category assigned
- Ensure other products exist in same category and are in stock
- ⚠️ If using PrestaShop 1.8+ or 8.x, the adapter may need modifications

### Webhook Returns 401

- Verify `X-Webhook-Token` header matches `WEBHOOK_SECRET`

### Profile Not Found

- Verify email exists in Klaviyo
- Check Klaviyo API key permissions

---

## Project Structure

```
klaviyo-presta/
├── app/
│   ├── adapters/          # E-commerce platform adapters
│   │   ├── base.py        # Abstract base classes
│   │   └── prestashop.py  # PrestaShop 1.7.x implementation
│   ├── clients/           # External API clients
│   │   └── klaviyo_client.py
│   ├── services/          # Business logic
│   │   ├── similar_products_service.py
│   │   └── product_similarity.py  # BM25 algorithm
│   ├── webhooks/          # Flask endpoints
│   │   ├── enrich.py
│   │   └── cleanup.py
│   └── utils/             # Utilities
│       ├── logger.py      # Structured logging
│       └── validators.py  # Security
├── tests/                 # Unit & integration tests
├── run.py                 # Application entry point
└── requirements.txt
```

---

## Future Enhancements

**Platform Integrations:**
- [ ] WooCommerce adapter
- [ ] Shopify adapter
- [ ] Magento adapter

**Algorithm Improvements:**
- [ ] Word2Vec embeddings (requires dedicated server, gensim dependency)
- [ ] BERT/Sentence Transformers (requires GPU or high-performance CPU)
- [ ] N-gram tokenization for Polish inflections ("ciastka" → "ciasteczka")
- [ ] Fine-tuned BM25 parameters (k1, b) per product category

**Performance & Scale:**
- [ ] Redis caching layer for PrestaShop API responses
- [ ] Background job processing for large catalogs (>1000 products)
- [ ] Product embedding pre-computation (cache BM25 vectors)

**Analytics & Testing:**
- [ ] A/B testing framework for algorithm comparison
- [ ] Analytics dashboard (click-through rates, conversion tracking)
- [ ] Recommendation quality metrics (precision@k, NDCG)

---

## Contributing

Contributions welcome! Please open an issue or pull request.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with Flask, designed for growth.**
