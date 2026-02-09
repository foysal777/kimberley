from django.contrib import admin
from django.urls import path , include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,

)

from project_root import settings
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swager/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path('api/accounts/', include('accounts.urls')),
    path('api/preferences/', include('preferences.urls')),
    path('api/swipe/', include('swipe.urls')),
    path('api/match/', include('match.urls')),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)