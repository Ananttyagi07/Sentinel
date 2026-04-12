import os
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

class NotionTools:
    def __init__(self):
        self.api_key = os.getenv("NOTION_API_KEY")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        if not self.api_key:
            logger.warning("⚠️  NOTION_API_KEY not set — Notion sync will use mock mode")
        if self.api_key and not self.database_id:
            logger.warning("⚠️  NOTION_DATABASE_ID not set — Notion sync will fail")
            
    async def check_duplicate(self, url: str) -> bool:
        if not self.api_key:
            return False
        if not self.database_id:
            logger.error("NOTION_DATABASE_ID is missing")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/databases/{self.database_id}/query",
                    headers=self.headers,
                    json={
                        "filter": {
                            "property": "URL",
                            "url": {"equals": url}
                        }
                    }
                )
                if response.status_code >= 400:
                    logger.error(
                        "Notion duplicate check failed (%s): %s",
                        response.status_code,
                        response.text,
                    )
                    return False
                data = response.json()
                return len(data.get("results", [])) > 0
        except Exception as e:
            logger.error(f"Notion duplicate check error: {e}")
        return False
    
    async def create_page(
        self,
        title: str,
        url: str,
        page_type: str,
        summary: str,
        tags: list[str],
        insights: list[str],
    ) -> str:
        if not self.api_key:
            logger.info(f"[Mock Notion] Would create page: {title}")
            return "mock-page-id-12345"
        if not self.database_id:
            logger.error("NOTION_DATABASE_ID is missing")
            return "error"

        try:
            children = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "📋 Summary"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": summary}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "💡 Key Insights"}}]
                    }
                },
            ]

            for insight in insights:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": insight}}]
                    }
                })

            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🔗 Source"}}]
                }
            })
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": url, "link": {"url": url}}}]
                }
            })

            payload = {
                "parent": {"database_id": self.database_id},
                "icon": {"emoji": self._get_emoji(page_type)},
                "properties": {
                    "Name": {
                        "title": [{"text": {"content": title[:200]}}]
                    },
                    "URL": {"url": url},
                    "Type": {
                        "select": {"name": page_type.capitalize()}
                    },
                    "Tags": {
                        "multi_select": [{"name": tag} for tag in tags[:5]]
                    },
                    "Saved by": {
                        "rich_text": [{"type": "text", "text": {"content": "Sentinel"}}]
                    }
                },
                "children": children,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/pages",
                    headers=self.headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    logger.error(
                        "Notion create page failed (%s): %s",
                        response.status_code,
                        response.text,
                    )
                    return "error"
                data = response.json()
                return data.get("id", "unknown")

        except Exception as e:
            logger.error(f"Notion create page error: {e}")
            return "error"

    def _get_emoji(self, page_type: str) -> str:
        return {
            "article": "📰",
            "product": "🛍️",
            "documentation": "📚",
            "news": "📡",
        }.get(page_type, "🌐")
