import re
import shutil
import tempfile

from typing import Optional

from django.core.files.base import ContentFile
from django.test import TestCase

from wagtailmedia.models import MediaType, get_media_model


Media = get_media_model()


class TempDirMediaRootMixin(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def run(self, result=None):
        with self.settings(MEDIA_ROOT=self.tmpdir):
            return super().run(result)


def create_media(
    media_type: str,
    title: str,
    duration: Optional[int] = 100,
    thumbnail: Optional[str] = False,
) -> Media:
    filename = re.sub(r"[/:\"\'] ", "_", title).lower()
    if media_type == MediaType.AUDIO:
        extension = "mp3"
    elif media_type == MediaType.VIDEO:
        extension = "mp4"
    elif media_type == MediaType.MODEL3D:
        extension = "glb"
    else:
        extension = "bin"
    item = Media.objects.create(
        type=media_type,
        title=title,
        duration=duration,
        file=ContentFile("📼", name=f"{filename}.{extension}"),
    )

    if thumbnail:
        item.thumbnail = ContentFile("Thumbnail", name=thumbnail)
        item.save()

    return item


def create_video(title="Test video", duration=100, thumbnail=None) -> Media:
    return create_media(
        MediaType.VIDEO, title=title, duration=duration, thumbnail=thumbnail
    )


def create_audio(title="Test audio", duration=100, thumbnail=None) -> Media:
    return create_media(
        MediaType.AUDIO, title=title, duration=duration, thumbnail=thumbnail
    )


def create_model3d(title="Test 3D model", duration=0, thumbnail=None) -> Media:
    return create_media(
        MediaType.MODEL3D, title=title, duration=duration, thumbnail=thumbnail
    )
