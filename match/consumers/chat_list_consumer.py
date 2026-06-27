import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils.timesince import timesince
from django.utils import timezone

from match.models import Conversation
from accounts.models import UserProfile
from match.models import Conversation, Message


class ChatListConsumer(AsyncWebsocketConsumer):
    """
    ws://host/ws/chat-list/

    - Auth required
    - On connect: send full conversation list
    - Can be triggered later via group_send to refresh list
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.group_name = f"chatlist_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        data = await self.get_chat_list(self.user.id)
        await self.send_json(data)

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

    async def chatlist_refresh(self, event):
        data = await self.get_chat_list(self.user.id)
        await self.send_json(data)

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    # ---------------- DB ----------------

    @database_sync_to_async
    def get_chat_list(self, user_id: int):

        conversations = (
            Conversation.objects
            .select_related("match", "match__user1", "match__user2")
            .order_by("-last_message_at", "-id")
        )

        results = []

        from accounts.models import UserBlock
        blocked_by_me = list(UserBlock.objects.filter(blocker_id=user_id).values_list("blocked_user_id", flat=True))
        blocked_me = list(UserBlock.objects.filter(blocked_user_id=user_id).values_list("blocker_id", flat=True))
        blocked_user_ids = set(blocked_by_me).union(set(blocked_me))

        for conv in conversations:
            match = conv.match

            if user_id not in (match.user1_id, match.user2_id):
                continue
            if not match.is_active:
                continue

            other_user = match.user2 if match.user1_id == user_id else match.user1
            if other_user.id in blocked_user_ids:
                continue

            # last message
            last_msg = (
                Message.objects
                .filter(conversation=conv)
                .order_by("-created_at")
                .first()
            )

            # profile
            profile = getattr(other_user, "profile", None)

            full_name = profile.full_name if profile else ""
            photo = profile.photo.url if profile and profile.photo else None
            is_online = profile.is_online if profile else False

            results.append({
                "match_id": match.id,
                "conversation_id": conv.id,
                "matched_at": match.created_at.isoformat(),
                "time_ago": timesince(match.created_at, timezone.now()) + " ago",
                "last_message_at": last_msg.created_at.isoformat() if last_msg else None,
                "last_message": last_msg.text if last_msg else None,

                # NEW STATUS FIELDS
                "is_seen": last_msg.is_seen if last_msg else False,
                "is_delivered": last_msg.is_delivered if last_msg else False,

                "user": {
                    "id": other_user.id,
                    "email": other_user.email,
                    "username": other_user.username,
                    "full_name": full_name,
                    "photo": photo,
                    "is_online": is_online,
                }
            })

        return {
            "count": len(results),
            "results": results
        }
