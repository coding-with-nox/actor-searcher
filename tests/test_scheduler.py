from app.scheduler.scheduler_service import SchedulerService


def test_scheduler_instantiates() -> None:
    service = SchedulerService(orchestrator=None)  # type: ignore[arg-type]
    assert service.scheduler is not None
