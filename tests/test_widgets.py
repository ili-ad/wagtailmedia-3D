from django.test import TestCase
from django.urls import reverse

from wagtailmedia import widgets
from wagtailmedia.widgets import (
    AdminAudioChooser,
    AdminMediaChooser,
    AdminModel3DChooser,
    AdminVideoChooser,
)

from .utils import create_video


class WidgetTests(TestCase):
    def test_get_value_data(self):
        item = create_video(title="foo")

        test_data = [
            # (input value, expected output value)
            (None, None),
            (
                item.pk,
                {
                    "id": item.pk,
                    "title": "foo",
                    "edit_url": f"/admin/media/edit/{item.pk}/",
                },
            ),
            (
                item,
                {
                    "id": item.pk,
                    "title": "foo",
                    "edit_url": f"/admin/media/edit/{item.pk}/",
                },
            ),
        ]

        media_chooser = widgets.AdminMediaChooser()
        for input_value, expected_output in test_data:
            self.assertEqual(media_chooser.get_value_data(input_value), expected_output)


class AdminMediaChooserTest(TestCase):
    def test_default_chooser_text(self):
        chooser = AdminMediaChooser()
        self.assertEqual(chooser.choose_one_text, "Choose a media item")
        self.assertEqual(chooser.choose_another_text, "Choose another media item")
        self.assertEqual(chooser.link_to_chosen_text, "Edit this media item")

    def test_audio_chooser_text(self):
        chooser = AdminAudioChooser()
        self.assertEqual(chooser.choose_one_text, "Choose audio")
        self.assertEqual(chooser.choose_another_text, "Choose another audio item")
        self.assertEqual(chooser.link_to_chosen_text, "Edit this audio item")

    def test_video_chooser_text(self):
        chooser = AdminVideoChooser()
        self.assertEqual(chooser.choose_one_text, "Choose video")
        self.assertEqual(chooser.choose_another_text, "Choose another video")
        self.assertEqual(chooser.link_to_chosen_text, "Edit this video")

    def test_model3d_chooser_text(self):
        chooser = AdminModel3DChooser()
        self.assertEqual(chooser.choose_one_text, "Choose a 3D model")
        self.assertEqual(chooser.choose_another_text, "Choose another 3D model")
        self.assertEqual(chooser.link_to_chosen_text, "Edit this 3D model")

    def test_render_html_uses_the_generic_chooser_url_by_default(self):
        chooser = AdminMediaChooser()
        self.assertEqual(
            chooser.get_chooser_modal_url(), reverse("wagtailmedia:chooser")
        )

    def test_render_html_uses_the_typed_chooser_url_when_using_media_type(self):
        chooser = AdminAudioChooser()
        self.assertEqual(
            chooser.get_chooser_modal_url(),
            reverse("wagtailmedia:chooser_typed", args=("audio",)),
        )

    def test_render_html_uses_typed_chooser_url_for_model3d(self):
        chooser = AdminModel3DChooser()
        self.assertEqual(
            chooser.get_chooser_modal_url(),
            reverse("wagtailmedia:chooser_typed", args=("model3d",)),
        )
