from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.auth import PermissionPolicyChecker
from wagtail.admin.forms.search import SearchForm
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.admin.models import popular_tags_for_model
from wagtail.models import Collection
from wagtail.search.backends import get_search_backends

from wagtailmedia.forms import get_media_form
from wagtailmedia.media_types import get_media_type, get_media_type_slugs, get_media_types
from wagtailmedia.models import get_media_model
from wagtailmedia.permissions import permission_policy
from wagtailmedia.utils import paginate


permission_checker = PermissionPolicyChecker(permission_policy)


def _make_upload_forms(Media, MediaForm, user, *, limit_to=None, bound_form=None, bound_slug=None):
    upload_forms = {}

    for media_type_def in get_media_types():
        if limit_to and media_type_def.slug not in limit_to:
            continue

        if bound_slug and media_type_def.slug == bound_slug and bound_form is not None:
            form = bound_form
        else:
            media = Media(uploaded_by_user=user, type=media_type_def.slug)
            form = MediaForm(
                user=user, prefix="media-chooser-upload", instance=media
            )
        upload_forms[media_type_def.slug] = form

    return upload_forms


def _make_upload_form_tabs(upload_forms):
    upload_form_tabs = []

    for media_type_def in get_media_types():
        if media_type_def.slug in upload_forms:
            upload_form_tabs.append(
                {
                    "slug": media_type_def.slug,
                    "tab_id": f"upload-{media_type_def.slug}",
                    "label": media_type_def.upload_tab_label,
                    "errors_count": len(upload_forms[media_type_def.slug].errors),
                }
            )

    return upload_form_tabs


def get_media_json(media):
    """
    helper function: given a media, return the json to pass back to the
    chooser panel
    """

    return {
        "id": media.id,
        "title": media.title,
        "edit_url": reverse("wagtailmedia:edit", args=(media.id,)),
    }


def get_ordering(request):
    if request.GET.get("ordering") in ["title", "-title", "-created_at", "created_at"]:
        return request.GET["ordering"]

    # default to -created_at
    return "-created_at"


def chooser(request, media_type=None):
    Media = get_media_model()

    ordering = get_ordering(request)
    media_files = permission_policy.instances_user_has_any_permission_for(
        request.user, ["change", "delete"]
    )

    # allow hooks to modify the queryset
    for hook in hooks.get_hooks("construct_media_chooser_queryset"):
        media_files = hook(media_files, request)

    if permission_policy.user_has_permission(request.user, "add"):
        MediaForm = get_media_form(Media)
        limit_to = {media_type} if media_type else None
        uploadforms = _make_upload_forms(
            Media, MediaForm, request.user, limit_to=limit_to
        )
    else:
        uploadforms = {}

    uploadform_tabs = _make_upload_form_tabs(uploadforms)
    first_uploadform = next(iter(uploadforms.values()), None)

    if media_type:
        media_files = media_files.filter(type=media_type)
        chooser_url = reverse("wagtailmedia:chooser_typed", args=(media_type,))
    else:
        chooser_url = reverse("wagtailmedia:chooser")

    if (
        "q" in request.GET
        or "p" in request.GET
        or "tag" in request.GET
        or "collection_id" in request.GET
    ):
        collection_id = request.GET.get("collection_id")
        if collection_id:
            media_files = media_files.filter(collection=collection_id)

        searchform = SearchForm(request.GET)
        if searchform.is_valid() and searchform.cleaned_data["q"]:
            q = searchform.cleaned_data["q"]

            media_files = media_files.search(q)
            is_searching = True
        else:
            media_files = media_files.order_by(ordering)
            is_searching = False
            q = None

            tag_name = request.GET.get("tag")
            if tag_name:
                media_files = media_files.filter(tags__name=tag_name)

        # Pagination
        paginator, media_files = paginate(request, media_files)

        return render(
            request,
            "wagtailmedia/chooser/results.html",
            {
                "media_files": media_files,
                "query_string": q,
                "is_searching": is_searching,
                "media_type": media_type,
                "ordering": ordering,
                "chooser_url": chooser_url,
                "elided_page_range": paginator.get_elided_page_range(
                    request.GET.get("p", 1)
                ),
            },
        )
    else:
        searchform = SearchForm()

        collections = Collection.objects.all()
        if len(collections) < 2:
            collections = None

        media_files = media_files.order_by(ordering)
        paginator, media_files = paginate(request, media_files)

    if media_type in get_media_type_slugs():
        title = get_media_type(media_type).choose_title
    else:
        title = _("Choose a media item")

    return render_modal_workflow(
        request,
        "wagtailmedia/chooser/chooser.html",
        None,
        {
            "media_files": media_files,
            "searchform": searchform,
            "collections": collections,
            "uploadforms": uploadforms,
            "uploadform_tabs": uploadform_tabs,
            "first_uploadform": first_uploadform,
            "is_searching": False,
            "popular_tags": popular_tags_for_model(Media),
            "media_type": media_type,
            "ordering": ordering,
            "title": title,
            "icon": "media"
            if media_type == "model3d"
            else (f"wagtailmedia-{media_type}" if media_type is not None else "media"),
            "chooser_url": chooser_url,
            "elided_page_range": paginator.get_elided_page_range(
                request.GET.get("p", 1)
            ),
        },
        json_data={
            "step": "chooser",
            "error_label": "Server Error",
            "error_message": "Report this error to your webmaster with the following information:",
            "tag_autocomplete_url": reverse("wagtailadmin_tag_autocomplete"),
        },
    )


def media_chosen(request, media_id):
    media = get_object_or_404(get_media_model(), id=media_id)

    return render_modal_workflow(
        request,
        None,
        None,
        None,
        json_data={"step": "media_chosen", "result": get_media_json(media)},
    )


@permission_checker.require("add")
def chooser_upload(request, media_type):
    upload_forms = {}
    uploadform_tabs = []
    first_uploadform = None

    if (
        permission_policy.user_has_permission(request.user, "add")
        and request.method == "POST"
    ):
        Media = get_media_model()
        MediaForm = get_media_form(Media)

        media = Media(uploaded_by_user=request.user, type=media_type)
        uploading_form = MediaForm(
            request.POST,
            request.FILES,
            instance=media,
            user=request.user,
            prefix="media-chooser-upload",
        )
        if uploading_form.is_valid():
            uploading_form.save()

            # Reindex the media entry to make sure all tags are indexed
            for backend in get_search_backends():
                backend.add(media)

            return render_modal_workflow(
                request,
                None,
                None,
                None,
                json_data={"step": "media_chosen", "result": get_media_json(media)},
            )
        upload_forms = _make_upload_forms(
            Media,
            MediaForm,
            request.user,
            bound_form=uploading_form,
            bound_slug=media_type,
        )
        uploadform_tabs = _make_upload_form_tabs(upload_forms)
        first_uploadform = next(iter(upload_forms.values()), None)

    ordering = get_ordering(request)

    media_files = permission_policy.instances_user_has_any_permission_for(
        request.user, ["change", "delete"]
    )

    # allow hooks to modify the queryset
    for hook in hooks.get_hooks("construct_media_chooser_queryset"):
        media_files = hook(media_files, request)

    searchform = SearchForm()

    collections = Collection.objects.all()
    if len(collections) < 2:
        collections = None

    media_files = media_files.order_by(ordering)
    paginator, media_files = paginate(request, media_files)

    chooser_url = reverse("wagtailmedia:chooser_typed", args=(media_type,))

    if media_type in get_media_type_slugs():
        title = get_media_type(media_type).choose_title
    else:
        title = _("Choose a media item")

    context = {
        "media_files": media_files,
        "searchform": searchform,
        "collections": collections,
        "uploadforms": upload_forms,
        "uploadform_tabs": uploadform_tabs,
        "first_uploadform": first_uploadform,
        "is_searching": False,
        "media_type": media_type,
        "ordering": ordering,
        "chooser_url": chooser_url,
        "title": title,
        "icon": "media" if media_type == "model3d" else f"wagtailmedia-{media_type}",
    }
    return render_modal_workflow(
        request,
        "wagtailmedia/chooser/chooser.html",
        None,
        context,
        json_data={"step": "chooser"},
    )
