from django.conf import settings
from django.db import models
from django.db.models import Q


class SwipeAction(models.Model):
    ACTION_LIKE = "LIKE"
    ACTION_PASS = "PASS"
    ACTION_CHOICES = (
        (ACTION_LIKE, "LIKE"),
        (ACTION_PASS, "PASS"),
    )

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="swipes_made")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="swipes_received")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="uniq_swipe_pair",
            ),
         
            models.CheckConstraint(
                condition=~Q(from_user=models.F("to_user")),
                name="no_self_swipe",
            ),
        ]
        indexes = [
            models.Index(fields=["from_user", "created_at"]),
            models.Index(fields=["to_user", "created_at"]),
            models.Index(fields=["from_user", "to_user"]),
        ]

    def __str__(self):
        return f"{self.from_user_id} -> {self.to_user_id} [{self.action}]"
