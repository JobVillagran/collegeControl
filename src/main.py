from __future__ import annotations

from src.bootstrap import BrowserManager
from src.services.auth_service import AuthService
from src.services.scraping_service import ScrapingService
from src.services.snapshot_service import SnapshotService
from src.services.comparison_service import ComparisonService
from src.services.summary_service import SummaryService
from src.services.email_service import EmailService
from src.utils.logger import get_logger
from src.utils.file_utils import write_json
from config.settings import CHANGES_FILE, UPCOMING_FILE
from config.constants import SUMMARY_TITLE
from config.settings import SEND_EMAIL
from src.services.config_validator import validate_required_config

validate_required_config()

logger = get_logger(__name__)


def main() -> None:
    logger.info("Starting university monitor.")

    snapshot_service = SnapshotService()
    comparison_service = ComparisonService()
    summary_service = SummaryService()
    email_service = EmailService()

    previous_snapshot = snapshot_service.load_previous_snapshot()

    with BrowserManager() as page:
        auth_service = AuthService(page)
        scraping_service = ScrapingService(page)

        logger.info("Logging into Canvas.")
        auth_service.login()

        logger.info("Scraping courses.")
        courses = scraping_service.get_courses()

        logger.info("Scraping assignments.")
        assignments = scraping_service.get_assignments(courses)

    current_snapshot = snapshot_service.build_snapshot(courses=courses, assignments=assignments)
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

    snapshot_service.rotate_snapshots(current_snapshot)

    logger.info("University monitor finished successfully.")

if __name__ == "__main__":
    main()