from django.urls import path
from .views import connected_users_list, connected_users_list_for_people, my_notifications

urlpatterns = [
    path("connections/", connected_users_list, name="connected-users-list"),
    path("connections/for-people/", connected_users_list_for_people, name="connected-users-list-for-people"),
    path("notifications_list/", my_notifications, name="my-notifications"),

    
]
