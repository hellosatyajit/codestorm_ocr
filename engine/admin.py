from django.contrib import admin

from .models import Block, Document, Page


class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    fields = ("index", "width_pt", "height_pt", "preview")
    readonly_fields = fields


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "source_lang", "target_lang", "created_at")
    list_filter = ("status", "source_lang", "target_lang")
    search_fields = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [PageInline]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "index", "width_pt", "height_pt")
    list_filter = ("document__status",)
    search_fields = ("document__id",)


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "page",
        "order",
        "block_type",
        "detected_lang",
        "confidence",
        "short_text",
    )
    list_filter = ("block_type", "detected_lang")
    search_fields = ("original_text", "translated_text")

    @admin.display(description="Text")
    def short_text(self, obj: Block) -> str:
        return (obj.original_text or "")[:60]
