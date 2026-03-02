from celery import shared_task
from analytics.services.analytics_engine import create_snapshot


@shared_task
def nightly_analytics_snapshot():
    snap = create_snapshot()
    return f"Analytics snapshot created: {snap.id}"