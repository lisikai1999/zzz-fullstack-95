from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        _run_sync_resources,
        trigger=IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES),
        id="sync_resources",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_sync_topology,
        trigger=IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES),
        id="sync_topology",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_check_certificates,
        trigger=IntervalTrigger(hours=settings.CERT_CHECK_INTERVAL_HOURS),
        id="check_certificates",
        replace_existing=True,
    )

    scheduler.start()
    return scheduler


def _run_sync_resources():
    from backend.scheduler.jobs.sync_resources import sync_all_resources
    sync_all_resources()


def _run_sync_topology():
    from backend.scheduler.jobs.sync_topology import sync_all_topologies
    sync_all_topologies()


def _run_check_certificates():
    from backend.scheduler.jobs.check_certificates import check_all_certificates
    check_all_certificates()
