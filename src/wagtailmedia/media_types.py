from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class MediaTypeDef:
    slug: str
    # Keep full phrases (don’t compose strings) so translations remain flexible.
    choose_title: str
    upload_tab_label: str
    add_button_label: str


# Canonical order matters for UI and for tests (audio first, then video)
MEDIA_TYPES: tuple[MediaTypeDef, ...] = (
    MediaTypeDef(
        slug="audio",
        choose_title=_("Choose audio"),
        upload_tab_label=_("Upload Audio"),
        add_button_label=_("Add audio"),
    ),
    MediaTypeDef(
        slug="video",
        choose_title=_("Choose video"),
        upload_tab_label=_("Upload Video"),
        add_button_label=_("Add video"),
    ),
    MediaTypeDef(
        slug="model3d",
        choose_title=_("Choose 3D model"),
        upload_tab_label=_("Upload 3D model"),
        add_button_label=_("Add 3D model"),
    ),
)

MEDIA_TYPE_BY_SLUG: Mapping[str, MediaTypeDef] = {mt.slug: mt for mt in MEDIA_TYPES}


def get_media_types() -> tuple[MediaTypeDef, ...]:
    return MEDIA_TYPES


def get_index_media_types() -> tuple[MediaTypeDef, ...]:
    # Kept for backwards compatibility; index now surfaces all media types.
    return get_media_types()


def get_media_type(slug: str) -> MediaTypeDef:
    return MEDIA_TYPE_BY_SLUG[slug]


def get_media_type_slugs() -> tuple[str, ...]:
    return tuple(mt.slug for mt in MEDIA_TYPES)


def get_media_type_slugs_regex() -> str:
    # Safe today because slugs are simple; keep a single function so future changes are centralized.
    return "|".join(get_media_type_slugs())
