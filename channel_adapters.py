import time
import requests
import json
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseChannelAdapter(ABC):
    def __init__(self, channel_id: int, name: str, account_id: str, access_token: str, extra_data: Dict[str, Any] = None):
        self.channel_id = channel_id
        self.name = name
        self.account_id = account_id
        self.access_token = access_token
        self.extra_data = extra_data or {}

    @abstractmethod
    def publish(self, media_url: str, caption: str, media_type: str = "IMAGE") -> Dict[str, Any]:
        """Publish media to the channel and return status and post_id"""
        pass

class InstagramAdapter(BaseChannelAdapter):
    """Meta Instagram Content Publishing API Adapter"""
    def publish(self, media_url: str, caption: str, media_type: str = "IMAGE") -> Dict[str, Any]:
        container_url = f"https://graph.facebook.com/v21.0/{self.account_id}/media"
        params = {
            "caption": caption,
            "access_token": self.access_token
        }
        
        if media_type.upper() in ["REELS", "VIDEO"]:
            params["video_url"] = media_url
            params["media_type"] = "REELS"
        else:
            params["image_url"] = media_url

        try:
            r1 = requests.post(container_url, data=params, timeout=30)
            res1 = r1.json()
            if "id" not in res1:
                return {
                    "status": "error",
                    "error": res1.get("error", {}).get("message", "Container creation failed"),
                    "platform": "INSTAGRAM"
                }

            creation_id = res1["id"]

            # Wait briefly if video processing
            if media_type.upper() in ["REELS", "VIDEO"]:
                time.sleep(5)

            publish_url = f"https://graph.facebook.com/v21.0/{self.account_id}/media_publish"
            pub_params = {"creation_id": creation_id, "access_token": self.access_token}
            r2 = requests.post(publish_url, data=pub_params, timeout=30)
            res2 = r2.json()

            if "id" in res2:
                return {
                    "status": "success",
                    "post_id": res2["id"],
                    "platform": "INSTAGRAM",
                    "channel_name": self.name
                }
            else:
                return {
                    "status": "error",
                    "error": res2.get("error", {}).get("message", "Publishing container failed"),
                    "platform": "INSTAGRAM"
                }
        except Exception as e:
            return {"status": "error", "error": str(e), "platform": "INSTAGRAM"}

class FacebookPageAdapter(BaseChannelAdapter):
    """Meta Facebook Page Video/Photo Publishing Adapter"""
    def publish(self, media_url: str, caption: str, media_type: str = "IMAGE") -> Dict[str, Any]:
        try:
            if media_type.upper() in ["REELS", "VIDEO"]:
                url = f"https://graph.facebook.com/v21.0/{self.account_id}/videos"
                params = {
                    "file_url": media_url,
                    "description": caption,
                    "access_token": self.access_token
                }
            else:
                url = f"https://graph.facebook.com/v21.0/{self.account_id}/photos"
                params = {
                    "url": media_url,
                    "caption": caption,
                    "access_token": self.access_token
                }

            r = requests.post(url, data=params, timeout=35)
            res = r.json()
            if "id" in res:
                return {
                    "status": "success",
                    "post_id": res["id"],
                    "platform": "FACEBOOK",
                    "channel_name": self.name
                }
            else:
                return {
                    "status": "error",
                    "error": res.get("error", {}).get("message", "Facebook publish failed"),
                    "platform": "FACEBOOK"
                }
        except Exception as e:
            return {"status": "error", "error": str(e), "platform": "FACEBOOK"}

class TelegramAdapter(BaseChannelAdapter):
    """Telegram Channel / Group Bot Adapter"""
    def publish(self, media_url: str, caption: str, media_type: str = "IMAGE") -> Dict[str, Any]:
        bot_token = self.access_token # Bot token
        chat_id = self.account_id     # @channelusername or -100xxx
        
        try:
            if media_type.upper() in ["REELS", "VIDEO"]:
                url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
                payload = {"chat_id": chat_id, "video": media_url, "caption": caption}
            else:
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                payload = {"chat_id": chat_id, "photo": media_url, "caption": caption}
            
            r = requests.post(url, json=payload, timeout=25)
            res = r.json()
            if res.get("ok"):
                return {
                    "status": "success",
                    "post_id": str(res["result"]["message_id"]),
                    "platform": "TELEGRAM",
                    "channel_name": self.name
                }
            else:
                return {
                    "status": "error",
                    "error": res.get("description", "Telegram publish failed"),
                    "platform": "TELEGRAM"
                }
        except Exception as e:
            return {"status": "error", "error": str(e), "platform": "TELEGRAM"}

class GenericWebhookAdapter(BaseChannelAdapter):
    """Custom Webhook Adapter (For YouTube Shorts, Discord, Custom Scripts)"""
    def publish(self, media_url: str, caption: str, media_type: str = "IMAGE") -> Dict[str, Any]:
        webhook_url = self.access_token
        payload = {
            "channel_id": self.channel_id,
            "channel_name": self.name,
            "account_id": self.account_id,
            "media_url": media_url,
            "caption": caption,
            "media_type": media_type
        }
        try:
            r = requests.post(webhook_url, json=payload, timeout=20)
            return {
                "status": "success" if r.status_code in [200, 201] else "error",
                "post_id": f"webhook_{int(time.time())}",
                "platform": "WEBHOOK",
                "channel_name": self.name
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "platform": "WEBHOOK"}

class AdapterFactory:
    """Dynamically instantiates the correct adapter for any platform"""
    REGISTRY = {
        "INSTAGRAM": InstagramAdapter,
        "FACEBOOK": FacebookPageAdapter,
        "TELEGRAM": TelegramAdapter,
        "WEBHOOK": GenericWebhookAdapter,
        "YOUTUBE": GenericWebhookAdapter # Ready to bridge via n8n / Zapier webhook
    }

    @classmethod
    def get_adapter(cls, platform: str, channel_id: int, name: str, account_id: str, access_token: str, extra_data: dict = None) -> BaseChannelAdapter:
        platform_key = platform.upper().strip()
        adapter_cls = cls.REGISTRY.get(platform_key, GenericWebhookAdapter)
        return adapter_cls(channel_id, name, account_id, access_token, extra_data)
