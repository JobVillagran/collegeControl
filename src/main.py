from __future__ import annotations

from config.constants import SUMMARY_TITLE
from config.settings import CHANGES_FILE, SEND_EMAIL, UPCOMING_FILE
from src.services.comparison_service import ComparisonService
from src.services.config_validator import validate_required_config
from src.services.email_service import EmailService
from src.services.notification_decision_service import NotificationDecisionService
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
    notification_decision_service = NotificationDecisionService()

    previous_snapshot = snapshot_service.load_previous_snapshot()

    logger.info("Fetching courses from Canvas API.")
    courses = scraping_service.get_courses()
    logger.info("Courses fetched: %s", len(courses))

    logger.info("Fetching assignments from Canvas API.")
    assignments = scraping_service.get_assignments(courses)
    logger.info("Assignments fetched: %s", len(assignments))

    current_snapshot = snapshot_service.build_snapshot(
        courses=courses,
        assignments=assignments,
    )
    snapshot_service.save_current_snapshot(current_snapshot)

    changes = comparison_service.compare(previous_snapshot, current_snapshot)
    write_json(CHANGES_FILE, changes)
    write_json(UPCOMING_FILE, changes.get("actionable_groups", {}))

    payload = summary_service.build_payload(changes)
    html = summary_service.render_html(payload)
    text = summary_service.render_text(payload)
    summary_service.save_outputs(payload, html, text)

    sections = payload.get("sections", {})
    logger.info(
        "Payload summary | act_now=%s | this_week=%s | next_week=%s | third_week=%s | urgent_projects=%s | opens_same_day=%s | no_due_date=%s | changed_assignments=%s | new_grades=%s",
        len(sections.get("act_now", [])),
        len(sections.get("this_week", [])),
        len(sections.get("next_week", [])),
        len(sections.get("third_week", [])),
        len(sections.get("urgent_projects", [])),
        len(sections.get("opens_same_day", [])),
        len(sections.get("no_due_date", [])),
        len(sections.get("changed_assignments", [])),
        len(sections.get("new_grades", [])),
    )

    if SEND_EMAIL:
        should_send, reason = notification_decision_service.should_send_email(payload)
        logger.info("Notification decision: %s", reason)

        if should_send:
            logger.info("Sending email summary.")
            email_service.send_summary(
                subject=SUMMARY_TITLE,
                html_body=html,
                text_body=text,
            )
            notification_decision_service.mark_email_sent(payload)
            logger.info("Email sent successfully.")
        else:
            logger.info("Email skipped by notification rules.")
    else:
        logger.info("SEND_EMAIL is false. Skipping email delivery.")

    logger.info("University monitor finished successfully.")


if __name__ == "__main__":
    main()