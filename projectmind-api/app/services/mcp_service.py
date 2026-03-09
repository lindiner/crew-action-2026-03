"""
Client MCP genérico para integrações (Asana, Slack, Gmail).
MVP: wrappers HTTP; futuramente usar MCP SDK.
"""
import httpx
from app.config import settings


class MCPService:
    @staticmethod
    def asana_request(method: str, path: str, json_body: dict | None = None) -> dict:
        if not settings.asana_access_token:
            return {"error": "Asana not configured"}
        url = f"https://app.asana.com/api/1.0{path}"
        headers = {"Authorization": f"Bearer {settings.asana_access_token}"}
        with httpx.Client(timeout=15.0) as client:
            if method == "GET":
                r = client.get(url, headers=headers)
            else:
                r = client.request(method, url, headers=headers, json=json_body or {})
        return r.json() if r.content else {}

    @staticmethod
    def slack_request(method: str, path: str, json_body: dict | None = None) -> dict:
        if not settings.slack_bot_token:
            return {"error": "Slack not configured"}
        url = f"https://slack.com/api{path}"
        headers = {"Authorization": f"Bearer {settings.slack_bot_token}", "Content-Type": "application/json"}
        with httpx.Client(timeout=15.0) as client:
            r = client.request(method, url, headers=headers, json=json_body or {})
        return r.json() if r.content else {}
