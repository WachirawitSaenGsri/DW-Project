from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("api/summary", views.api_summary, name="api_summary"),
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
