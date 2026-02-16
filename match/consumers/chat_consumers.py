import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from match.models import Conversation, Message, Notification
from accounts.models import UserProfile

class ChatConsumer(AsyncWebsocketConsumer):
    """
    ws://host/ws/chat/<conversation_id>/
    - Only matched users can connect
    - Receive JSON: {"type":"message", "text":"hi"}
    - Broadcast to room group
    - Save message in DB
    - Create DB notification + push over NotificationConsumer group
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        self.room_group_name = f"chat_{self.conversation_id}"

        allowed = await self.user_can_access_conversation(self.user.id, self.conversation_id)
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # optional: send "connected" event
        await self.send_json({"type": "connected", "conversation_id": self.conversation_id})

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception:
            pass

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send_json({"type": "error", "detail": "Invalid JSON"})
            return

        msg_type = payload.get("type")
        if msg_type != "message":
            await self.send_json({"type": "error", "detail": "Unsupported message type"})
            return

        text = (payload.get("text") or "").strip()
        if not text:
            await self.send_json({"type": "error", "detail": "Text is required"})
            return

        # Save message + create DB notification
        msg, other_user_id = await self.create_message_and_notification(
            conversation_id=self.conversation_id,
            sender_id=self.user.id,
            text=text,
        )


        await self.channel_layer.group_send(
        f"chatlist_{other_user_id}",
        {"type": "chatlist.refresh"}
)

        await self.channel_layer.group_send(
        f"chatlist_{self.user.id}",
        {"type": "chatlist.refresh"}
      )

        # Broadcast to chat group (both users will get)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": {
                    "id": msg["id"],
                    "conversation_id": self.conversation_id,
                    "sender_id": self.user.id,
                    "text": msg["text"],
                    "created_at": msg["created_at"],
                }
            }
        )

        # Also push real-time notification to receiver's notification group
        await self.channel_layer.group_send(
            f"notif_{other_user_id}",
            {
                "type": "notif.push",
                "notification": {
                    "type": "MESSAGE",
                    "from_user_id": self.user.id,
                    "title": "New message",
                    "body": text[:120],
                    "data": {"conversation_id": self.conversation_id, "message_id": msg["id"]},
                    "created_at": msg["created_at"],
                }
            }
        )

    async def chat_message(self, event):
        await self.send_json(event["message"])

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    # ---------- DB helpers ----------
    @database_sync_to_async
    def user_can_access_conversation(self, user_id: int, conversation_id: int) -> bool:
        try:
            conv = Conversation.objects.select_related("match").get(id=conversation_id)
        except Conversation.DoesNotExist:
            return False
        m = conv.match
        return user_id in (m.user1_id, m.user2_id) and m.is_active

    @database_sync_to_async
    def create_message_and_notification(self, conversation_id: int, sender_id: int, text: str):
        conv = Conversation.objects.select_related("match").get(id=conversation_id)
        msg = Message.objects.create(conversation=conv, sender_id=sender_id, text=text)

        conv.last_message_at = msg.created_at
        conv.save(update_fields=["last_message_at"])

        m = conv.match
        other_user_id = m.user2_id if m.user1_id == sender_id else m.user1_id

        Notification.objects.create(
            to_user_id=other_user_id,
            from_user_id=sender_id,
            type=Notification.TYPE_MESSAGE,
            title="New message",
            body=text[:120],
            data={"conversation_id": conv.id, "message_id": msg.id},
        )

        # return serializable dict (avoid datetime json issue by isoformat)
        return (
            {"id": msg.id, "text": msg.text, "created_at": msg.created_at.isoformat()},
            other_user_id,
        )


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    ws://host/ws/notifications/
    - Join group notif_<user_id>
    - Server pushes notifications here in real-time
    -  Mark user online/offline in UserProfile
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.group_name = f"notif_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # set online = True
        await self.set_user_online(self.user.id, True)

        await self.send_json({"type": "connected", "channel": "notifications"})

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

        # set online = False
        await self.set_user_online(self.user.id, False)

    async def notif_push(self, event):
        await self.send_json(event["notification"])

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    # ---------- DB helper ----------
    @database_sync_to_async
    def set_user_online(self, user_id: int, online: bool):
        profile, _ = UserProfile.objects.get_or_create(user_id=user_id)
        profile.is_online = online
        profile.save(update_fields=["is_online"])









