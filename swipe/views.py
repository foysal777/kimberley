from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import SwipeAction

User = get_user_model()


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from django.contrib.auth import get_user_model
from match.models import  Match, Conversation  # ✅ add these imports
from match.models import Notification  # optional, if you want notifications

User = get_user_model()


def ordered_pair(a_id: int, b_id: int):
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def swipe_action_create(request):
    """
    POST:
    {
        "to_user_id": 5,
        "action": "LIKE" | "PASS"
    }

    If mutual LIKE -> creates Match + Conversation and returns conversation_id.
    """
    to_user_id = request.data.get("to_user_id")
    action = request.data.get("action")

    if not to_user_id or not action:
        return Response(
            {"detail": "to_user_id and action are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action not in ["LIKE", "PASS"]:
        return Response(
            {"detail": "Invalid action. Use LIKE or PASS."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        to_user_id = int(to_user_id)
    except (TypeError, ValueError):
        return Response({"detail": "to_user_id must be integer."}, status=status.HTTP_400_BAD_REQUEST)

    if request.user.id == to_user_id:
        return Response(
            {"detail": "You cannot swipe yourself."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        to_user = User.objects.get(id=to_user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "Target user does not exist."},
            status=status.HTTP_404_NOT_FOUND,
        )

    match_id = None
    conversation_id = None
    is_match = False

    with transaction.atomic():
        swipe, created = SwipeAction.objects.update_or_create(
            from_user=request.user,
            to_user=to_user,
            defaults={"action": action},
        )

        # ✅ Only check mutual when action is LIKE
        if action == "LIKE":
            mutual = SwipeAction.objects.filter(
                from_user=to_user,
                to_user=request.user,
                action="LIKE"
            ).exists()

            if mutual:
                is_match = True

                u1_id, u2_id = ordered_pair(request.user.id, to_user.id)

                match_obj, _ = Match.objects.get_or_create(
                    user1_id=u1_id,
                    user2_id=u2_id,
                    defaults={"is_active": True},
                )
                match_id = match_obj.id

                conv_obj, _ = Conversation.objects.get_or_create(match=match_obj)
                conversation_id = conv_obj.id

                # ✅ optional notifications (uncomment if you have Notification model)
                Notification.objects.create(to_user=request.user, from_user=to_user, type="MATCH", data={"match_id": match_id, "conversation_id": conversation_id})
                Notification.objects.create(to_user=to_user, from_user=request.user, type="MATCH", data={"match_id": match_id, "conversation_id": conversation_id})

    return Response(
        {
            "id": swipe.id,
            "from_user": swipe.from_user_id,
            "to_user": swipe.to_user_id,
            "action": swipe.action,
            "created_at": swipe.created_at,
            "created": created,

            # ✅ match info
            "is_match": is_match,
            "match_id": match_id,
            "conversation_id": conversation_id,
        },
        status=status.HTTP_201_CREATED,
    )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_swipes(request):
    """
    GET: returns swipes made by logged-in user
    """
    swipes = (
        SwipeAction.objects
        .filter(from_user=request.user)
        .select_related("to_user")
        .order_by("-created_at")
    )

    data = []
    for s in swipes:
        data.append(
            {
                "id": s.id,
                "to_user_id": s.to_user_id,
                "to_user_email": s.to_user.email,
                "action": s.action,
                "created_at": s.created_at,
            }
        )

    return Response(data)





# ---------------------------- Haversine Km -------------------
import math

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Return distance between two points in KM.
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


import math
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SwipeAction
from accounts.models import UserProfileSelection
from accounts.models import UserLocation

User = get_user_model()


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Return distance between two points in KM.
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2) + (math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def feed(request):
    """
    GET /feed/?radius_km=50&limit=20

    Rules:
    - Exclude me
    - Exclude LIKE forever
    - Exclude PASS only for last 7 days
    - Only users with profile + location
    - Filter within radius_km
    - Rank by (taxonomy match score desc, distance asc)
    """

    # ---- query params ----
    try:
        radius_km = float(request.query_params.get("radius_km", 50))
    except (TypeError, ValueError):
        radius_km = 50.0

    try:
        limit = int(request.query_params.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20

    # ---- my location required ----
    try:
        my_loc = request.user.location  # related_name="location"
    except UserLocation.DoesNotExist:
        return Response(
            {"detail": "Your location is not set. Please save UserLocation first."},
            status=400
        )

    # ---- my profile required ----
    if not hasattr(request.user, "profile"):
        return Response(
            {"detail": "Your profile is not set."},
            status=400
        )

    # ---- my taxonomy items ----
    my_item_ids = set(
        UserProfileSelection.objects.filter(profile=request.user.profile)
        .values_list("item_id", flat=True)
    )

    # ---- exclude rules (LIKE forever, PASS only 7 days) ----
    cutoff = timezone.now() - timedelta(days=7)

    liked_ids = SwipeAction.objects.filter(
        from_user=request.user,
        action="LIKE",
    ).values_list("to_user_id", flat=True)

    passed_recent_ids = SwipeAction.objects.filter(
        from_user=request.user,
        action="PASS",
        created_at__gte=cutoff,  # only last 7 days
    ).values_list("to_user_id", flat=True)

    # combine
    exclude_ids = liked_ids.union(passed_recent_ids)

    # ---- candidate base queryset ----
    qs = (
        User.objects
        .exclude(id=request.user.id)
        .exclude(id__in=exclude_ids)
        .filter(profile__isnull=False)
        .filter(location__isnull=False)
        .select_related("profile", "location")
    )

    # ---- compute score + distance in python ----
    results = []
    for u in qs:
        d_km = haversine_km(
            my_loc.latitude, my_loc.longitude,
            u.location.latitude, u.location.longitude
        )
        if d_km > radius_km:
            continue

        cand_item_ids = set(
            UserProfileSelection.objects.filter(profile=u.profile)
            .values_list("item_id", flat=True)
        )
        score = len(my_item_ids.intersection(cand_item_ids))

        results.append((score, d_km, u))

    # ---- sort: score desc, distance asc ----
    results.sort(key=lambda x: (-x[0], x[1]))
    results = results[:limit]

    # ---- response ----
    data = []
    for score, d_km, u in results:
        p = u.profile

        photo_url = None
        if p.photo:
            photo_url = request.build_absolute_uri(p.photo.url)

        data.append({
            "user_id": u.id,
            "full_name": p.full_name,
            "role": p.role,
            "industry": p.industry,
            "location": p.location,
            "bio": p.bio,
            "photo": photo_url,
            "match_score": score,
            "distance_km": round(d_km, 2),
        })

    return Response(data)
