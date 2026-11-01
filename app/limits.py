"""Product limits, in one place. The values are part of the spec; change them deliberately."""

from datetime import timedelta

RATE_WINDOW_SECONDS = 60
AI_REQUESTS_PER_WINDOW = 10  # open planning endpoints, per client IP
PHOTO_UPLOADS_PER_WINDOW = 5  # photo ideas, per signed-in user

MAX_IMAGE_BYTES = 5_000_000
MAX_SPEND_ENTRIES = 500  # keeps each Firestore document well under its 1 MiB limit
MAX_PHOTO_IDEAS_KEPT = 20
VENDOR_CACHE_TTL = timedelta(hours=24)
