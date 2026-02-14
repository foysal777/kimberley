from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.timesince import timesince
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from match.models import Match, Message

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def connected_users_list(request):
    """
    GET /api/match/connections/

    Returns all active matched users with profile & chat info.
    """
    user_id = request.user.id

    matches = (
        Match.objects
        .filter(is_active=True)
        .filter(Q(user1_id=user_id) | Q(user2_id=user_id))
        .select_related("user1", "user2")
        .select_related("conversation")
        .order_by("-created_at")
    )

    results = []

    for m in matches:
        other_user = m.user2 if m.user1_id == user_id else m.user1
        profile = getattr(other_user, "profile", None)
        conv = getattr(m, "conversation", None)

        # 🔹 last message
        last_message_text = None
        last_message_at = None
        if conv:
            last_msg = (
                Message.objects
                .filter(conversation=conv)
                .order_by("-created_at")
                .only("text", "created_at")
                .first()
            )
            if last_msg:
                last_message_text = last_msg.text
                last_message_at = last_msg.created_at

        results.append({
            "match_id": m.id,
            "conversation_id": conv.id if conv else None,
            "matched_at": m.created_at,
            "time_ago": timesince(m.created_at) + " ago",
            "last_message_at": last_message_at,
            "last_message": last_message_text,

            "user": {
                "id": other_user.id,
                "email": other_user.email,
                "username": other_user.username,
                "full_name": profile.full_name if profile else "",
                "photo": profile.photo.url if profile and profile.photo else None,
                "is_online": profile.is_online if profile else False,
            }
        })

    return Response({
        "count": len(results),
        "results": results
    })








from django.db.models import Q
from django.utils.timesince import timesince
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from match.models import Match


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def connected_users_list_for_people(request):
    """
    GET /api/match/connections/people/

    Returns all active matched users (connected users) for current user.
    """
    user_id = request.user.id

    matches = (
        Match.objects
        .filter(is_active=True)
        .filter(Q(user1_id=user_id) | Q(user2_id=user_id))
        .select_related("user1", "user2")
        .select_related("conversation")
        .order_by("-created_at")
    )

    results = []

    for m in matches:
        other_user = m.user2 if m.user1_id == user_id else m.user1
        profile = getattr(other_user, "profile", None)
        conv = getattr(m, "conversation", None)

        photo_url = None
        if profile and profile.photo:
            photo_url = request.build_absolute_uri(profile.photo.url)

        results.append({
            "match_id": m.id,
            "conversation_id": conv.id if conv else None,
            "time_ago": timesince(m.created_at) + " ago",

            "user": {
                "id": other_user.id,
                "email": other_user.email,
                "username": other_user.username,
                "full_name": profile.full_name if profile else other_user.username,
                "photo": photo_url,
                "is_online": profile.is_online if profile else False,
            }
        })

    return Response({
        "count": len(results),
        "results": results
    })







from django.utils.timesince import timesince
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from match.models import Notification


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    """
    GET /api/notifications/

    Returns current user's notifications with sender photo + time_ago.
    """
    qs = (
        Notification.objects
        .filter(to_user=request.user)
        .select_related("from_user")
        .order_by("-created_at")
    )

    results = []
    for n in qs:
        from_user = n.from_user
        profile = getattr(from_user, "profile", None) if from_user else None

        photo_url = None
        if profile and profile.photo:
            photo_url = request.build_absolute_uri(profile.photo.url)

        # notification message (priority: body -> title)
        message = n.body or n.title or ""

        results.append({
            "id": n.id,
            "type": n.type,
            "message": message,
            "time_ago": timesince(n.created_at) + " ago",
            "created_at": n.created_at,

            "from_user": {
                "id": from_user.id if from_user else None,
                "photo": photo_url,
            },
            "data": n.data,  # optional: conversation_id / match_id / message_id
            "is_read": n.is_read,
        })

    return Response({"count": len(results), "results": results})









import math
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from match.models import Match
from accounts.models import UserProfile, UserLocation  # 

User = get_user_model()


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2) + (math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def match_users_info(request, match_id: int):
    """
    GET /api/match/<match_id>/users/

    Response:
    - both users: photo, full_name, role
    - distance_km (from logged-in user to the other user)
    """

    try:
        match = (
            Match.objects
            .select_related("user1", "user2")
            .get(id=match_id, is_active=True)
        )
    except Match.DoesNotExist:
        return Response({"detail": "Match not found."}, status=status.HTTP_404_NOT_FOUND)

    # Only participants can access
    if request.user.id not in (match.user1_id, match.user2_id):
        return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    # logged-in user's location
    try:
        my_loc = request.user.location  # related_name="location"
    except UserLocation.DoesNotExist:
        return Response({"detail": "Your location is not set."}, status=400)

    users = [match.user1, match.user2]
    results = []

    for u in users:
        profile = getattr(u, "profile", None)

        # user location
        try:
            u_loc = u.location
            distance = haversine_km(
                my_loc.latitude, my_loc.longitude,
                u_loc.latitude, u_loc.longitude
            )
            distance_km = round(distance, 2)
        except UserLocation.DoesNotExist:
            distance_km = None

        photo_url = None
        if profile and profile.photo:
            photo_url = request.build_absolute_uri(profile.photo.url)

        results.append({
            "user_id": u.id,
            "full_name": profile.full_name if profile else u.username,
            "role": profile.role if profile else "",
            "photo": photo_url,
            "distance_km": distance_km,
        })

    return Response({
        "match_id": match.id,
        "results": results
    })









from datetime import timedelta

from django.db.models import Q, Count, Min
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from match.models import Match, Conversation, Message
from swipe.models import SwipeAction
from accounts.models import UserProfileSelection
from accounts.models import ProfileView  




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics(request):
    """
    GET /api/match/analytics/?days=7   or  /api/match/analytics/?days=30
    """

    # ---- days param ----
    days_raw = request.query_params.get("days", "7")
    try:
        days = int(days_raw)
    except (TypeError, ValueError):
        days = 7
    if days not in (7, 30):
        days = 7

    now = timezone.now()
    since = now - timedelta(days=days)
    user = request.user

    # ---------------------------
    # 1) Connections Sent (LIKE given by me) in period
    # ---------------------------
    connections_sent = SwipeAction.objects.filter(
        from_user=user,
        action=SwipeAction.ACTION_LIKE,
        created_at__gte=since
    ).count()

    # ---------------------------
    # 2) My active matches
    # ---------------------------
    my_matches_qs = Match.objects.filter(
        is_active=True
    ).filter(
        Q(user1=user) | Q(user2=user)
    )

    # Connections Accepted (matches created in period)
    connections_accepted = my_matches_qs.filter(created_at__gte=since).count()

    # ---------------------------
    # Conversations for my matches
    # ---------------------------
    my_conversation_ids = Conversation.objects.filter(
        match__in=my_matches_qs
    ).values_list("id", flat=True)

    # ---------------------------
    # 3) Messages Received (from other users) in period
    # ---------------------------
    messages_received = (
        Message.objects
        .filter(conversation_id__in=my_conversation_ids, created_at__gte=since)
        .exclude(sender=user)
        .count()
    )

    # ---------------------------
    # 4) Start Chat (first message time >= since) in my conversations
    # ---------------------------
    start_chat = (
        Message.objects
        .filter(conversation_id__in=my_conversation_ids)
        .values("conversation_id")
        .annotate(first_time=Min("created_at"))
        .filter(first_time__gte=since)
        .count()
    )

    # ---------------------------
    # 5) Viewed Profile (others viewed my profile) in period
    # ---------------------------
    viewed_profile = ProfileView.objects.filter(
        viewed_user=user,
        created_at__gte=since
    ).count()

    # ---------------------------
    # 6) Audience Overview
    # period matches -> other users -> their taxonomy selections -> top items
    # TaxonomyItem field is `text` (NOT name)
    # ---------------------------
    period_matches = my_matches_qs.filter(created_at__gte=since).only("user1_id", "user2_id")

    other_user_ids = []
    for m in period_matches:
        other_user_ids.append(m.user2_id if m.user1_id == user.id else m.user1_id)

    if other_user_ids:
        top_items_qs = (
            UserProfileSelection.objects
            .filter(profile__user_id__in=other_user_ids)
            .values("item_id", "item__text")           # ✅ FIX: item__text
            .annotate(cnt=Count("item_id"))
            .order_by("-cnt")[:3]
        )
        audience_overview = [
            {"item_id": x["item_id"], "name": x["item__text"], "count": x["cnt"]}  # name key kept for frontend
            for x in top_items_qs
        ]
    else:
        audience_overview = []

    # ---------------------------
    # 7) Active conversations in period (by last_message_at)
    # ---------------------------
    active_conversations = Conversation.objects.filter(
        id__in=my_conversation_ids,
        last_message_at__gte=since
    ).count()

    return Response({
        "range_days": days,
        "since": since.isoformat(),
        "top_summary": {
            "connections_sent": connections_sent,
            "connections_accepted": connections_accepted,
            "messages_received": messages_received,
        },
        "connection_activity": {
            "viewed_profile": viewed_profile,
            "start_chat": start_chat,
        },
        "audience_overview": audience_overview,
        "your_activity": {
            "active_conversations": active_conversations,
        }
    })
