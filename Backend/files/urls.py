from django.urls import path

from . import views

urlpatterns = [
    path("", views.UploadView.as_view(), name="file-upload"),
    path("download/<str:token>/", views.download, name="file-download"),
    path("<uuid:file_id>/", views.FileDetailView.as_view(), name="file-detail"),
]
