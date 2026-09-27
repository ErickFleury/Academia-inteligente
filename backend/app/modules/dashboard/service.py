"""Read-only, non-identifying aggregates for the administrative dashboard."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.occupancy.models import AccessPassageEvent
from app.modules.occupancy.service import OccupancyService, OccupancySnapshot


@dataclass(frozen=True)
class AttendanceWeek:
    week_start: date
    confirmed_entries: int


class DashboardService:
    """Derive bounded dashboard indicators without exposing ledger identities."""

    attendance_weeks = 8

    def __init__(self, occupancy_service: OccupancyService | None = None) -> None:
        self._occupancy_service = occupancy_service or OccupancyService()

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def active_client_count(self, session: Session) -> int:
        """Count only clients whose linked application account remains active."""
        return int(
            session.scalar(
                select(func.count(Client.id))
                .join(Account, Client.account_id == Account.id)
                .where(Account.account_active.is_(True), Client.active.is_(True))
            )
            or 0
        )

    def attendance_history(
        self, session: Session, now: datetime | None = None
    ) -> list[AttendanceWeek]:
        """Return eight UTC Monday-start weeks of confirmed client entry counts.

        The access ledger is timestamped in UTC for its authoritative occupancy
        calculations. This read model uses the same UTC calendar boundary and
        intentionally counts entry events, not unique people or time present.
        """
        current = self._utc(now or datetime.now(UTC))
        current_week_start = current.date() - timedelta(days=current.weekday())
        first_week_start = current_week_start - timedelta(weeks=self.attendance_weeks - 1)
        week_starts = [
            first_week_start + timedelta(weeks=index) for index in range(self.attendance_weeks)
        ]
        counts = {week_start.isoformat(): 0 for week_start in week_starts}
        cutoff = datetime.combine(first_week_start, datetime.min.time(), tzinfo=UTC)
        week_bucket = self._week_bucket(session)
        rows = session.execute(
            select(week_bucket.label("week_start"), func.count(AccessPassageEvent.id))
            .where(
                AccessPassageEvent.direction == "entry",
                AccessPassageEvent.event_type == "passage_confirmed",
                AccessPassageEvent.occurred_at >= cutoff,
            )
            .group_by(week_bucket)
            .order_by(week_bucket)
        )
        for week_start, count in rows:
            key = str(week_start)
            if key in counts:
                counts[key] = int(count)
        return [
            AttendanceWeek(week_start, counts[week_start.isoformat()]) for week_start in week_starts
        ]

    def occupancy(self, session: Session, now: datetime | None = None) -> OccupancySnapshot:
        """Read the existing authoritative Task 22 projection without mutation."""
        return self._occupancy_service.snapshot(session, now)

    @staticmethod
    def _week_bucket(session: Session):
        """Use database aggregation while preserving the UTC Monday-week contract.

        Production PostgreSQL and the repository's SQLite test database expose
        different date functions, so the equivalent SQL expression is selected
        at the persistence boundary rather than grouping ledger rows in Python.
        """
        if session.get_bind().dialect.name == "sqlite":
            return func.date(AccessPassageEvent.occurred_at, "weekday 0", "-6 days")
        return func.to_char(
            func.date_trunc("week", func.timezone("UTC", AccessPassageEvent.occurred_at)),
            "YYYY-MM-DD",
        )
