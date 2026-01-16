# Simplii Architecture Documentation

## System Overview

Simplii is an AI-powered news-to-content automation platform that transforms daily news into curated LinkedIn posts with AI-generated images. The system leverages Google Gemini 2.0 Flash API for intelligent content generation and LangGraph for orchestrated multi-agent workflows.

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL INTEGRATIONS                                │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│  LinkedIn OAuth  │  Google Gemini   │  DuckDuckGo/     │  Gmail SMTP        │
│  API 2.0         │  2.0 Flash API   │  Google CSE      │  Notifications     │
└────────┬─────────┴──────────┬───────┴────────┬────────┴────────┬───────────┘
         │                    │                │                 │
         ▼                    ▼                ▼                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND SERVER                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    7 API ROUTERS                                     │  │
│  ├──────────────────┬──────────────────┬──────────────────┬────────────┤  │
│  │ /auth            │ /linkedin        │ /ingest          │ /queue     │  │
│  │ • Signup         │ • OAuth Flow     │ • Parse URLs     │ • Add Job  │  │
│  │ • Login          │ • Account Sync   │ • Parse Docs     │ • Get Job  │  │
│  │ • Waitlist       │ • Profile Fetch  │ • Prompt Gen     │ • Status   │  │
│  └──────────────────┴──────────────────┴──────────────────┴────────────┘  │
│                                                                              │
│  ┌──────────────────┬──────────────────┬──────────────────┐                │
│  │ /scheduler       │ /products        │ /media           │                │
│  │ • Schedule Post  │ • Create Profile │ • Upload Image   │                │
│  │ • List Schedule  │ • Update Profile │ • Get Image      │                │
│  │ • Publish Post   │ • Manage Links   │ • Delete Image   │                │
│  └──────────────────┴──────────────────┴──────────────────┘                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                  AGENT ORCHESTRATION LAYER                          │  │
│  │                      (LangGraph State Machine)                      │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│  │  │ NEWS FETCH AGENT │  │ CURATION AGENT   │  │ CAPTION AGENT    │  │  │
│  │  │ • Fetch Daily    │  │ • Filter News    │  │ • Gen Captions   │  │  │
│  │  │   News (DuckDG)  │  │ • Score Relevance│  │ • Polish Text    │  │  │
│  │  │ • Fetch Backup   │  │ • Select Top     │  │ • Validate Post  │  │  │
│  │  │   (Google CSE)   │  │   Articles       │  │ • Add Hashtags   │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│  │  │ IMAGE AGENT      │  │ LINKEDIN AGENT   │  │ DOCUMENT READER  │  │  │
│  │  │ • Generate Image │  │ • Publish Post   │  │ • Parse PDF/DOC  │  │  │
│  │  │ • Edit Image     │  │ • Get Accounts   │  │ • Extract Text   │  │  │
│  │  │ • Apply Style    │  │ • Post Status    │  │ • Summarize      │  │  │
│  │  │ • Gemini Vision  │  │ • Validate Auth  │  │                  │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  │  │
│  │                                                                      │  │
│  │  + 8 More Agents:                                                   │  │
│  │  • URL Reader Agent (Extract web content)                          │  │
│  │  • Topic Normalizer Agent (Categorize news)                        │  │
│  │  • Detailed Prompt Agent (Expand user prompts)                     │  │
│  │  • LinkedIn Blog Agent (Blog generation)                           │  │
│  │  • News Suggestion Agent (Recommend articles)                      │  │
│  │  • Post Generation Agent (Full post creation)                      │  │
│  │  • QA Agent (Validate content)                                     │  │
│  │  • Visual Planning Agent (Image strategy)                          │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │           BACKGROUND SERVICES & QUEUE MANAGEMENT                    │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │ • Daily News Fetcher (6 AM Scheduled Task)                          │  │
│  │ • Post Queue Manager (Process generation jobs)                      │  │
│  │ • Scheduled Publisher (Publish queued posts)                        │  │
│  │ • Fallback Mechanisms (Failed fetch recovery)                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
         │                                                          │
         ▼                                                          ▼
┌──────────────────────────────────┐        ┌────────────────────────────────┐
│    PostgreSQL DATABASE           │        │  OBJECT STORAGE               │
│  (AsyncPG + SQLAlchemy ORM)      │        │  (Image Uploads & Collateral) │
├──────────────────────────────────┤        └────────────────────────────────┘
│ • User (Auth)                    │
│ • LinkedInAccount (OAuth tokens) │
│ • Product (User profiles)        │
│ • News (Scraped articles)        │
│ • Post (Generated content)       │
│ • Queue (Job queue)              │
│ • Processing (Pipeline state)    │
└──────────────────────────────────┘
         ▲
         │
┌────────┴─────────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ News Feed UI     │  │ Post Editor      │  │ LinkedIn Account │     │
│  │ • Display News   │  │ • Edit Caption   │  │ • Connect OAuth  │     │
│  │ • Curate Items   │  │ • Image Editor   │  │ • Account List   │     │
│  │ • Category Filter│  │ • Preview Post   │  │ • Sync Accounts  │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Product Manager  │  │ Scheduler        │  │ Queue/Status     │     │
│  │ • Create Profile │  │ • Schedule Posts │  │ • View Queue     │     │
│  │ • Manage Links   │  │ • View Timeline  │  │ • Job Status     │     │
│  │ • Add Collateral │  │ • Publish Now    │  │ • Logs & Errors  │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐                            │
│  │ Settings         │  │ Chrome Extension │                            │
│  │ • User Prefs     │  │ • Popup UI       │                            │
│  │ • API Keys       │  │ • Quick Actions  │                            │
│  │ • Notification   │  │ • Bookmark News  │                            │
│  └──────────────────┘  └──────────────────┘                            │
│                                                                          │
│  Stack: Vanilla JavaScript, HTML5, CSS3                                │
│  Communication: Fetch API / JSON over HTTPS                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. **Backend Server** (`backend/server.py`)

**Framework:** FastAPI + Uvicorn

**Key Responsibilities:**
- HTTP request routing to 7 API endpoints
- Request validation and authentication
- JWT token verification via `backend/auth/security.py`
- CORS and security headers
- Error handling and logging
- WebSocket support for real-time updates (optional)

**Deployment:**
- Render Free Tier with Gunicorn + Uvicorn workers
- PostgreSQL connection pooling with asyncpg

---

### 2. **API Routes** (7 Router Modules)

#### **Auth Router** (`backend/routes/auth.py`)
```
POST   /auth/signup       → Create user account
POST   /auth/login        → JWT authentication
POST   /auth/waitlist     → Join waitlist
GET    /auth/me           → Current user info
POST   /auth/refresh      → Refresh JWT token
```

#### **LinkedIn Router** (`backend/routes/linkedin.py`)
```
GET    /linkedin/oauth    → LinkedIn OAuth callback
POST   /linkedin/accounts → List linked accounts
POST   /linkedin/sync     → Sync account info
GET    /linkedin/profile  → Get account profile
POST   /linkedin/publish  → Publish post to LinkedIn
```

#### **Ingest Router** (`backend/routes/ingest.py`)
```
POST   /ingest/url        → Parse URL content
POST   /ingest/document   → Parse PDF/DOC
POST   /ingest/prompt     → Generate AI prompt from input
```

#### **Queue Router** (`backend/routes/queue_router.py`)
```
POST   /queue/generate    → Create generation job
GET    /queue/jobs        → List all jobs
GET    /queue/job/{id}    → Get job status
POST   /queue/cancel/{id} → Cancel job
```

#### **Scheduler Router** (`backend/routes/scheduler.py`)
```
POST   /scheduler/schedule → Schedule post for future
GET    /scheduler/list     → List scheduled posts
POST   /scheduler/publish  → Publish now
DELETE /scheduler/{id}     → Cancel scheduled post
```

#### **Products Router** (`backend/routes/products.py`)
```
POST   /products/create    → Create product profile
GET    /products/list      → List user products
PUT    /products/{id}      → Update product
DELETE /products/{id}      → Delete product
POST   /products/{id}/link → Add reference link
```

#### **Media Router** (`backend/routes/media.py`)
```
POST   /media/upload       → Upload image
GET    /media/{filename}   → Get image
DELETE /media/{filename}   → Delete image
```

---

### 3. **Agent Orchestration** (`backend/agents/`)

**Framework:** LangGraph (Multi-Agent Orchestration)

**State Machine Flow:**
```
START
  ↓
NEWS_FETCH_AGENT ─────→ CURATION_AGENT ─────→ CAPTION_AGENT
  (Get latest news)      (Filter & rank)      (Write captions)
                                              ↓
                                        TOPIC_NORMALIZER
                                        (Categorize news)
                                              ↓
                                        DETAILED_PROMPT
                                        (Expand prompts)
                                              ↓
                                        IMAGE_AGENT
                                        (Generate/edit images)
                                              ↓
                                        POST_GENERATION_AGENT
                                        (Finalize post)
                                              ↓
                                        QA_AGENT
                                        (Validate content)
                                              ↓
                                        LINKEDIN_AGENT
                                        (Publish to LinkedIn)
                                              ↓
END
```

**Agent Details:**

| Agent | Purpose | Key Actions |
|-------|---------|-------------|
| **NewssFetchAgent** | Daily news ingestion | DuckDuckGo search, Google CSE fallback, dedup |
| **CurationAgent** | Content filtering | Relevance scoring, topic filtering, ranking |
| **CaptionAgent** | Post writing | Gemini API calls, hashtag generation, validation |
| **ImageAgent** | Visual content | Gemini Vision, image generation, style application |
| **LinkedInAgent** | Social publishing | OAuth token refresh, post API, error handling |
| **DocumentReaderAgent** | Content parsing | PDF extraction, text summarization |
| **URLReaderAgent** | Web scraping | HTTP requests, HTML parsing, content extraction |
| **TopicNormalizerAgent** | Categorization | Tag mapping, category standardization |
| **DetailedPromptAgent** | Prompt enhancement | Context expansion, template application |
| **NewssuggestionAgent** | Recommendations | Personalized article ranking |
| **PostGenerationAgent** | Content assembly | Multi-step workflow orchestration |
| **QAAgent** | Quality control | Content validation, fact-checking |
| **LinkedInBlogAgent** | Blog generation | Long-form content creation |
| **VisualPlanningAgent** | Image strategy | Style selection, composition planning |

---

### 4. **Database Layer** (`backend/db/`)

**ORM:** SQLAlchemy (Async with asyncpg)
**Database:** PostgreSQL

**Core Models:**

```
┌─────────────────────────────────┐
│         User Model              │
├─────────────────────────────────┤
│ • id (PK)                       │
│ • username (Unique)             │
│ • email (Unique)                │
│ • hashed_password               │
│ • created_at                    │
│ • updated_at                    │
│ • is_active                     │
│                                 │
│ Relations:                      │
│ → LinkedInAccounts (1:Many)     │
│ → Products (1:Many)             │
│ → News (1:Many)                 │
│ → Posts (1:Many)                │
└─────────────────────────────────┘
           │
           ├─────────────────────┐
           ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│ LinkedInAccount      │  │ Product              │
├──────────────────────┤  ├──────────────────────┤
│ • id (PK)            │  │ • id (PK)            │
│ • user_id (FK)       │  │ • user_id (FK)       │
│ • linkedin_id        │  │ • name               │
│ • access_token       │  │ • description        │
│ • refresh_token      │  │ • category           │
│ • encrypted          │  │ • image_url          │
│ • expires_at         │  │ • reference_links    │
│ • profile_name       │  │ • collateral_path    │
│ • profile_image      │  │ • created_at         │
│                      │  │ • updated_at         │
└──────────────────────┘  └──────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│         News Model               │
├──────────────────────────────────┤
│ • id (PK)                        │
│ • title                          │
│ • content_summary                │
│ • source_url                     │
│ • source_domain                  │
│ • published_at                   │
│ • fetched_at                     │
│ • category                       │
│ • relevance_score                │
│ • is_curated                     │
│                                  │
│ Relations:                       │
│ → Posts (1:Many)                 │
│ → Processing (1:Many)            │
└──────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│         Post Model               │
├──────────────────────────────────┤
│ • id (PK)                        │
│ • user_id (FK)                   │
│ • linkedin_account_id (FK)       │
│ • news_id (FK)                   │
│ • caption                        │
│ • hashtags                       │
│ • image_url                      │
│ • image_style                    │
│ • status (draft/scheduled/pub)   │
│ • linkedin_post_id               │
│ • published_at                   │
│ • created_at                     │
│ • updated_at                     │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│      Queue Model                 │
├──────────────────────────────────┤
│ • id (PK)                        │
│ • user_id (FK)                   │
│ • job_type                       │
│ • status (pending/processing)    │
│ • input_data (JSON)              │
│ • output_data (JSON)             │
│ • error_message                  │
│ • created_at                     │
│ • started_at                     │
│ • completed_at                   │
│ • priority                       │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│    Processing Model              │
├──────────────────────────────────┤
│ • id (PK)                        │
│ • news_id (FK)                   │
│ • step (fetch/curate/generate)   │
│ • status (pending/success)       │
│ • details (JSON)                 │
│ • timestamp                      │
└──────────────────────────────────┘
```

---

### 5. **External API Integrations**

#### **Google Gemini 2.0 Flash API**
```python
# Text Generation
POST https://api.google.ai/v1/models/gemini-2.0-flash:generateContent
• News caption generation
• Content expansion
• Caption refinement

# Image Generation
POST https://api.google.ai/v1/models/gemini-2.0-flash-vision:generateContent
• Post image creation
• Style-specific variations
• Image editing/enhancement
```

#### **LinkedIn OAuth 2.0**
```
Authorization Code Flow:
1. Redirect user to LinkedIn login
2. Receive authorization code
3. Exchange for access_token
4. Store encrypted token in database
5. Use token to publish posts via LinkedIn API

Permissions:
• r_liteprofile (profile info)
• r_basicprofile (basic profile)
• w_member_social (post creation)
```

#### **DuckDuckGo Search API**
```python
GET https://api.duckduckgo.com/
• Daily news fetching
• No authentication required
• JSON response parsing
• Fallback for failed Google searches
```

#### **Google Custom Search Engine**
```
Fallback news source when DuckDuckGo fails
• Requires API key + custom search ID
• Used for more refined search results
• Rate limited (100 queries/day free tier)
```

#### **Gmail SMTP**
```
SMTP Server: smtp.gmail.com:587
• Email notifications for scheduled posts
• Error alerts for failed jobs
• Daily summary emails
```

---

## Data Flow Diagrams

### Daily News Processing Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. Daily News Fetch (Scheduled at 6 AM UTC)                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   NewssFetchAgent                                                    │
│   ├─→ DuckDuckGo API (search keywords)                              │
│   │   ↓ Success: Parse JSON, extract articles                       │
│   │   ↑ Failure: Fallback to Google CSE                             │
│   └─→ Google CSE (secondary search)                                 │
│       ↓                                                              │
│   Deduplicate & store in PostgreSQL News table                      │
│       ↓                                                              │
│   Log processing status in Processing table                         │
│       ↓                                                              │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 2. User Selects Article & Generates Post                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User clicks "Generate Post" → Frontend sends POST to /queue       │
│       ↓                                                              │
│   Backend creates Queue entry with status=pending                   │
│       ↓                                                              │
│   LangGraph state machine starts (Agent Orchestration)              │
│       ↓                                                              │
│   TopicNormalizerAgent: Categorize article                          │
│       ↓                                                              │
│   DetailedPromptAgent: Expand user's custom prompt                  │
│       ↓                                                              │
│   CaptionAgent: Generate LinkedIn caption with Gemini API           │
│       ├─→ Calls Gemini 2.0 Flash                                    │
│       ├─→ Validates length & tone                                   │
│       └─→ Adds hashtags                                             │
│       ↓                                                              │
│   ImageAgent: Generate matching image                               │
│       ├─→ Calls Gemini 2.0 Flash for prompt generation              │
│       ├─→ Gemini Vision API for image creation                      │
│       ├─→ Download and save to storage                              │
│       └─→ Apply user-selected style                                 │
│       ↓                                                              │
│   QAAgent: Validate final post                                      │
│       ├─→ Check caption length                                      │
│       ├─→ Verify image compatibility                                │
│       └─→ Detect brand policy violations                            │
│       ↓                                                              │
│   Update Post table with generated caption & image                  │
│       ↓                                                              │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 3. Post Publishing (User-Triggered or Scheduled)                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User clicks "Publish" or scheduled time triggers                  │
│       ↓                                                              │
│   LinkedInAgent: Publish via LinkedIn API                           │
│       ├─→ Refresh OAuth token if expired                            │
│       ├─→ POST /posts endpoint with caption & image                 │
│       ├─→ LinkedIn returns post_id                                  │
│       └─→ Handle rate limiting (429 errors)                         │
│       ↓                                                              │
│   Update Post table: status=published, linkedin_post_id=XXX         │
│       ↓                                                              │
│   EmailSender: Send confirmation email                              │
│       ├─→ Post URL                                                  │
│       ├─→ LinkedIn account                                          │
│       └─→ Next scheduled post                                       │
│       ↓                                                              │
│   Log success in Processing table                                   │
│       ↓                                                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Authentication & Security

### JWT Token Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Registration/Login                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Frontend: POST /auth/login {username, password}                 │
│   ↓                                                              │
│ Backend (security.py):                                          │
│   ├─→ Fetch user from database                                  │
│   ├─→ Verify password with bcrypt.verify()                      │
│   ├─→ Generate JWT token (default 24h expiry)                   │
│   └─→ Return {access_token, token_type: "bearer"}              │
│   ↓                                                              │
│ Frontend: Store token in localStorage                           │
│   ↓                                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. Protected API Requests                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Frontend: GET /products (with Authorization header)             │
│   ├─→ Authorization: Bearer {jwt_token}                         │
│   ↓                                                              │
│ Backend (Depends: get_current_user):                            │
│   ├─→ Extract token from header                                 │
│   ├─→ Decode JWT with SECRET_KEY                               │
│   ├─→ Verify signature & expiration                             │
│   ├─→ Fetch user from payload.sub (user_id)                     │
│   └─→ Inject user into route handler                            │
│   ↓                                                              │
│ Route Handler: @app.get("/products")                            │
│   ├─→ Receives user object                                      │
│   ├─→ Query database with user_id                               │
│   └─→ Return user's products only                               │
│   ↓                                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. OAuth Integration (LinkedIn)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Frontend: User clicks "Connect LinkedIn"                        │
│   ↓                                                              │
│ Frontend: Redirects to LinkedIn OAuth endpoint                  │
│   └─→ https://www.linkedin.com/oauth/v2/authorization           │
│       ?client_id={CLIENT_ID}                                    │
│       &redirect_uri={CALLBACK_URL}                              │
│       &response_type=code                                       │
│       &scope=r_liteprofile%20w_member_social                    │
│   ↓                                                              │
│ User: Approves access on LinkedIn                               │
│   ↓                                                              │
│ LinkedIn: Redirects to /linkedin/oauth with code                │
│   ↓                                                              │
│ Backend (linkedin.py):                                          │
│   ├─→ Exchange code for access_token                            │
│   ├─→ POST to LinkedIn token endpoint                           │
│   ├─→ Encrypt tokens with Fernet symmetric key                  │
│   ├─→ Store in LinkedInAccount table                            │
│   └─→ Redirect to success page                                  │
│   ↓                                                              │
│ Frontend: Display "LinkedIn Connected"                          │
│   ↓                                                              │
└─────────────────────────────────────────────────────────────────┘
```

### Password & Token Encryption

```
Storage Layer:
├─ User passwords: bcrypt (cost=12, salted hashing)
├─ LinkedIn tokens: Fernet symmetric encryption (ENCRYPTION_KEY env var)
├─ JWT secret: SECRET_KEY env variable (256+ bits)
└─ Database connection: SSL/TLS to PostgreSQL

Environment Variables (.env file):
├─ DATABASE_URL=postgresql+asyncpg://user:pass@host/db
├─ SECRET_KEY={random_256_bit_key}
├─ ENCRYPTION_KEY={fernet_key}
├─ LINKEDIN_CLIENT_ID={oauth_client_id}
├─ LINKEDIN_CLIENT_SECRET={oauth_secret}
├─ GOOGLE_API_KEY={gemini_api_key}
└─ GMAIL_PASSWORD={app_specific_password}
```

---

## Frontend Architecture

### Component Hierarchy

```
index.html
├── <nav> Navigation Bar
│   ├── Logo
│   ├── User Menu
│   └── Settings Link
│
├── <main id="app">
│   ├── ────────────────────────────────────────
│   │ Page 1: News Feed
│   ├── ────────────────────────────────────────
│   │   ├── News List Container
│   │   │   └── News Items (dynamic)
│   │   │       ├── Article Title
│   │   │       ├── Summary
│   │   │       ├── Source & Time
│   │   │       └── Actions (View, Generate, Share)
│   │   │
│   │   └── Filters & Controls
│   │       ├── Category Filter
│   │       ├── Date Range
│   │       └── Sort Options
│   │
│   ├── ────────────────────────────────────────
│   │ Page 2: Post Editor
│   ├── ────────────────────────────────────────
│   │   ├── Caption Editor
│   │   │   ├── Textarea (editable)
│   │   │   ├── Character counter
│   │   │   └── Suggestion button
│   │   │
│   │   ├── Image Editor (image_options_modal.js)
│   │   │   ├── Image Preview
│   │   │   ├── Style Selector (dropdown)
│   │   │   ├── Edit Tools
│   │   │   └── Regenerate Button
│   │   │
│   │   └── Post Actions
│   │       ├── Save Draft
│   │       ├── Schedule
│   │       └── Publish Now
│   │
│   ├── ────────────────────────────────────────
│   │ Page 3: LinkedIn Accounts
│   ├── ────────────────────────────────────────
│   │   ├── Connected Accounts List
│   │   │   └── Account Item
│   │   │       ├── Profile Image
│   │   │       ├── Name
│   │   │       └── Disconnect Button
│   │   │
│   │   └── Connect New Account
│   │       └── "Connect LinkedIn" Button
│   │
│   ├── ────────────────────────────────────────
│   │ Page 4: Product Profiles
│   ├── ────────────────────────────────────────
│   │   ├── Products List
│   │   │   └── Product Item
│   │   │       ├── Name & Description
│   │   │       ├── Category
│   │   │       ├── Links
│   │   │       ├── Edit Button
│   │   │       └── Delete Button
│   │   │
│   │   └── Create New Product
│   │       └── Form Modal
│   │
│   ├── ────────────────────────────────────────
│   │ Page 5: Scheduler
│   ├── ────────────────────────────────────────
│   │   ├── Calendar View
│   │   │   └── Scheduled Posts
│   │   │       ├── Post Preview
│   │   │       ├── Date/Time
│   │   │       └── Actions (Edit, Delete, Publish)
│   │   │
│   │   └── Time Picker
│   │       ├── Date Input
│   │       ├── Hour Select
│   │       └── Timezone
│   │
│   ├── ────────────────────────────────────────
│   │ Page 6: Queue & Status
│   ├── ────────────────────────────────────────
│   │   ├── Active Jobs List
│   │   │   └── Job Item
│   │   │       ├── Status Icon (pending/processing)
│   │   │       ├── Job Type
│   │   │       ├── Progress Bar
│   │   │       └── Logs
│   │   │
│   │   └── Completed Jobs History
│   │       └── Job Item (archive view)
│   │
│   └── ────────────────────────────────────────
│    Page 7: Settings
│    ────────────────────────────────────────
│       ├── Account Settings
│       │   ├── Username/Email
│       │   └── Change Password
│       │
│       ├── API Keys
│       │   └── Regenerate Button
│       │
│       └── Notifications
│           ├── Email Notifications Toggle
│           └── Notification Frequency
│
└── Modals & Overlays
    ├── image_options_modal.js (Image editor)
    ├── upload_modal.js (File upload)
    └── Global Error/Success Toasts
```

### JavaScript Module Relationships

```
index.html
├── api.js (API client wrapper)
│   ├── Functions: fetchNews, createPost, publishPost, etc.
│   └── Handles: Auth headers, error handling, JSON parsing
│
├── blog_generator.js (Blog content generation)
│   └── Depends on: api.js
│
├── image_options_modal.js (Image editing UI)
│   ├── Depends on: api.js, styles.css
│   └── Handles: Image preview, style selection, regeneration
│
├── linkedin_accounts.js (OAuth account management)
│   ├── Depends on: api.js
│   └── Handles: Connect/disconnect, account sync
│
├── products.js (Product profile CRUD)
│   ├── Depends on: api.js
│   └── Handles: Create, update, delete products
│
├── queue_panel.js (Job queue display)
│   ├── Depends on: api.js
│   ├── Polling: GET /queue/jobs every 5 seconds
│   └── Handles: Job status updates, logs
│
├── scheduler.js (Post scheduling)
│   ├── Depends on: api.js
│   └── Handles: Calendar, date picker, scheduling
│
├── settings.js (User preferences)
│   ├── Depends on: api.js
│   └── Handles: Profile, notifications, API keys
│
├── swipe.js (Touch gestures)
│   └── Handles: Swipe navigation between pages
│
└── upload_modal.js (File upload UI)
    ├── Depends on: api.js
    └── Handles: Image/document upload, preview
```

---

## Deployment Architecture

### Production Environment (Render)

```
┌──────────────────────────────────────────────────────────────────┐
│                      RENDER FREE TIER                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Backend Service (Gunicorn + Uvicorn)                       │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker   │ │
│  │ Port: 10000 (internal)                                     │ │
│  │ Health Check: GET / (every 30s)                            │ │
│  │ Auto-deploy: On push to main branch                        │ │
│  │ Build: pip install -r requirements.txt                     │ │
│  │ Start: python run.py                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PostgreSQL Database (Managed by Render)                    │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Version: PostgreSQL 14                                     │ │
│  │ Connections: Connection pooling (10 max)                   │ │
│  │ Backups: Daily snapshots                                   │ │
│  │ SSL: Enforced for all connections                          │ │
│  │ Region: Virginia (US-EAST)                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Static Files & Frontend (Nginx)                            │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Served from: frontend/ directory                           │ │
│  │ Configuration: etc/nginx/sites-available                   │ │
│  │ Cache: Browser caching headers (24h for .js, .css)        │ │
│  │ Compression: Gzip enabled                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Background Jobs & Scheduled Tasks                          │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Method: APScheduler (Python task scheduler)                │ │
│  │ Daily News Fetch: 6:00 AM UTC                              │ │
│  │ Cron Job: Run in main FastAPI app process                  │ │
│  │ Fallback: Manual trigger via admin endpoint                │ │
│  │ Logs: Application logs (Render dashboard)                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
    Environment Variables    External APIs            CDN/Cache
    ├─ DATABASE_URL           ├─ Google Gemini      ├─ Cloudflare
    ├─ SECRET_KEY             ├─ LinkedIn OAuth     └─ Image CDN
    ├─ GOOGLE_API_KEY         ├─ DuckDuckGo
    └─ ENCRYPTION_KEY         └─ Gmail SMTP
```

### Deployment Pipeline

```
1. Developer pushes to main branch on GitHub
   ↓
2. GitHub Actions (or Render auto-deploy):
   ├─ Run tests
   ├─ Lint code
   ├─ Build Docker image (if applicable)
   └─ Push to registry
   ↓
3. Render detects new push:
   ├─ Pulls latest code
   ├─ Builds environment: pip install -r requirements.txt
   ├─ Runs migrations: alembic upgrade head
   └─ Starts service: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
   ↓
4. Health checks pass → Service goes live
   ↓
5. Old service terminates (zero-downtime deploy)
```

### Database Migrations

```
Alembic (Database versioning)
├─ init: alembic init
├─ create migration: alembic revision --autogenerate -m "description"
├─ apply: alembic upgrade head
├─ rollback: alembic downgrade -1
└─ history: alembic history

Migration files stored in: alembic/versions/
Current: 070bb1f8212e_initial_migration.py
```

---

## System Monitoring & Logging

### Application Logging

```python
# Structured Logging
import logging
from backend.config import logger

logger.info(f"User {user_id} created post")
logger.error(f"Failed to publish to LinkedIn: {error}")
logger.warning(f"API rate limit approaching")

# Log Levels
├─ DEBUG: Detailed execution flow
├─ INFO: Normal operational events
├─ WARNING: Unexpected but recoverable
├─ ERROR: Recoverable errors
└─ CRITICAL: System failures

# Output Destinations
├─ Console: Standard output (Render logs)
├─ File: agent_log.txt (local debugging)
└─ External: Sentry (optional error tracking)
```

### Health Checks

```
GET /health
├─ Database connection: SELECT 1
├─ Gemini API: HEAD request to API endpoint
├─ LinkedIn OAuth: Validate stored tokens
└─ Response: 200 OK {status: "healthy"}

Frequency: Every 30 seconds by Render load balancer
```

---

## Performance Considerations

### Optimization Strategies

1. **Database Optimization**
   - Connection pooling (asyncpg with SQLAlchemy async)
   - Query optimization with indexed columns
   - Prepared statements to prevent SQL injection

2. **API Response Caching**
   - Cache news items (1 hour)
   - Cache product profiles (5 minutes)
   - Cache LinkedIn account info (24 hours)

3. **Async/Await Processing**
   - All I/O operations non-blocking
   - Concurrent API calls to Gemini, LinkedIn, DuckDuckGo
   - Queue processing in background tasks

4. **Image Optimization**
   - Compress images before storage
   - Serve via CDN (Cloudflare optional)
   - Generate thumbnails for previews

5. **Frontend Performance**
   - Lazy load images
   - Minify CSS/JavaScript
   - Service workers for offline functionality (optional)

---

## Security Best Practices

### Implemented Measures

- ✅ HTTPS/TLS for all communications
- ✅ JWT token-based authentication
- ✅ bcrypt password hashing
- ✅ Environment variable for secrets
- ✅ CORS restriction to domain
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Rate limiting (optional: Redis + slowapi)
- ✅ OAuth 2.0 for third-party integrations
- ✅ Encrypted token storage (Fernet)
- ✅ Input validation on all endpoints

### Recommended Additions

- 🔄 Implement request rate limiting
- 🔄 Add WAF (Web Application Firewall) rules
- 🔄 Enable two-factor authentication (2FA)
- 🔄 Regular security audits
- 🔄 Dependency scanning (Dependabot)
- 🔄 Secret rotation policy

---

## Troubleshooting Guide

### Common Issues

**Issue: News fetch fails at 6 AM**
- Check DuckDuckGo API availability
- Verify Google CSE fallback credentials
- Check application logs: `agent_log.txt`

**Issue: LinkedIn post publish fails**
- Refresh LinkedIn OAuth tokens (automatic retry)
- Check rate limiting: LinkedIn allows 10 posts/24h for free accounts
- Verify post content doesn't violate LinkedIn policy

**Issue: Database connection timeout**
- Check PostgreSQL connection pool settings
- Verify DATABASE_URL environment variable
- Check Render PostgreSQL service status

**Issue: Gemini API errors**
- Verify GOOGLE_API_KEY is set
- Check API quota and billing
- Monitor API response times

**Issue: Frontend not loading**
- Clear browser cache
- Check static file paths in Nginx config
- Verify CSS/JavaScript bundle builds

---

## Future Enhancements

1. **Machine Learning**
   - Content personalization based on user engagement
   - Auto-generate post timing recommendations
   - Sentiment analysis on published posts

2. **Additional Platforms**
   - Twitter/X integration
   - Instagram captions + carousel images
   - TikTok short-form content

3. **Team Collaboration**
   - Approval workflows for posts
   - Content calendar sharing
   - Comment collaboration

4. **Analytics**
   - Post performance tracking
   - Engagement metrics
   - ROI calculation per product

5. **Advanced AI**
   - Custom model fine-tuning
   - Brand voice training
   - Automated A/B testing

---

Generated: January 15, 2026
Last Updated: Architecture Documentation Created
