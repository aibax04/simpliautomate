"""
Social Media Connectors Package

This package contains connectors for various social media platforms
used in the Simplii social media ingestion system.
"""

from .base_connector import (
    BaseConnector,
    UnifiedPost,
    FetchCursor,
    Platform,
    ConnectorError,
    AuthenticationError,
    RateLimitError,
    APIError
)

from .twitter_connector import TwitterConnector
from .news_connector import NewsConnector
from .connector_manager import ConnectorManager, IngestionRule, IngestionResult

__all__ = [
    # Base classes
    'BaseConnector',
    'UnifiedPost',
    'FetchCursor',
    'Platform',
    'ConnectorError',
    'AuthenticationError',
    'RateLimitError',
    'APIError',

    # Connectors
    'TwitterConnector',
    'NewsConnector',

    # Manager
    'ConnectorManager',
    'IngestionRule',
    'IngestionResult'
]