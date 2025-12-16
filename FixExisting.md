## Codex Ticket: Fix 3D model chooser crash in Wagtail admin (`NoReverseMatch: chooser_typed(model3d)`)

### Title

Fix `AdminModelChooser` URL + add a safe “model-only” filter for the media chooser (so ProductPage edit loads and the 3D model chooser works)

---

### Context

You’re hitting:

> `NoReverseMatch: Reverse for 'chooser_typed' with arguments ('model3d',) not found … tried: admin/media/chooser/(?P<media_type>audio|video)/`

That comes from `AdminModelChooser.get_chooser_modal_url()` which currently does:

```py
return reverse("wagtailmedia:chooser_typed", args=(self.media_type,))
```

…with `media_type = "model3d"` 

But WagtailMedia’s `chooser_typed` URL only recognizes `audio|video`, so reversing with `model3d` will always fail (and it fails during ProductPage edit rendering before you even click anything).

You already *do* have a custom chooser endpoint in your project URLConf:

```py
path("media/chooser/model/", model_chooser, name="wagtailmedia_model_chooser")
```



…and a hook that can filter GLB files, but only when `media_type == "model3d"` .

Also, your current `custom_media_chooser.html` is essentially a stub and does not render the full chooser UI, so even after fixing the reverse, the modal would be a blank shell unless we restore a proper template .

---

### Goals

1. **Wagtail ProductPage edit loads** (no chooser URL reverse errors).
2. The `model_3d` FieldPanel chooser opens a functioning modal.
3. The chooser modal shows **only `.glb`** files (or `.glb` + `.gltf` if you want later).
4. Upload within that chooser is restricted to `.glb` via your `Custom3DMediaForm` (server-side validation) .
5. This fix is localized and does **not** require patching third-party wagtailmedia URL regexes.

---

### Non-goals

* Don’t redesign WagtailMedia or introduce a new ViewSet chooser (we can do that later if desired).
* Don’t change DB schema.
* Don’t touch the configurator models.

---

## Files in scope

* `apps/django/products/widgets.py` 
* `apps/django/products/views.py` 
* `apps/django/products/wagtail_hooks.py` 
* `apps/django/products/templates/wagtailmedia/chooser/custom_media_chooser.html` 
* `apps/django/myproject/urls.py` (optional small URL placement tweak) 

---

# Implementation plan (explicit edits, no patches)

## Step 1) Fix the chooser URL so it doesn’t use `wagtailmedia:chooser_typed(model3d)`

In `apps/django/products/widgets.py`, update `AdminModelChooser.get_chooser_modal_url`.

### Current code

```py
def get_chooser_modal_url(self):
    return reverse("wagtailmedia:chooser_typed", args=(self.media_type,))
```



### Replace with

```py
from urllib.parse import urlencode

def get_chooser_modal_url(self):
    # Use our project-level model chooser URL (does not rely on wagtailmedia's typed regex)
    base = reverse("wagtailmedia_model_chooser")
    params = {"model3d": "1"}  # tells hooks/views to filter to .glb
    glue = "&" if "?" in base else "?"
    return f"{base}{glue}{urlencode(params)}"
```

Why:

* This completely avoids the unsupported `chooser_typed(model3d)` reverse.
* We pass an explicit `model3d=1` flag so the filtering logic can be clean and doesn’t depend on wagtailmedia accepting `media_type=model3d`.

Optional (recommended): set the widget upload form class so uploads validate `.glb`:

```py
from products.forms import Custom3DMediaForm

class AdminModelChooser(AdminMediaChooser):
    ...
    form_class = Custom3DMediaForm
```

This mirrors what you already do in the StreamField `ModelChooserBlock` path , but applies it to the ProductPage field widget as well.

---

## Step 2) Make the chooser view respect the `model3d=1` flag and keep wagtailmedia happy

In `apps/django/products/views.py`, update `model_chooser`.

### Current

```py
def model_chooser(request):
    # Force media_type=video and use our template
    request.GET = request.GET.copy()
    request.GET['media_type'] = 'video'
    response = media_chooser_view(request)
    response.template_name = 'wagtailmedia/chooser/custom_media_chooser.html'
    return response
```



### Keep the `media_type='video'` (important)

Do not set `media_type='model3d'` because wagtailmedia’s chooser UI machinery is wired around audio/video tabs and forms.

But add one line to *preserve* the `model3d=1` flag:

```py
def model_chooser(request):
    request.GET = request.GET.copy()
    request.GET["media_type"] = "video"  # keep wagtailmedia chooser stable
    # do NOT delete model3d=1 if present; our hook will filter by extension
    response = media_chooser_view(request)
    response.template_name = "wagtailmedia/chooser/custom_media_chooser.html"
    return response
```

---

## Step 3) Update the queryset filter hook to key off `model3d=1` (not media_type=model3d)

In `apps/django/products/wagtail_hooks.py`, you currently filter based on `media_type` :

```py
media_type = request.GET.get("media_type", "").lower()
if media_type == "model3d":
    queryset = queryset.filter(file__iendswith=".glb")
elif media_type == "video":
    queryset = queryset.exclude(file__iendswith=".glb")
```

Change it to:

```py
@hooks.register("construct_media_chooser_queryset")
def filter_media_chooser_queryset(queryset, request):
    # Explicit flag used by AdminModelChooser / model_chooser
    if request.GET.get("model3d") == "1":
        return queryset.filter(file__iendswith=".glb")

    media_type = request.GET.get("media_type", "").lower()
    if media_type == "video":
        # Exclude GLB files for normal video chooser
        queryset = queryset.exclude(file__iendswith=".glb")
    return queryset
```

Why:

* Your `model_chooser` view must keep `media_type=video` for wagtailmedia’s chooser UI stability.
* But you still want filtering to “models only”.
* The `model3d=1` flag is a clean, explicit switch.

---

## Step 4) Fix `custom_media_chooser.html` so it actually renders a chooser UI

Right now `custom_media_chooser.html` extends `wagtailadmin/base.html` and doesn’t include the real chooser internals . That risks showing a blank modal.

Replace it with the simple, robust approach you already started (commented out at the top): extend wagtailmedia’s chooser template and hide audio.

### Replace file with:

```django
{% extends "wagtailmedia/chooser/chooser.html" %}
{% load i18n %}

{# Remove audio upload UI #}
{% block audio_upload %}{% endblock %}

{% block extra_css %}
  {{ block.super }}
  <style>
    /* Hide audio tab if wagtailmedia renders it */
    .upload-tabs li[data-type="audio"],
    [data-tab-nav="audio"],
    [data-tab-content="audio"] {
      display: none !important;
    }
  </style>
{% endblock %}

{# Optional: adjust the modal title visually (non-critical) #}
{% block header %}
  {% include "wagtailadmin/shared/header.html" with title=_("Choose a 3D Model") icon="media" %}
{% endblock %}
```

This keeps all chooser functionality intact while removing the audio tab affordances.

---

## Step 5) (Optional but recommended) Move the URL under `/admin/` to match expectations

You currently have:

```py
path("media/chooser/model/", model_chooser, name="wagtailmedia_model_chooser")
```



It will work as-is, but it’s cleaner to put it under `/admin/` so it’s clearly an admin tool and matches other chooser routes:

Change to:

```py
path("admin/media/chooser/model/", model_chooser, name="wagtailmedia_model_chooser"),
```

This does **not** conflict with Wagtail’s `path("admin/", include(wagtailadmin_urls))` because Django matches the specific path before falling back into the include.

If you do this, nothing else needs to change because your widget reverses by name.

---

# Validation / test plan

## A) Confirm the crash is gone

1. Restart server.
2. Open: `http://localhost:8000/admin/pages/42/edit/`
3. Expected: page renders; no `NoReverseMatch` error.

## B) Confirm chooser opens and filters correctly

1. Go to the ProductPage “3D” tab and click “Choose a 3D model”.
2. Expected:

   * Modal opens.
   * Only `.glb` media items appear.
   * Audio tab does not appear.

## C) Confirm upload validation

1. In the chooser modal, upload a `.glb` → should succeed.
2. Try uploading `.mp4` → should fail with “Only .GLB files are allowed…” from `Custom3DMediaForm.clean_file()` .

---

# Definition of Done

* ✅ Product edit view loads (no chooser URL reversing error).
* ✅ `AdminModelChooser` no longer calls `reverse("wagtailmedia:chooser_typed", args=("model3d",))` .
* ✅ Clicking the `model_3d` chooser opens a functional modal.
* ✅ Modal shows only `.glb` files (filter enforced by hook)  (updated behavior).
* ✅ Upload rejects non-`.glb` via `Custom3DMediaForm` .
* ✅ No third-party wagtailmedia URL regex patching required.

---

## Notes (why this is the “least foot-gunny” fix)

* It avoids fighting wagtailmedia’s hardcoded typed chooser URL regex (audio|video).
* It reuses your existing infrastructure: custom view + hook + form validation.
* It keeps you aligned with the “world-class” direction: stable UX now, and later you can replace this with a fully custom `ChooserViewSet` if you want a dedicated “Models” tab, KTX2 previews, etc.

If you want, I can follow this with an “upgrade ticket” that replaces the `model_chooser` hack entirely with a proper Wagtail `ChooserViewSet` (cleaner long-term), but the above will get you unblocked immediately and correctly.
