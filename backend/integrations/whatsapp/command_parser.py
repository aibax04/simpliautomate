from typing import Dict, Any
import logging
from backend.agents.news_fetch_agent import NewsFetchAgent
from backend.db.database import AsyncSessionLocal
from sqlalchemy import select, func
from backend.db.models import FetchedPost, NewsItem

class CommandParser:
    def __init__(self):
        self.news_agent = NewsFetchAgent()

    async def parse_and_execute(self, command_text: str, sender_phone: str) -> str:
        """
        Parses the command and executes the corresponding action.
        Returns the response text to be sent back to the user.
        """
        command = command_text.strip().upper()
        
        if command == "LATEST NEWS":
            return await self.handle_latest_news()
        elif command == "STATS":
            return await self.handle_stats()
        elif command == "SHOW FEED":
            return await self.handle_show_feed()
        elif command.startswith("GENERATE POST"):
            return "Post generation started. (Mock)"
        elif command.startswith("APPROVE POST"):
             # Format: APPROVE POST <ID>
            return await self.handle_approve_post(command)
        elif command == "ALERT STATUS":
            return "All systems operational."
        elif command == "HELP":
            return "Commands:\nLATEST NEWS\nSHOW FEED\nSTATS\nGENERATE POST\nAPPROVE POST <ID>"
        else:
            return f"Unknown command: {command}. Type HELP for options."

    async def handle_latest_news(self) -> str:
        try:
            # Fetch from DB first for speed
            async with AsyncSessionLocal() as session:
                stmt = select(NewsItem).order_by(NewsItem.created_at.desc()).limit(3)
                res = await session.execute(stmt)
                items = res.scalars().all()
                
                if not items:
                    return "No news available right now. Try again later."
                
                response = "📰 *Latest News:*\n\n"
                for item in items:
                    response += f"🔹 *{item.headline}*\n{item.summary[:100]}...\nLINK: {item.source_url}\n\n"
                return response
        except Exception as e:
            return f"Error fetching news: {str(e)}"

    async def handle_stats(self) -> str:
        try:
            async with AsyncSessionLocal() as session:
                # Count fetched posts
                stmt = select(func.count(FetchedPost.id))
                res = await session.execute(stmt)
                count = res.scalar()
                return f"📊 *System Stats:*\n\nFetched Posts: {count}\nActive Agents: 3"
        except Exception as e:
            return f"Error fetching stats: {str(e)}"

    async def handle_show_feed(self) -> str:
         try:
            async with AsyncSessionLocal() as session:
                stmt = select(FetchedPost).order_by(FetchedPost.posted_at.desc()).limit(3)
                res = await session.execute(stmt)
                posts = res.scalars().all()
                
                if not posts:
                    return "Feed is empty."

                response = "📱 *Social Feed:*\n\n"
                for post in posts:
                    response += f"🔸 *{post.platform}*: {post.content[:50]}...\n"
                return response
         except Exception as e:
            return f"Error fetching feed: {str(e)}"
            
    async def handle_approve_post(self, command: str) -> str:
        parts = command.split()
        if len(parts) < 3:
            return "Usage: APPROVE POST <ID>"
        post_id = parts[2]
        # Logic to approve would go here
        return f"✅ Post {post_id} approved (Simulation)."
