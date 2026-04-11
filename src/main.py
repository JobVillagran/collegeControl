from __future__ import annotations

from config.constants import SUMMARY_TITLE
from config.settings import CHANGES_FILE, SEND_EMAIL, UPCOMING_FILE
from src.services.comparison_service import ComparisonService
from src.services.config_validator import validate_required_config
from src.services.email_service import EmailService
from src.services.scraping_service import ScrapingService
from src.services.snapshot_service import SnapshotService
from src.services.summary_service import SummaryService
from src.utils.file_utils import write_json
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    validate_required_config()
    logger.info("Starting university monitor.")

    snapshot_service = SnapshotService()
    comparison_service = ComparisonService()
    summary_service = SummaryService()
    email_service = EmailService()
    scraping_service = ScrapingService()

    previous_snapshot = snapshot_service.load_previous_snapshot()

    logger.info("Fetching courses from Canvas API.")
    courses = scraping_service.get_courses()

    logger.info("Fetching assignments from Canvas API.")
    assignments = scraping_service.get_assignments(courses)

    current_snapshot = snapshot_service.build_snapshot(
        courses=courses,
        assignments=assignments,
    )
    snapshot_service.save_current_snapshot(current_snapshot)

    changes = comparison_service.compare(previous_snapshot, current_snapshot)
    write_json(CHANGES_FILE, changes)
    write_json(UPCOMING_FILE, changes.get("upcoming_assignments", []))

    payload = summary_service.build_payload(changes)
    html = summary_service.render_html(payload)
    text = summary_service.render_text(payload)
    summary_service.save_outputs(payload, html, text)

    if SEND_EMAIL:
        logger.info("Sending email summary.")
        email_service.send_summary(
            subject=SUMMARY_TITLE,
            html_body=html,
            text_body=text,
        )
    else:
        logger.info("SEND_EMAIL is false. Skipping email delivery.")

    logger.info("University monitor finished successfully.")


if __name__ == "__main__":
    main()