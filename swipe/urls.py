from django.urls import path
from .views import swipe_action_create, my_swipes, feed

urlpatterns = [
    path("swipes/", swipe_action_create, name="swipe-create"),   # antother person like or disliek ( swipe action create )
    path("swipes/me/", my_swipes, name="my-swipes"),  # WHOS PEOPLE I LIKED OR DISLIKED ( swipe action list )
    path("feed/", feed, name="feed"),
]
 