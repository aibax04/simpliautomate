# Social Media Data Ingestion Layer

This module implements a production-grade social media data ingestion pipeline for the Simplii platform, supporting Twitter/X API v2 and NewsAPI/GNews with unified data normalization and incremental fetching.

## 🚀 Features

- **Multi-Platform Support**: Twitter and News APIs
- **Unified Schema**: All data normalized into consistent format
- **Incremental Fetching**: Cursor-based pagination prevents duplicates
- **Rate Limit Handling**: Automatic retry with exponential backoff
- **Background Processing**: Async task integration
- **Query Builders**: Platform-specific query construction
- **Error Resilience**: Comprehensive error handling and logging

## 📁 Architecture

```
backend/services/connectors/
├── base_connector.py          # Abstract base class
├── twitter_connector.py       # Twitter API v2 implementation
├── news_connector.py          # NewsAPI/GNews implementation
├── connector_manager.py       # Orchestration and deduplication
├── ingestion_service.py       # Background task integration
├── tests/                     # Unit tests
│   └── test_base_connector.py
└── README.md                  # This file
```

## 🔧 Setup

### 1. Environment Variables

Add the following to your `.env` file:

```bash
# Twitter API v2 (Required for Twitter ingestion)
TWITTER_BEARER_TOKEN=your_bearer_token_here

# News API (Choose one provider)
NEWS_PROVIDER=newsapi  # or 'gnews'
NEWSAPI_KEY=your_newsapi_key_here
# OR
GNEWS_API_KEY=your_gnews_key_here
```

### 2. Dependencies

Install required packages:

```bash
pip install praw newsapi-python tweepy aiohttp
```

### 3. API Credentials Setup

#### Twitter API v2
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app or use existing one
3. Generate a Bearer Token
4. Add to environment: `TWITTER_BEARER_TOKEN=your_token`

#### NewsAPI
1. Go to [NewsAPI](https://newsapi.org/)
2. Sign up for a free API key
3. Add to environment: `NEWSAPI_KEY=your_key`

#### GNews (Alternative)
1. Go to [GNews](https://gnews.io/)
2. Sign up for a free API key
3. Set `NEWS_PROVIDER=gnews` and `GNEWS_API_KEY=your_key`

## 🔌 API Endpoints

### Status and Configuration

```http
GET /api/social-ingestion/status
```
Returns service status and connector authentication state.

```http
GET /api/social-ingestion/platforms
```
Returns available platforms and their status.

### Query Testing

```http
POST /api/social-ingestion/test-query
Content-Type: application/json

{
  "platform": "twitter",
  "query": "AI OR artificial intelligence",
  "limit": 5
}
```
Test a query before creating ingestion rules.

### Ingestion Tasks

```http
POST /api/social-ingestion/run
Content-Type: application/json

{
  "rule_id": "twitter_ai_trends",
  "platform": "twitter",
  "query": "(artificial intelligence OR AI) -filter:replies",
  "max_posts_per_run": 50,
  "enabled": true
}
```
Run a single ingestion task.

```http
POST /api/social-ingestion/run-bulk
Content-Type: application/json

{
  "rules": [
    {
      "rule_id": "twitter_ai",
      "platform": "twitter",
      "query": "AI OR machine learning",
      "max_posts_per_run": 50
    },
  ]
}
```
Run multiple ingestion tasks concurrently.

### Query Syntax

```http
GET /api/social-ingestion/query-syntax/{platform}
```
Get query syntax documentation for a platform.

```http
GET /api/social-ingestion/examples
```
Get example ingestion rules.

## 📝 Query Syntax

### Twitter API v2

**Basic Search:**
```
AI OR artificial intelligence
```

**Handle-based filtering:**
```
from:OpenAI OR from:GoogleAI
```

**Combined queries:**
```
(AI OR startup) from:sequoia min_faves:10
```

**Operators:**
- `OR` - logical OR
- `from:username` - posts from specific user
- `to:username` - posts to specific user
- `lang:en` - language filter
- `since:2024-01-01` - posts since date
- `until:2024-01-31` - posts until date
- `min_faves:N` - minimum likes
- `min_retweets:N` - minimum retweets
- `-term` - exclude term


### NewsAPI/GNews

**Keyword search:**
```
artificial intelligence
```

**Source filtering:**
```
AI source:bbc-news
```

**Date range:**
```
tech from:2024-01-01 to:2024-01-31
```

## 🧪 Testing

### Run Unit Tests

```bash
cd backend/services/connectors
python -m pytest tests/
```

### API Test Script

Run the comprehensive test script:

```bash
python test_social_ingestion.py
```

Set environment variables:
```bash
export SIMPLII_BASE_URL=http://localhost:8000
export SIMPLII_AUTH_TOKEN=your_jwt_token
```

## 📊 Data Schema

All ingested data is normalized into this unified format:

```python
{
  "post_id": "twitter:1234567890",
  "platform": "twitter",
  "author": "John Doe",
  "handle": "@johndoe",
  "content": "Exciting AI developments... #AI",
  "url": "https://twitter.com/johndoe/status/1234567890",
  "posted_at": "2024-01-15T10:30:00Z",
  "fetched_at": "2024-01-15T10:35:00Z",
  "metadata": {
    "tweet_id": "1234567890",
    "public_metrics": {"likes": 42, "retweets": 12},
    "lang": "en"
  }
}
```

## 🔄 Incremental Fetching

The system uses cursor-based pagination to avoid duplicates:

- **Twitter**: `since_id` parameter for tweet IDs
- **Reddit**: `before` parameter for post IDs
- **News**: Offset-based pagination

Cursors are stored per rule and platform, ensuring only new content is fetched.

## ⚡ Rate Limiting

- **Twitter**: 300 requests per 15 minutes (free tier)
- **Reddit**: 600 requests per 10 minutes
- **NewsAPI**: 100 requests per day (free tier)

Automatic retry with exponential backoff on rate limit errors.

## 🔒 Security

- API keys stored as environment variables
- Input sanitization and validation
- Query injection prevention
- Isolated user query execution

## 🚨 Error Handling

- Network timeouts with retry logic
- API rate limit handling
- Authentication error detection
- Partial success handling
- Comprehensive logging

## 📈 Monitoring

Monitor ingestion health via:

```http
GET /api/social-ingestion/status
```

Returns:
```json
{
  "initialized": true,
  "available_platforms": ["twitter", "reddit", "news"],
  "connector_status": {
    "twitter": true,
    "reddit": true,
    "news": false
  }
}
```

## 🛠️ Development

### Adding New Platforms

1. Create new connector inheriting from `BaseConnector`
2. Implement required methods: `authenticate()`, `fetch_posts()`, `normalize()`
3. Add to `ConnectorManager._setup_connectors()`
4. Update environment variables and validation

### Extending Query Builders

Add platform-specific query builders in the respective connector classes.

## 🤝 Contributing

1. Follow the existing code structure
2. Add unit tests for new functionality
3. Update documentation
4. Test with all supported platforms

## 📄 License

This module is part of the Simplii platform and follows the same licensing terms.