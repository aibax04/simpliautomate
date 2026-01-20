"""
Social Listening Agent
Fetches content from DuckDuckGo and official APIs based on tracking rules and stores matches
Supports platform-specific searches for Twitter, LinkedIn, Reddit, and News APIs
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ddgs import DDGS
import hashlib
import re
import requests
from bs4 import BeautifulSoup

# Import social ingestion services
from backend.services.ingestion_service import get_ingestion_service
from backend.services.connectors import Platform

# Import email functionality
from backend.utils.email_sender import send_email


async def send_email_async(to_email: str, subject: str, body: str):
    """Send email asynchronously"""
    try:
        # Run email sending in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, send_email, to_email, subject, body
        )
    except Exception as e:
        print(f"[EMAIL ASYNC] Failed to send email to {to_email}: {e}")

logger = logging.getLogger(__name__)


class SocialListeningAgent:
    """Agent that fetches social media content based on tracking rules"""

    # Platform-specific site filters for DuckDuckGo
    PLATFORM_SITES = {
        "twitter": ["site:twitter.com", "site:x.com"],
        "linkedin": ["site:linkedin.com/posts", "site:linkedin.com/feed"],
        "reddit": ["site:reddit.com"],
        "news": []  # No site filter for general news
    }

    # Platforms that support official APIs
    API_SUPPORTED_PLATFORMS = {
        "twitter": Platform.TWITTER.value,
        "news": Platform.NEWS.value
    }
    
    def __init__(self):
        self.search_delay = 1.5  # Seconds between searches to avoid rate limiting

    def get_frequency_limit(self, frequency: str) -> int:
        """
        Get the maximum number of results to return based on frequency
        """
        limits = {
            "realtime": 10,  # Focus on breaking news, fewer but more urgent
            "hourly": 18,    # Balanced - 15-20 range, settled on 18
            "daily": 25,     # More comprehensive for daily digests
            "weekly": 50     # Most comprehensive for weekly reports
        }
        return limits.get(frequency, 18)  # Default to hourly limit
    
    async def search_official_apis(self, platform: str, keywords: List[str], handles: List[str], max_results: int = 15) -> List[Dict]:
        """
        Search using official APIs for supported platforms (Twitter, News)
        Returns results in the same format as DuckDuckGo for consistency
        """
        results = []

        if platform not in self.API_SUPPORTED_PLATFORMS:
            return results

        try:
            ingestion_service = await get_ingestion_service()

            # Build query based on platform
            if platform == "twitter":
                # Build Twitter query from keywords and handles
                query_parts = []

                # Add handles (from: syntax)
                if handles:
                    for handle in handles[:2]:  # Limit to avoid query complexity
                        clean_handle = handle.replace("@", "").strip()
                        query_parts.append(f"from:{clean_handle}")

                # Add keywords
                if keywords:
                    keyword_part = " OR ".join(keywords[:3])  # Combine keywords
                    query_parts.append(f"({keyword_part})")

                # Combine with AND logic if both exist
                if query_parts:
                    api_query = " ".join(query_parts)
                else:
                    api_query = " OR ".join(keywords[:3]) if keywords else ""

            elif platform == "news":
                # Build News query
                query_parts = []

                # Add keywords
                if keywords:
                    query_parts.extend(keywords[:3])

                # Add handles/sources
                if handles:
                    for handle in handles[:2]:
                        clean_handle = handle.replace("@", "").strip()
                        query_parts.append(clean_handle)

                api_query = " OR ".join(query_parts) if query_parts else ""

            if not api_query:
                return results

            # Run ingestion task
            rule_config = {
                "rule_id": f"social_listening_{platform}_{hash(api_query)}",
                "platform": platform,
                "query": api_query,
                "max_posts_per_run": max_results,
                "enabled": True
            }

            api_result = await ingestion_service.run_ingestion_task(rule_config)

            # Convert API results to DuckDuckGo-like format
            if api_result.get("success", False):
                for post_data in api_result.get("posts", []):
                    # Convert UnifiedPost format to DuckDuckGo-like format
                    results.append({
                        "title": post_data.get("content", "")[:100] + "..." if len(post_data.get("content", "")) > 100 else post_data.get("content", ""),
                        "body": post_data.get("content", ""),
                        "href": post_data.get("url", ""),
                        "source": post_data.get("author", ""),
                        "platform": platform,
                        "from_api": True  # Mark as coming from official API
                    })

            print(f"[SocialListening] Official {platform} API search returned {len(results)} results")

        except Exception as e:
            print(f"[SocialListening] Official {platform} API search error: {e}")

        return results

    def search_duckduckgo(self, query: str, max_results: int = 15) -> List[Dict]:
        """
        Search DuckDuckGo for the given query
        """
        results = []
        try:
            with DDGS() as ddgs:
                ddgs_results = ddgs.text(query, max_results=max_results)
                for r in ddgs_results:
                    results.append({
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "href": r.get("href", ""),
                        "source": r.get("source", ""),
                        "from_api": False  # Mark as coming from search
                    })
            print(f"[SocialListening] DuckDuckGo search for '{query}' returned {len(results)} results")
        except Exception as e:
            print(f"[SocialListening] DuckDuckGo search error: {e}")
        return results
    
    def fetch_authentic_content(self, url: str, platform: str, original_title: str = "", original_body: str = "") -> str:
        """
        Fetch authentic full content from a social media URL.
        This goes beyond the search snippet to get the actual post content.
        
        Args:
            url: The URL of the social media post
            platform: The platform type (twitter, linkedin, reddit, news)
            original_title: The title from search (fallback)
            original_body: The body from search (fallback)
            
        Returns:
            The full authentic content of the post
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Set a reasonable timeout
            response = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"[SocialListening] URL fetch failed ({response.status_code}): {url}")
                # Return combination of title and body as fallback
                return self._format_fallback_content(original_title, original_body, platform)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content based on platform
            content = ""
            
            if platform == "twitter":
                content = self._extract_twitter_content(soup, url)
            elif platform == "linkedin":
                content = self._extract_linkedin_content(soup, url)
            elif platform == "reddit":
                content = self._extract_reddit_content(soup, url)
            else:  # news
                content = self._extract_news_content(soup, url)
            
            # If extraction failed, use the fallback
            if not content or len(content.strip()) < 30:
                content = self._format_fallback_content(original_title, original_body, platform)
            
            # Clean and limit content length
            content = self._clean_extracted_content(content)
            
            return content
            
        except requests.Timeout:
            print(f"[SocialListening] URL fetch timeout: {url}")
            return self._format_fallback_content(original_title, original_body, platform)
        except Exception as e:
            print(f"[SocialListening] Error fetching authentic content from {url}: {e}")
            return self._format_fallback_content(original_title, original_body, platform)
    
    def _extract_twitter_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract tweet content from Twitter/X page"""
        content = ""
        
        # Try multiple selectors for tweet content
        # Twitter uses article tags for tweets
        tweet_selectors = [
            'article[data-testid="tweet"]',
            'div[data-testid="tweetText"]',
            'div[lang]',  # Tweet text usually has a lang attribute
            'article div[dir="auto"]',
            '.tweet-text'
        ]
        
        for selector in tweet_selectors:
            elements = soup.select(selector)
            if elements:
                # Get text from the first matching element
                for elem in elements[:1]:  # Take first tweet
                    text = elem.get_text(separator=' ', strip=True)
                    if text and len(text) > 20:
                        content = text
                        break
            if content:
                break
        
        # Also try meta tags for Twitter cards
        if not content:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                content = meta_desc.get('content')
            
            # Try og:description
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                desc = og_desc.get('content')
                if len(desc) > len(content or ''):
                    content = desc
        
        return content
    
    def _extract_linkedin_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract post content from LinkedIn"""
        content = ""
        
        # LinkedIn post selectors
        linkedin_selectors = [
            'div.feed-shared-update-v2__description',
            'div.feed-shared-inline-show-more-text',
            'span.break-words',
            'div[data-id] .feed-shared-text',
            '.share-update-card__update-text',
            'div.attributed-text-segment-list__content'
        ]
        
        for selector in linkedin_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:1]:
                    text = elem.get_text(separator=' ', strip=True)
                    if text and len(text) > 30:
                        content = text
                        break
            if content:
                break
        
        # Try meta description
        if not content:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                content = meta_desc.get('content')
            
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                desc = og_desc.get('content')
                if len(desc) > len(content or ''):
                    content = desc
        
        return content
    
    def _extract_reddit_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract post content from Reddit"""
        content = ""
        
        # Reddit post selectors
        reddit_selectors = [
            'div[data-test-id="post-content"]',
            'div[slot="text-body"]',
            'div.md',  # Markdown content
            '[data-click-id="text"] .RichTextJSON-root',
            'shreddit-post .md',
            '.Post .RichTextJSON-root'
        ]
        
        for selector in reddit_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:1]:
                    text = elem.get_text(separator=' ', strip=True)
                    if text and len(text) > 30:
                        content = text
                        break
            if content:
                break
        
        # Also try post title for Reddit (sometimes the title IS the content)
        if not content or len(content) < 50:
            title_elem = soup.select_one('h1, shreddit-post h1, [slot="title"]')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text:
                    if content:
                        content = f"{title_text}\n\n{content}"
                    else:
                        content = title_text
        
        # Try meta description
        if not content:
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                content = og_desc.get('content')
        
        return content
    
    def _extract_news_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract article content from news sites"""
        content = ""
        
        # Remove script, style, and navigation elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'button']):
            element.decompose()
        
        # News article selectors (ordered by priority)
        news_selectors = [
            'article .article-body',
            'article .story-body',
            'div.article-content',
            'div.story-content',
            'div.entry-content',
            'div.post-content',
            'main article',
            'article',
            '.article-text',
            '.story-text',
            '[itemprop="articleBody"]'
        ]
        
        for selector in news_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:1]:
                    # Get all paragraphs within the article
                    paragraphs = elem.find_all('p')
                    if paragraphs:
                        texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                        # Take first 3-5 paragraphs to get the gist
                        content = ' '.join(texts[:4])
                        if len(content) > 100:
                            break
            if content and len(content) > 100:
                break
        
        # If no article content, try to get page title + description
        if not content or len(content) < 100:
            # Get title
            title = ""
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Get description
            desc = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                desc = meta_desc.get('content', '')
            if not desc:
                og_desc = soup.find('meta', attrs={'property': 'og:description'})
                if og_desc:
                    desc = og_desc.get('content', '')
            
            if title or desc:
                content = f"{title}\n\n{desc}" if title and desc else (title or desc)
        
        return content
    
    def _format_fallback_content(self, title: str, body: str, platform: str) -> str:
        """Format fallback content when URL fetch fails"""
        if body and len(body) > len(title or ''):
            return body.strip()
        elif title and body:
            return f"{title.strip()}\n\n{body.strip()}"
        elif title:
            return title.strip()
        elif body:
            return body.strip()
        return ""
    
    def _clean_extracted_content(self, content: str) -> str:
        """Clean and format extracted content"""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Remove common clutter phrases
        clutter_phrases = [
            'Sign in to continue',
            'Sign up',
            'Login to',
            'Create an account',
            'Already have an account',
            'Terms of Service',
            'Privacy Policy',
            'Cookie Policy',
            'Subscribe now',
            'Read more...',
            'Continue reading'
        ]
        
        for phrase in clutter_phrases:
            content = content.replace(phrase, '')
        
        # Limit to reasonable length (keep first ~1500 chars for comprehensive content)
        if len(content) > 1500:
            content = content[:1500] + '...'
        
        # Ensure minimum quality
        if len(content) < 30:
            return ""
        
        return content.strip()
    
    def clean_url(self, url: str) -> str:
        """
        Clean and resolve URL to get the direct link to the post.
        Removes tracking parameters and ensures it's a direct link.
        """
        if not url:
            return ""
        
        try:
            # Remove common tracking parameters
            tracking_params = [
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                'ref', 'src', 'source', 'via', 'from', 'fbclid', 'gclid', 'dclid',
                'mc_cid', 'mc_eid', 'trk', 'trkInfo', 'share', 'refId'
            ]
            
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            parsed = urlparse(url)
            
            # Parse query params and remove tracking ones
            if parsed.query:
                params = parse_qs(parsed.query)
                clean_params = {k: v for k, v in params.items() 
                               if k.lower() not in tracking_params}
                clean_query = urlencode(clean_params, doseq=True)
                url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, clean_query, parsed.fragment
                ))
            
            return url
            
        except Exception as e:
            print(f"[SocialListening] Error cleaning URL: {e}")
            return url
    
    def is_direct_post_url(self, url: str, platform: str) -> bool:
        """
        Check if the URL is a direct link to a post/status, not a search or profile page.
        """
        url_lower = url.lower()
        
        if platform == "twitter":
            # Twitter direct post URLs contain /status/ 
            # Good: twitter.com/user/status/123456
            # Bad: twitter.com/search?q=keyword, twitter.com/user (profile only)
            if "/status/" in url_lower:
                return True
            # Also allow individual tweet links from x.com
            if "x.com/" in url_lower and "/status/" in url_lower:
                return True
            # Profile pages can be useful for monitoring handles
            if "/search" not in url_lower and "/hashtag/" not in url_lower:
                # Check if it's a profile with potential posts
                parts = url_lower.split("/")
                # twitter.com/username format (could be profile with recent tweets)
                if len(parts) >= 4 and parts[-1] and parts[-1] not in ['followers', 'following', 'likes', 'lists']:
                    return True
            return False
            
        elif platform == "linkedin":
            # LinkedIn post URLs contain /posts/, /pulse/, /feed/update/
            # Good: linkedin.com/posts/username-activity-123456
            # Bad: linkedin.com/search/results/, linkedin.com/company/ (profile only)
            direct_patterns = ['/posts/', '/pulse/', '/feed/update/', '/in/']
            excluded_patterns = ['/search/', '/jobs/', '/learning/', '/premium/']
            
            if any(pattern in url_lower for pattern in excluded_patterns):
                return False
            if any(pattern in url_lower for pattern in direct_patterns):
                return True
            return False
            
        elif platform == "reddit":
            # Reddit post URLs contain /comments/
            # Good: reddit.com/r/subreddit/comments/123456/
            # Bad: reddit.com/search?q=, reddit.com/r/subreddit (just subreddit page)
            if "/comments/" in url_lower:
                return True
            # Allow subreddit top-level for monitoring subreddit mentions
            if "/r/" in url_lower and "/search" not in url_lower:
                return True
            return False
            
        else:  # news
            # For news, most article URLs are direct
            # Exclude search result pages
            excluded = ['/search', '/tag/', '/category/', '/author/', '/page/']
            if any(ex in url_lower for ex in excluded):
                return False
            return True
    
    def generate_external_id(self, url: str, title: str) -> str:
        """Generate a unique ID for deduplication"""
        content = f"{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def determine_platform(self, url: str) -> str:
        """Determine platform from URL"""
        url_lower = url.lower()
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        elif "linkedin.com" in url_lower:
            return "linkedin"
        elif "reddit.com" in url_lower:
            return "reddit"
        else:
            return "news"
    
    def extract_author_from_url(self, url: str, platform: str) -> tuple:
        """Extract author/handle from URL"""
        try:
            if platform == "twitter":
                # Extract @handle from twitter URLs
                parts = url.split("/")
                for i, part in enumerate(parts):
                    if part in ["twitter.com", "x.com"] and i + 1 < len(parts):
                        handle = parts[i + 1]
                        if handle and handle not in ["search", "hashtag", "i", "intent", "share"]:
                            return handle, f"@{handle}"
            elif platform == "reddit":
                if "/r/" in url:
                    parts = url.split("/r/")
                    if len(parts) > 1:
                        subreddit = parts[1].split("/")[0]
                        # Also try to get username if it's a post
                        if "/comments/" in url and "/user/" not in url:
                            return f"r/{subreddit}", f"r/{subreddit}"
                        return f"r/{subreddit}", f"r/{subreddit}"
                if "/user/" in url or "/u/" in url:
                    match = re.search(r'/u(?:ser)?/([^/]+)', url)
                    if match:
                        username = match.group(1)
                        return username, f"u/{username}"
            elif platform == "linkedin":
                # Try to extract name from LinkedIn URL
                if "/in/" in url:
                    parts = url.split("/in/")
                    if len(parts) > 1:
                        profile = parts[1].split("/")[0].split("?")[0]
                        name = profile.replace("-", " ").title()
                        return name, f"linkedin.com/in/{profile}"
                return "LinkedIn User", ""
        except:
            pass
        return "Unknown", ""
    
    def is_industry_relevant_content(self, content: str, title: str, author: str, platform: str) -> bool:
        """
        Filter out personal achievements and focus on industry-relevant content
        Returns True if content is industry-focused and valuable for competitive intelligence
        """
        combined_text = f"{title} {content}".lower()

        # Keywords that indicate PERSONAL achievements (FILTER OUT)
        personal_achievement_keywords = [
            # Awards and recognitions
            "award", "awarded", "winner", "winning", "honored", "recognition",
            "achievement", "accomplished", "milestone", "landmark", "breakthrough",

            # Personal promotions/announcements
            "promoted to", "appointed", "joined as", "new role", "new position",
            "celebrates", "celebrating", "congratulations", "congrats",

            # Personal accomplishments
            "achieved", "accomplished", "reached", "completed", "finished",
            "launched my", "built my", "created my", "developed my",

            # Personal news
            "birthday", "anniversary", "graduation", "retirement", "vacation",
            "holiday", "wedding", "marriage", "family", "personal",

            # Self-promotional
            "excited to announce", "proud to share", "thrilled to", "happy to",
            "pleased to", "delighted to", "honored to", "grateful to",

            # Individual-focused
            "i am", "i'm", "my journey", "my story", "my experience"
        ]

        # Keywords that indicate INDUSTRY news (KEEP)
        industry_keywords = [
            # Business developments
            "funding", "investment", "raised", "series", "valuation", "investors",
            "acquisition", "acquired", "merger", "partnership", "alliance",

            # Market news
            "market share", "competition", "competitor", "rival", "challenge",
            "market leader", "industry leader", "disruption", "innovation",

            # Company actions
            "launched new", "released", "announced", "unveiled", "introduced",
            "expanded", "grew", "scaled", "hired", "team expansion",

            # Industry trends
            "trend", "analysis", "report", "study", "research", "forecast",
            "growth", "decline", "increase", "decrease", "projection",

            # Competitive intelligence
            "vs", "versus", "compared to", "better than", "superior to",
            "leading", "top", "best", "worst", "ranking", "position",

            # Business context
            "industry", "market", "business", "company", "corporate",
            "enterprise", "startup", "venture", "capital", "revenue"
        ]

        # Check for personal achievement indicators (only reject INDIVIDUAL achievements)
        for keyword in personal_achievement_keywords:
            if keyword in combined_text:
                # Check if this is an INDIVIDUAL achievement (reject)
                individual_indicators = [
                    author.lower(), "i ", "my ", "me ", "he ", "she ", "they ",
                    "personally", "myself", "himself", "herself", "themselves",
                    "individual", "person", "people", "executive", "ceo", "cto",
                    "founder", "cofounder", "president", "chairman", "director"
                ]

                # Check if this is a COMPANY/ORGANIZATION achievement (allow)
                company_indicators = [
                    "company", "corporation", "organization", "org", "inc", "ltd", "llc",
                    "corp", "group", "enterprise", "business", "firm", "agency",
                    "startup", "venture", "brand", "platform", "solution", "product",
                    "announced", "launched", "released", "unveiled", "introduced",
                    "achieved", "reached", "accomplished", "completed", "delivered"
                ]

                # If it has individual indicators AND lacks company indicators, reject
                has_individual = any(indicator in combined_text for indicator in individual_indicators)
                has_company = any(indicator in combined_text for indicator in company_indicators)

                if has_individual and not has_company:
                    print(f"[FILTER] Rejected individual achievement: {title[:50]}...")
                    return False
                elif has_company:
                    # Company achievement - allow it
                    print(f"[FILTER] Allowed company achievement: {title[:50]}...")
                    continue

        # Check for industry relevance (ACCEPT if found)
        industry_score = 0
        for keyword in industry_keywords:
            if keyword in combined_text:
                industry_score += 1

        # Must have at least 1 industry keyword OR be from news sources
        if platform == "news" or industry_score >= 1:
            return True

        # For social platforms, be more selective
        if platform in ["twitter", "linkedin", "reddit"]:
            # Must have clear business/industry context
            business_context = [
                "industry", "market", "business", "company", "corporate",
                "enterprise", "startup", "venture", "capital", "funding"
            ]
            if any(context in combined_text for context in business_context):
                return True

            # Reject ambiguous content
            return False

        return False

    def is_content_recent(self, content: str, title: str) -> bool:
        """
        Check if content appears to be recent based on keywords and context
        """
        combined_text = f"{title} {content}".lower()

        # Strong indicators of future content - focused on 2026 and beyond
        future_years = ["2026", "2027", "2028", "2029", "2030"]
        recent_indicators = [
            # Future years (primary focus)
            "2026", "2027", "2028", "2029", "2030",
            # Current/future time indicators
            "today", "yesterday", "this week", "this month", "this year",
            "recent", "latest", "breaking", "just now", "just announced",
            "new report", "new study", "new analysis", "new data", "upcoming",
            "quarterly results", "annual report", "q1", "q2", "q3", "q4",
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
            # Future-focused terms
            "forecast", "prediction", "expected", "projected", "anticipated",
            "next year", "coming year", "future outlook"
        ]

        # Indicators of old/past content (reject if found)
        old_indicators = [
            "2019", "2020", "2021", "2022", "2023", "2024", "2025",
            "last year", "two years ago", "three years ago", "four years ago", "five years ago",
            "decade ago", "in 201", "in 202", "back in", "years ago", "ago",
            "previously", "formerly", "past", "historic", "historical"
        ]

        # Check for old content indicators (reject)
        for old_indicator in old_indicators:
            if old_indicator in combined_text:
                # If it mentions past years (before 2026), likely old content
                past_years = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
                if any(year in combined_text for year in past_years):
                    print(f"[RECENCY] Rejected past content (mentions pre-2026 year): {title[:50]}...")
                    return False

        # Check for future indicators (accept if found)
        future_score = 0
        for indicator in recent_indicators:
            if indicator in combined_text:
                future_score += 1

        # If we have future years mentioned OR 2+ future indicators, accept
        if any(year in combined_text for year in future_years) or future_score >= 2:
            return True

        # For news content, be more lenient - news sources tend to be current
        news_keywords = ["news", "report", "analysis", "study", "announcement"]
        if any(keyword in combined_text for keyword in news_keywords):
            return True

        # Default: accept (we can't be 100% sure from text alone)
        return True

    def calculate_content_quality_score(self, content: str, title: str) -> int:
        """
        Score content quality for competitive intelligence
        Returns 0-10 score (higher = more valuable)
        """
        score = 5  # Base score

        text = f"{title} {content}".lower()

        # High value indicators (+2-3 points)
        if any(word in text for word in ["funding", "acquisition", "partnership", "ipo", "merger"]):
            score += 3
        elif any(word in text for word in ["market share", "competition", "competitor", "vs", "versus"]):
            score += 2

        # Medium value (+1-2 points)
        if any(word in text for word in ["growth", "expansion", "launch", "product", "revenue"]):
            score += 2
        elif any(word in text for word in ["analysis", "report", "study", "forecast"]):
            score += 1

        # Negative indicators (-1-2 points)
        if any(word in text for word in ["personal", "achievement", "award", "congratulations"]):
            score -= 2
        elif any(word in text for word in ["birthday", "vacation", "family", "celebration"]):
            score -= 1

        return max(0, min(10, score))

    def clean_content(self, title: str, body: str, platform: str) -> str:
        """
        Clean and format content based on platform
        Remove news site clutter and focus on actual content
        """
        # Remove common news site names from title
        news_sites = [
            "- The Hindu", "| Reuters", "- Reuters", "| BBC", "- BBC",
            "| CNN", "- CNN", "| Forbes", "- Forbes", "| TechCrunch",
            "- TechCrunch", "| The Verge", "- The Verge", "| CNBC", "- CNBC",
            "| Bloomberg", "- Bloomberg", "| WSJ", "- WSJ", "| NYT", "- NYT",
            "- Hindustan Times", "| Hindustan Times", "- Times of India",
            "| Times of India", "- Economic Times", "| Economic Times",
            "- NDTV", "| NDTV", "- India Today", "| India Today"
        ]

        clean_title = title
        for site in news_sites:
            clean_title = clean_title.replace(site, "").strip()

        # For social platforms, prioritize the body (actual post content)
        if platform in ["twitter", "reddit", "linkedin"]:
            if body and len(body) > 50:
                # Body usually contains the actual post text
                return body.strip()
            elif clean_title:
                return clean_title.strip()

        # For news, combine title and body
        if body and clean_title:
            return f"{clean_title}\n\n{body}".strip()

        return clean_title or body or ""
    
    def build_platform_queries(self, keywords: List[str], handles: List[str], platform: str, frequency: str = "hourly") -> List[str]:
        """
        Build platform-specific search queries with real-time date filters
        Frequency-aware: real-time focuses on breaking news, hourly on recent developments
        """
        queries = []
        site_filters = self.PLATFORM_SITES.get(platform, [])

        # Date filters based on frequency - focused on 2026 and future
        future_years = ["2026", "2027", "2028", "2029", "2030"]
        if frequency == "realtime":
            # Real-time: Focus on breaking/urgent news right now
            date_filters = [
                "breaking news", "just now", "urgent", "breaking",
                "latest news", "right now", "moments ago", "live",
                "today", "this hour", "last hour"
            ] + future_years  # Include future years
        else:
            # Hourly/Daily/Weekly: Focus on 2026+ and recent breaking news
            date_filters = [
                "latest", "recent", "today", "yesterday",
                "this week", "last 24 hours", "breaking news",
                "upcoming", "forecast", "prediction", "expected"
            ] + future_years  # Include all future years

        if platform == "twitter":
            # Twitter/X specific searches - prioritize handle-specific content
            # First priority: Content directly from specified handles
            if handles:
                for handle in handles[:3]:
                    clean_handle = handle.replace("@", "").strip()
                    # Direct from user queries (highest priority)
                    queries.append(f"from:{clean_handle}")  # Most recent from user
                    for date_filter in date_filters[:3]:
                        queries.append(f"from:{clean_handle} {date_filter}")
                        # Also search for mentions of the handle
                        queries.append(f"{clean_handle} {date_filter}")

            # Second priority: General keyword searches (if no handles or as supplement)
            for keyword in keywords[:3]:
                for date_filter in date_filters[:2]:
                    queries.append(f"{keyword} {date_filter}")
                    for site in site_filters:
                        queries.append(f"{keyword} {date_filter} {site}")

        elif platform == "linkedin":
            # LinkedIn specific searches - prioritize handle-specific content
            # First priority: Content from specific LinkedIn profiles/companies
            if handles:
                for handle in handles[:3]:
                    clean_handle = handle.replace("@", "").strip()
                    # Direct profile/company content (highest priority)
                    queries.append(f"{clean_handle} site:linkedin.com")
                    queries.append(f"site:linkedin.com/in/{clean_handle}")
                    queries.append(f"site:linkedin.com/company/{clean_handle}")
                    for date_filter in date_filters[:3]:
                        queries.append(f"{clean_handle} {date_filter} site:linkedin.com")

            # Second priority: General keyword searches
            for keyword in keywords[:3]:
                for date_filter in date_filters[:3]:
                    queries.append(f"{keyword} {date_filter}")
                    for site in site_filters:
                        queries.append(f"{keyword} {date_filter} {site}")

        elif platform == "reddit":
            # Reddit specific searches - prioritize subreddit/user-specific content
            # First priority: Content from specific subreddits/users
            if handles:
                for handle in handles[:3]:
                    clean_handle = handle.replace("@", "").replace("r/", "").replace("u/", "").strip()
                    # Direct subreddit/user content (highest priority)
                    queries.append(f"site:reddit.com/r/{clean_handle}")  # Specific subreddit
                    queries.append(f"site:reddit.com/u/{clean_handle}")  # Specific user
                    queries.append(f"r/{clean_handle} site:reddit.com")   # Alternative syntax
                    # Recent posts from specific communities
                    for date_filter in date_filters[:2]:
                        queries.append(f"site:reddit.com/r/{clean_handle} {date_filter}")

            # Second priority: General keyword searches in Reddit
            for keyword in keywords[:3]:
                queries.append(f"{keyword} site:reddit.com")  # Reddit naturally shows recent
                for date_filter in date_filters[:2]:
                    queries.append(f"{keyword} {date_filter} site:reddit.com")

        elif platform == "news":
            # News searches - focus on 2026+ and company achievements
            future_years = ["2026", "2027", "2028"]

            # First priority: Company/person specific future news
            if handles:
                for handle in handles[:3]:
                    clean_handle = handle.replace("@", "").strip()
                    for year in future_years[:2]:  # Focus on 2026-2027
                        queries.append(f"{clean_handle} {year} business news industry development announcement -personal")
                        queries.append(f"{clean_handle} {year} company launch product achievement")  # Allow company achievements
                        queries.append(f"{clean_handle} {year} milestone growth expansion")  # Allow company milestones

            # Second priority: General industry keyword searches for future
            for keyword in keywords[:3]:
                for year in future_years[:2]:  # 2026-2027 focus
                    queries.append(f"{keyword} {year} industry news business latest -personal -site:twitter.com -site:reddit.com")
                # Also include recent breaking news and future-focused content
                queries.append(f"{keyword} recent news today breaking upcoming -personal -site:twitter.com -site:reddit.com")
                queries.append(f"{keyword} forecast prediction expected future -personal -site:twitter.com -site:reddit.com")

        return queries
    
    async def fetch_for_rule(self, rule: Dict) -> List[Dict]:
        """
        Fetch content matching a single tracking rule
        Now with platform-specific search for Twitter, LinkedIn, Reddit
        """
        results = []
        keywords = rule.get("keywords", [])
        handles = rule.get("handles", [])
        platforms = rule.get("platforms", ["news"])
        logic_type = rule.get("logic_type", "keywords_or_handles")
        frequency = rule.get("frequency", "hourly")
        
        seen_urls = set()  # Avoid duplicates
        
        print(f"[SocialListening] Rule '{rule.get('name')}' - Platforms: {platforms}, Keywords: {keywords}, Handles: {handles}")
        
        # Search each selected platform separately
        for platform in platforms:
            platform_queries = []
            
            # Build queries based on logic type
            if logic_type == "keywords_only" and keywords:
                platform_queries = self.build_platform_queries(keywords, [], platform, frequency)

            elif logic_type == "handles_only" and handles:
                platform_queries = self.build_platform_queries([], handles, platform, frequency)

            elif logic_type == "keywords_and_handles" and keywords and handles:
                # Combined search
                for kw in keywords[:2]:
                    for handle in handles[:2]:
                        clean_handle = handle.replace("@", "").strip()
                        if platform == "news":
                            platform_queries.append(f"{kw} {clean_handle}")
                        else:
                            site_filter = self.PLATFORM_SITES.get(platform, [""])[0] if self.PLATFORM_SITES.get(platform) else ""
                            platform_queries.append(f"{kw} {clean_handle} {site_filter}".strip())

            elif logic_type == "keywords_or_handles":
                platform_queries = self.build_platform_queries(keywords, handles, platform, frequency)
            
            else:
                # Default: search keywords
                platform_queries = self.build_platform_queries(keywords or [""], handles, platform, frequency)
            
            # Execute searches for this platform - try official APIs first, then DuckDuckGo
            for query in platform_queries[:5]:  # Limit queries per platform
                try:
                    search_results = []

                    # First, try official APIs for supported platforms
                    if platform in self.API_SUPPORTED_PLATFORMS:
                        try:
                            # Extract keywords and handles from the query for API calls
                            api_keywords = keywords[:3] if keywords else []
                            api_handles = handles[:2] if handles else []

                            # For Twitter, try to extract handles from query if it's a "from:" query
                            if platform == "twitter" and "from:" in query:
                                # Extract handles from Twitter queries
                                import re
                                handle_matches = re.findall(r'from:(\w+)', query)
                                if handle_matches:
                                    api_handles.extend([f"@{h}" for h in handle_matches])

                            api_results = await self.search_official_apis(platform, api_keywords, api_handles, max_results=8)
                            search_results.extend(api_results)

                            # If we got good results from API, reduce DuckDuckGo search
                            max_duck_results = 4 if len(api_results) >= 4 else 8
                        except Exception as api_e:
                            print(f"[SocialListening] Official API failed for {platform}, falling back to DuckDuckGo: {api_e}")
                            max_duck_results = 8
                    else:
                        max_duck_results = 8

                    # Always do DuckDuckGo search as backup/supplement
                    duck_results = self.search_duckduckgo(query, max_results=max_duck_results)
                    search_results.extend(duck_results)
                    
                    for item in search_results:
                        url = item.get("href", "")

                        # Skip if already seen
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        # Determine actual platform from URL or use marked platform
                        actual_platform = item.get("platform") or self.determine_platform(url)

                        # For platform-specific searches, only accept results from that platform
                        if platform != "news" and actual_platform != platform:
                            continue
                        
                        # Clean the URL - remove tracking parameters
                        url = self.clean_url(url)
                        
                        # Validate URL is a direct link to a post, not a search page
                        if not self.is_direct_post_url(url, actual_platform):
                            print(f"[SocialListening] Skipping non-direct URL: {url[:60]}...")
                            continue

                        # Skip if this is from API and we already have it from search (avoid duplicates)
                        if item.get("from_api") and url in seen_urls:
                            continue
                        
                        # For API results, use the provided author/handle, otherwise extract from URL
                        if item.get("from_api"):
                            author = item.get("source", "Unknown") or "Unknown"
                            handle_extracted = ""  # API results may not have handles in the same format
                        else:
                            author, handle_extracted = self.extract_author_from_url(url, actual_platform)

                        # Clean and format content - API results may have better content
                        # For non-API results, fetch authentic content from the URL
                        if item.get("from_api") and item.get("body"):
                            content = item.get("body", "").strip()
                        else:
                            # Fetch authentic full content from the actual URL
                            # This gets the real post content, not just search snippets
                            original_title = item.get("title", "")
                            original_body = item.get("body", "")
                            
                            # Try to get authentic content from the URL
                            content = self.fetch_authentic_content(
                                url, 
                                actual_platform, 
                                original_title, 
                                original_body
                            )
                            
                            # If authentic fetch didn't work well, fall back to clean_content
                            if not content or len(content) < 50:
                                content = self.clean_content(
                                    original_title,
                                    original_body,
                                    actual_platform
                                )

                        # Skip if content is too short or empty
                        if not content or len(content) < 20:
                            continue

                        # Apply industry relevance filter
                        if not self.is_industry_relevant_content(
                            content,
                            item.get("title", ""),
                            author,
                            actual_platform
                        ):
                            continue  # Skip this result - not industry relevant

                        # Apply recency filter - ensure content is recent
                        if not self.is_content_recent(
                            content,
                            item.get("title", "")
                        ):
                            continue  # Skip this result - appears to be old content
                        
                        # Calculate content quality score
                        quality_score = self.calculate_content_quality_score(
                            content,
                            item.get("title", "")
                        )

                        results.append({
                            "external_id": self.generate_external_id(url, item.get("title", "")),
                            "platform": actual_platform,
                            "author": author if author != "Unknown" else item.get("source", "Unknown"),
                            "handle": handle_extracted,
                            "content": content,
                            "url": url,
                            "posted_at": datetime.now(),
                            "rule_id": rule.get("id"),
                            "rule_name": rule.get("name"),
                            "quality_score": quality_score
                        })
                    
                    # Rate limiting between queries
                    await asyncio.sleep(self.search_delay)
                    
                except Exception as e:
                    print(f"[SocialListening] Error searching for '{query}': {e}")
        
        # Apply frequency-based result limits
        frequency = rule.get("frequency", "hourly")
        max_results = self.get_frequency_limit(frequency)

        if len(results) > max_results:
            # Sort by quality score and recency, keep top results
            results.sort(key=lambda x: (x.get("quality_score", 0), x.get("posted_at", datetime.min)), reverse=True)
            results = results[:max_results]
            print(f"[SocialListening] Limited results to top {max_results} for {frequency} frequency")

        print(f"[SocialListening] Rule '{rule.get('name')}' returning {len(results)} results across {platforms}")
        return results
    
    async def process_all_rules(self, user_id: int) -> Dict:
        """
        Process all active rules for a user and store results
        """
        from backend.db.database import AsyncSessionLocal
        from backend.db.models import TrackingRule, FetchedPost, MatchedResult, SocialAlert, User
        from sqlalchemy import select
        
        stats = {"rules_processed": 0, "posts_fetched": 0, "alerts_created": 0}
        
        async with AsyncSessionLocal() as session:
            try:
                # Get all active rules for the user
                stmt = select(TrackingRule).where(
                    TrackingRule.user_id == user_id,
                    TrackingRule.status == "active"
                )
                result = await session.execute(stmt)
                rules = result.scalars().all()
                
                if not rules:
                    print(f"[SocialListening] No active rules found for user {user_id}")
                    return stats
                
                print(f"[SocialListening] Processing {len(rules)} active rules for user {user_id}")
                
                for rule in rules:
                    rule_dict = {
                        "id": rule.id,
                        "name": rule.name,
                        "keywords": rule.keywords or [],
                        "handles": rule.handles or [],
                        "platforms": rule.platforms or ["news"],
                        "logic_type": rule.logic_type,
                        "alert_in_app": rule.alert_in_app,
                        "alert_email": rule.alert_email
                    }
                    
                    # Fetch content for this rule
                    fetched_items = await self.fetch_for_rule(rule_dict)
                    stats["rules_processed"] += 1
                    
                    new_matches = 0
                    
                    for item in fetched_items:
                        # Check if post already exists
                        existing_stmt = select(FetchedPost).where(
                            FetchedPost.external_id == item["external_id"]
                        )
                        existing = await session.execute(existing_stmt)
                        existing_post = existing.scalar_one_or_none()
                        
                        if existing_post:
                            # Check if this rule already matched this post
                            match_stmt = select(MatchedResult).where(
                                MatchedResult.post_id == existing_post.id,
                                MatchedResult.rule_id == rule.id
                            )
                            match_exists = await session.execute(match_stmt)
                            if match_exists.scalar_one_or_none():
                                continue  # Already matched
                            post_id = existing_post.id
                        else:
                            # Create new post
                            new_post = FetchedPost(
                                platform=item["platform"],
                                external_id=item["external_id"],
                                author=item["author"],
                                handle=item["handle"],
                                content=item["content"],
                                url=item["url"],
                                posted_at=item["posted_at"],
                                quality_score=item.get("quality_score", 5)
                            )
                            session.add(new_post)
                            await session.flush()
                            post_id = new_post.id
                            stats["posts_fetched"] += 1
                        
                        # Create matched result
                        matched = MatchedResult(
                            rule_id=rule.id,
                            post_id=post_id,
                            user_id=user_id
                        )
                        session.add(matched)
                        new_matches += 1
                    
                    # Create alert if there are new matches and alerts are enabled
                    if new_matches > 0:
                        # Create in-app alert if enabled
                        if rule.alert_in_app:
                            alert = SocialAlert(
                                user_id=user_id,
                                rule_id=rule.id,
                                title=f"New matches for '{rule.name}'",
                                message=f"Found {new_matches} new posts matching your rule.",
                                alert_type="match"
                            )
                            session.add(alert)
                            stats["alerts_created"] += 1

                        # Send email notification if enabled
                        if rule.alert_email:
                            try:
                                # Get user email for notification (use notification_email if set, otherwise regular email)
                                user_stmt = select(User).where(User.id == user_id)
                                user_result = await session.execute(user_stmt)
                                user = user_result.scalar_one_or_none()

                                # Use notification_email if set, otherwise fall back to regular email
                                notification_email = user.notification_email or user.email

                                if user and notification_email:
                                    subject = f"🚨 Social Media Alert: {rule.name}"
                                    body = f"""
                                    <h2>New Social Media Matches Found</h2>
                                    <p>Hi {user.username},</p>
                                    <p>Your tracking rule "<strong>{rule.name}</strong>" has found <strong>{new_matches}</strong> new matching posts.</p>
                                    <p><strong>Platforms monitored:</strong> {', '.join(rule.platforms or ['news'])}</p>
                                    <p><strong>Keywords:</strong> {', '.join(rule.keywords or [])}</p>
                                    {f'<p><strong>Handles:</strong> {', '.join(rule.handles or [])}</p>' if rule.handles else ''}
                                    <p>Check your Simplii dashboard for details and take action on these opportunities.</p>
                                    <br>
                                    <p>Best regards,<br>Your Simplii Team</p>
                                    """

                                    # Send email asynchronously to avoid blocking
                                    asyncio.create_task(
                                        send_email_async(notification_email, subject, body)
                                    )

                                    print(f"[SocialListening] Email alert sent to {notification_email} for rule '{rule.name}'")

                            except Exception as email_e:
                                print(f"[SocialListening] Failed to send email alert: {email_e}")
                                # Don't fail the entire process if email fails
                
                await session.commit()
                print(f"[SocialListening] Processing complete: {stats}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[SocialListening] Error processing rules: {e}")
                import traceback
                traceback.print_exc()
        
        return stats


# Singleton instance
_agent_instance = None

def get_social_listening_agent() -> SocialListeningAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SocialListeningAgent()
    return _agent_instance
