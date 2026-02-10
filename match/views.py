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
