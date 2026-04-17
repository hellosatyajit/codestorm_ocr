"""URL routes for the translation engine."""
from django.urls import path

from . import views

app_name = "engine"

urlpatterns = [
    path("", views.upload_view, name="upload"),
    path("doc/<uuid:doc_id>/", views.results_view, name="results"),
    path("doc/<uuid:doc_id>/blocks.json", views.blocks_json, name="blocks_json"),
    path("doc/<uuid:doc_id>/download.json", views.download_json, name="download_json"),
    path("doc/<uuid:doc_id>/download.pdf", views.download_pdf, name="download_pdf"),
    path(
        "doc/<uuid:doc_id>/original",
        views.view_original,
        name="view_original",
    ),
    path(
        "doc/<uuid:doc_id>/translated.pdf",
        views.view_translated_pdf,
        name="view_translated_pdf",
    ),
]
