"""URL configuration for the engine app."""

from django.urls import path

from engine import views

urlpatterns = [
    path("translate/", views.translate_blocks, name="translate_blocks"),
    path("languages/", views.list_languages, name="list_languages"),
    path("health/", views.health_check, name="health_check"),
]
