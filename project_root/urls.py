from django.contrib import admin
from django.urls import path , include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,

)

from project_root import settings
from django.conf import settings
from django.conf.urls.static import static

from accounts.views import report_user_view, block_user_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swager/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path('api/accounts/', include('accounts.urls')),
    path('api/preferences/', include('preferences.urls')),
    path('api/swipe/', include('swipe.urls')),
    path('api/match/', include('match.urls')),
    path('api/users/<int:id>/report/', report_user_view, name='report-user'),
    path('api/users/<int:id>/block/', block_user_view, name='block-user'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)