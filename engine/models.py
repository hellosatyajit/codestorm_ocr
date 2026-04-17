"""Data model for the PDF translation engine.

A `Document` is a single upload. It owns `Page` rows (one per PDF page, or
one per image upload) which in turn own `Block` rows (one per OCR region).
All bounding boxes are stored in PDF points with the top-left origin
PyMuPDF uses, so the rebuild step and the frontend canvas share one
coordinate system.
"""
from __future__ import annotations

import uuid

from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_file = models.FileField(upload_to="originals/")
    translated_file = models.FileField(upload_to="translated/", null=True, blank=True)
    source_lang = models.CharField(max_length=10, default="auto")
    target_lang = models.CharField(max_length=10, default="en")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Document {self.id} ({self.status})"


class Page(models.Model):
    document = models.ForeignKey(Document, related_name="pages", on_delete=models.CASCADE)
    index = models.IntegerField()
    width_pt = models.FloatField()
    height_pt = models.FloatField()
    preview = models.ImageField(upload_to="previews/", null=True, blank=True)

    class Meta:
        ordering = ("document_id", "index")
        unique_together = (("document", "index"),)

    def __str__(self) -> str:
        return f"Page {self.index} of {self.document_id}"


class Block(models.Model):
    class Type(models.TextChoices):
        PARAGRAPH = "paragraph", "Paragraph"
        HEADING = "heading", "Heading"
        LIST = "list", "List"
        TABLE_CELL = "table_cell", "Table cell"

    page = models.ForeignKey(Page, related_name="blocks", on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    block_type = models.CharField(max_length=20, choices=Type.choices, default=Type.PARAGRAPH)
    x0 = models.FloatField()
    y0 = models.FloatField()
    x1 = models.FloatField()
    y1 = models.FloatField()
    original_text = models.TextField()
    translated_text = models.TextField(blank=True, default="")
    detected_lang = models.CharField(max_length=16, blank=True, default="")
    confidence = models.FloatField(default=0.0)
    font_size_pt = models.FloatField(default=11.0)

    class Meta:
        ordering = ("page_id", "order")

    def __str__(self) -> str:
        preview = (self.original_text or "")[:40]
        return f"Block#{self.pk} [{self.block_type}] {preview!r}"

    @property
    def bbox(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]
