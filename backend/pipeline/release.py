"""The pinned Overture Maps release.

Every read in the pipeline goes through :func:`overture_path` so the release string exists in
exactly one place. It is also reported in the API's ``meta.overture_release`` so results are
reproducible against the data they came from.
"""

# Resolved by listing s3://overturemaps-us-west-2/release/ on 2026-09-19; latest at that time.
OVERTURE_RELEASE = "2026-08-19.0"

OVERTURE_BUCKET = "s3://overturemaps-us-west-2/release"
OVERTURE_S3_REGION = "us-west-2"


def overture_path(theme: str, type_: str) -> str:
    """Return the S3 glob for one Overture ``theme``/``type`` in the pinned release."""
    return f"{OVERTURE_BUCKET}/{OVERTURE_RELEASE}/theme={theme}/type={type_}/*"
