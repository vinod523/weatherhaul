from django.urls import path, re_path
from django.http import FileResponse, JsonResponse
from django.conf import settings
from routing.views import plan, health

def frontend(request):
    file = settings.BASE_DIR.parent / 'dist' / 'index.html'
    return FileResponse(file.open('rb'), content_type='text/html') if file.exists() else JsonResponse({'detail':'Build React with npm run build first.'}, status=503)
urlpatterns = [path('api/plan', plan), path('api/health', health), re_path(r'^(?!api/|assets/).*$', frontend)]
