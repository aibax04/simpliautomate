from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from backend.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
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

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SavedPost(Base):
    __tablename__ = "saved_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("generated_posts.id"))
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
