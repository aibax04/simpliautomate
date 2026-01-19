from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from backend.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    notification_email = Column(String, nullable=True)  # Email for instant notifications
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    simplii_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    linkedin_person_urn = Column(String, index=True, nullable=False)
    linkedin_email = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    access_token = Column(String, nullable=False) # Encrypted
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

from sqlalchemy.orm import relationship

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    collateral = relationship("ProductCollateral", backref="product", cascade="all, delete-orphan")

class ProductCollateral(Base):
    __tablename__ = "product_collateral"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True) # doc, brochure, logo etc
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    domain = Column(String, index=True)
    trust_level = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NewsItem(Base):
    __tablename__ = "news_items"
    
    id = Column(Integer, primary_key=True, index=True)
    headline = Column(String, index=True)
    summary = Column(String)
    category = Column(String, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    source_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GenerationQueue(Base):
    __tablename__ = "generation_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    news_id = Column(Integer, ForeignKey("news_items.id"))
    status = Column(String, default="queued") # queued, processing, ready, failed
    preferences_json = Column(JSONB)
    result_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GeneratedPost(Base):
    __tablename__ = "generated_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    news_id = Column(Integer, ForeignKey("news_items.id"))
    caption = Column(String)
    image_path = Column(String)
    style = Column(String)
    palette = Column(String)
    posted_to_linkedin = Column(Boolean, default=False)
    last_image_edit_prompt = Column(String, nullable=True)
    image_updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SavedPost(Base):
    __tablename__ = "saved_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("generated_posts.id"))
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    linkedin_account_id = Column(Integer, ForeignKey("linkedin_accounts.id"), nullable=False)
    content = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    notification_email = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, completed, failed
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== SOCIAL LISTENING MODELS ====================

class TrackingRule(Base):
    """Tracking rules for social media monitoring"""
    __tablename__ = "tracking_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    keywords = Column(JSONB, default=[])  # List of keywords to track
    handles = Column(JSONB, default=[])   # List of social handles to track
    platforms = Column(JSONB, default=[]) # twitter, linkedin, reddit, news
    logic_type = Column(String, default="keywords_or_handles")  # keywords_only, handles_only, keywords_and_handles, keywords_or_handles, exclude_keywords
    frequency = Column(String, default="hourly")  # realtime, hourly, daily, weekly
    alert_email = Column(Boolean, default=False)
    alert_in_app = Column(Boolean, default=True)
    status = Column(String, default="active")  # active, paused
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships for cascade delete
    matched_results = relationship("MatchedResult", backref="rule", cascade="all, delete-orphan")
    alerts = relationship("SocialAlert", backref="rule", cascade="all, delete-orphan")


class FetchedPost(Base):
    """Posts fetched from social platforms"""
    __tablename__ = "fetched_posts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False, index=True)  # twitter, linkedin, reddit, news
    external_id = Column(String, index=True)  # Platform-specific ID for deduplication
    author = Column(String, nullable=True)
    handle = Column(String, nullable=True)
    content = Column(String, nullable=False)
    url = Column(String, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    quality_score = Column(Integer, default=5)  # Content quality score 0-10
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MatchedResult(Base):
    """Posts that matched tracking rules"""
    __tablename__ = "matched_results"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("tracking_rules.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("fetched_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    important = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SentimentAnalysis(Base):
    """Sentiment analysis results for matched posts"""
    __tablename__ = "sentiment_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("fetched_posts.id"), nullable=False)
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    sentiment_label = Column(String, nullable=True)  # positive, negative, neutral
    emotion_label = Column(String, nullable=True)
    key_themes = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SocialAlert(Base):
    """Alerts generated by tracking rules"""
    __tablename__ = "social_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("tracking_rules.id"), nullable=True)
    post_id = Column(Integer, ForeignKey("fetched_posts.id"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    read = Column(Boolean, default=False)
    alert_type = Column(String, default="match")  # match, summary, system
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MonitoringReport(Base):
    """Generated monitoring reports"""
    __tablename__ = "monitoring_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_type = Column(String, nullable=False)  # summary, detailed, sentiment
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    rules_included = Column(JSONB, default=[])
    content = Column(String, nullable=True)  # Store the actual report content
    pdf_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())