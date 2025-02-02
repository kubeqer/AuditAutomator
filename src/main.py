from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger
from consts import DATABASE_URL
from database import init_database, put_report, store_generated_report, get_report
from lynis_json import parse_lynis_report_pydantic
from openscap_json import load_openscap_rules
from pdf_generator import generate_audit_report_pdf
from consts import GENERATED_DIR
from comparison import compare_objects


def run_full_pipeline(pdf_path: str) -> None:
    """
    Executes the full pipeline:
      1. Loads data from Lynis and OpenSCAP JSON files.
      2. Creates a new report in the database.
      3. Compares objects (every OpenSCAP record paired with each detail and suggestion).
      4. Stores the generated comparison results into the GeneratedReport table.
      5. Generates a PDF Audit Report based on the GeneratedReport records.

    Args:
        pdf_path: File path where the PDF report will be saved.
    """
    logger.info("Starting program.")
    init_database(echo=True)
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = SessionLocal()

    try:
        logger.info("Fetching data from JSON files.")
        detail_items, suggestion_items = parse_lynis_report_pydantic()
        openscap_rules = load_openscap_rules()
        logger.info(
            f"Fetched {len(detail_items)} detail items, {len(suggestion_items)} suggestion items, and {len(openscap_rules)} OpenSCAP rules."
        )
        logger.info("Creating a new report in the database.")
        report_data = put_report(
            session, openscap_rules, detail_items, suggestion_items
        )
        new_report_id = report_data.get("report_id")
        if not new_report_id:
            logger.error("Failed to create a new report. Aborting pipeline.")
            return
        logger.info(f"New report created with ID: {new_report_id}")
        logger.info("Running comparisons using compare_objects.")
        comparisons = compare_objects(openscap_rules, detail_items, suggestion_items)
        logger.info("Comparisons computed.")
        logger.info("Storing generated comparison results into the database.")
        store_generated_report(session, new_report_id, comparisons)
        logger.info("Generated comparison results stored successfully.")

        logger.info("Generating PDF Audit Report.")
        generate_audit_report_pdf(session, new_report_id, str(pdf_path))
        logger.info(f"PDF Audit Report generated at: {pdf_path}")

    except Exception as e:
        logger.exception(f"An error occurred during the full pipeline: {e}")
    finally:
        session.close()
        logger.info("Session closed. Program finished.")


if __name__ == "__main__":
    pdf_file_path = GENERATED_DIR / "Audit_Report.pdf"
    run_full_pipeline(pdf_file_path)
