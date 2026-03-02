from celery import shared_task
from org.services.versioning import create_org_version
from org.services.snapshots import generate_snapshot


@shared_task
def nightly_org_versioning():
    version = create_org_version()
    return f"Org version {version} created"


@shared_task
def nightly_org_snapshot():
    snap = generate_snapshot()
    return f"Snapshot {snap.id} created"
