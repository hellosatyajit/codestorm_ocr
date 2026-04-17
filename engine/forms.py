"""Upload form for the translation engine."""
from __future__ import annotations

from django import forms
from django.conf import settings


TARGET_LANGUAGE_CHOICES = [
    ("en", "English"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("zh", "Chinese (Simplified)"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("ru", "Russian"),
]


class UploadForm(forms.Form):
    file = forms.FileField(
        label="PDF or image",
        help_text="PDF / PNG / JPEG / WEBP",
    )
    target_lang = forms.ChoiceField(
        choices=TARGET_LANGUAGE_CHOICES,
        initial="en",
        label="Translate to",
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        allowed = getattr(settings, "ALLOWED_UPLOAD_MIME_TYPES", set())
        if allowed and uploaded.content_type not in allowed:
            raise forms.ValidationError(
                f"Unsupported file type: {uploaded.content_type}. "
                "Upload a PDF, PNG, JPEG, or WebP file."
            )
        # 25 MB soft cap.
        if uploaded.size > 25 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 25 MB).")
        return uploaded
