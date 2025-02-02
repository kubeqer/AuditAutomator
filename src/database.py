from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    create_engine,
    Index,
    Text,
    Float,
    Boolean,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    sessionmaker,
    Session,
    selectinload,
)
from datetime import datetime
from loguru import logger
from consts import DATABASE_URL
from typing import Optional, Dict, List, Any
from models import OpenSCAPRule, DetailItemLynis, SuggestionItemLynis

Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique primary key for the Report record.",
    )
    date = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
        doc="Timestamp indicating when the report was created.",
    )

    openscap_items = relationship(
        "OpenSCAP", back_populates="report", cascade="all, delete-orphan"
    )
    lynis_items = relationship(
        "Lynis", back_populates="report", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Report(id={self.id}, date={self.date})>"


class OpenSCAP(Base):
    __tablename__ = "openscap"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique primary key for the OpenSCAP record.",
    )
    report_id = Column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key linking to the parent Report.",
    )
    title = Column(String, nullable=False, doc="Title of the rule/finding.")
    severity = Column(String, nullable=True, doc="Severity classification.")
    description = Column(
        Text, nullable=True, doc="Longer description of the rule/finding."
    )
    rationale = Column(
        Text, nullable=True, doc="Explanation of why this rule/finding matters."
    )
    result = Column(String, nullable=True, doc="Scan outcome (e.g., 'pass', 'fail').")

    report = relationship("Report", back_populates="openscap_items")

    __table_args__ = (
        Index("idx_openscap_severity", severity),
        Index("idx_openscap_result", result),
    )

    def __repr__(self):
        return f"<OpenSCAP(id={self.id}, title={self.title}, severity={self.severity})>"


class LynisTypes(Base):
    __tablename__ = "lynistypes"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique primary key for the LynisTypes record.",
    )
    name = Column(
        String,
        nullable=False,
        doc="Name of the Lynis category (e.g., 'details', 'suggestions').",
    )

    lynis_entries = relationship(
        "Lynis", back_populates="lynistype", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<LynisTypes(id={self.id}, name={self.name})>"


class Lynis(Base):
    __tablename__ = "lynis"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique primary key for the Lynis record.",
    )
    lynistype_id = Column(
        Integer,
        ForeignKey("lynistypes.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to LynisTypes.",
    )
    report_id = Column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key linking this item to the parent Report.",
    )
    lynis_json_id = Column(
        String, nullable=True, doc="The original JSON ID from the Pydantic model."
    )
    service = Column(String, nullable=True, doc="Service name (for detail items).")
    severity = Column(String, nullable=True, doc="Severity (for suggestion items).")
    long_description = Column(
        Text, nullable=True, doc="Long textual description (for suggestion items)."
    )
    desc = Column(
        Text, nullable=True, doc="Short textual info (from nested DescriptionLynis)."
    )
    value = Column(String, nullable=True, doc="Value from DescriptionLynis.")
    prefval = Column(
        String, nullable=True, doc="Preferred/expected value from DescriptionLynis."
    )
    field = Column(
        String, nullable=True, doc="Configuration field from DescriptionLynis."
    )

    lynistype = relationship("LynisTypes", back_populates="lynis_entries")
    report = relationship("Report", back_populates="lynis_items")

    __table_args__ = (
        Index("idx_lynis_service", service),
        Index("idx_lynis_severity", severity),
        Index("idx_lynis_json_id", lynis_json_id),
    )

    def __repr__(self):
        return f"<Lynis(id={self.id}, lynis_json_id={self.lynis_json_id}, report_id={self.report_id})>"


class GeneratedReport(Base):
    """
    The 'generated_report' table stores the results from the comparison pipeline.

    For each comparison category:
      - If a verified pair is available (cosine similarity > 0.5), both object A and object B database IDs are stored.
      - Otherwise, only object A's ID is stored.
    """

    __tablename__ = "generated_report"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique primary key for the GeneratedReport record.",
    )
    report_id = Column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key linking to the parent Report.",
    )
    object_a_type = Column(
        String,
        nullable=False,
        doc="Type of object A (e.g., 'openscap', 'detail', 'suggestion').",
    )
    object_a_id = Column(Integer, nullable=False, doc="Database ID of object A.")
    object_b_type = Column(
        String, nullable=True, doc="Type of object B (if a pair is formed)."
    )
    object_b_id = Column(
        Integer, nullable=True, doc="Database ID of object B (if a pair is formed)."
    )
    similarity_score = Column(
        Float, nullable=True, doc="Computed similarity score (if paired)."
    )
    verified = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if the pair is verified (cosine similarity > 0.5); False otherwise.",
    )

    def __repr__(self):
        return (
            f"<GeneratedReport(id={self.id}, report_id={self.report_id}, "
            f"object_a_id={self.object_a_id}, object_b_id={self.object_b_id}, verified={self.verified})>"
        )


def get_db_id_for_openscap(session: Session, rule: OpenSCAPRule) -> Optional[int]:
    """
    Retrieves the database ID for an OpenSCAP record by matching its title.
    Assumes that the title is unique.
    """
    db_rule = session.query(OpenSCAP).filter(OpenSCAP.title == rule.title).first()
    return db_rule.id if db_rule else None


def get_db_id_for_lynis(session: Session, obj: Any) -> Optional[int]:
    """
    Retrieves the database ID for a Lynis record by using the external ID from the Pydantic object.
    The Pydantic object is expected to have its 'id' attribute (from the JSON) which was stored in the database
    as lynis_json_id.
    """
    external_id = getattr(obj, "id", None)
    if external_id:
        db_obj = session.query(Lynis).filter(Lynis.lynis_json_id == external_id).first()
        return db_obj.id if db_obj else None
    return None


def init_database(echo: bool = True):
    """
    Initializes the database schema (creates all tables if they don't exist)
    and inserts two default LynisTypes ('details' and 'suggestions').
    """
    logger.info(f"Initializing database with URL={DATABASE_URL}, echo={echo}")
    engine = create_engine(DATABASE_URL, echo=echo)
    logger.debug("Creating all tables (if they don't exist).")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        logger.debug("Checking existing LynisTypes entries.")
        existing_count = session.query(LynisTypes).count()
        if existing_count == 0:
            logger.info(
                "No LynisTypes entries found. Inserting defaults: 'details' and 'suggestions'."
            )
            details_type = LynisTypes(name="details")
            suggestions_type = LynisTypes(name="suggestions")
            session.add_all([details_type, suggestions_type])
            session.commit()
            logger.info("Inserted 'details' and 'suggestions' into LynisTypes.")
        else:
            logger.info(
                f"LynisTypes already has {existing_count} entries. Skipping insert."
            )
        logger.info("Database schema is up-to-date. Initialization complete.")


def get_report(session: Session, report_id: int) -> Optional[Dict]:
    """
    Retrieves all information about a single report, including associated OpenSCAP and Lynis items.
    """
    report = (
        session.query(Report)
        .options(
            selectinload(Report.openscap_items),
            selectinload(Report.lynis_items).selectinload(Lynis.lynistype),
        )
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        return None
    report_data = {
        "report_id": report.id,
        "date": str(report.date),
        "openscap_items": [],
        "lynis_items": [],
    }
    for osc in report.openscap_items:
        report_data["openscap_items"].append(
            {
                "id": osc.id,
                "title": osc.title,
                "severity": osc.severity,
                "description": osc.description,
                "rationale": osc.rationale,
                "result": osc.result,
            }
        )
    for lyn in report.lynis_items:
        lynis_dict = {
            "id": lyn.id,
            "lynistype_id": lyn.lynistype_id,
            "lynis_json_id": lyn.lynis_json_id,
            "service": lyn.service,
            "severity": lyn.severity,
            "long_description": lyn.long_description,
            "desc": lyn.desc,
            "value": lyn.value,
            "prefval": lyn.prefval,
            "field": lyn.field,
        }
        if lyn.lynistype:
            lynis_dict["type_name"] = lyn.lynistype.name
        report_data["lynis_items"].append(lynis_dict)
    return report_data


def put_report(
    session: Session,
    openscap_rules: List[OpenSCAPRule],
    detail_items: List[DetailItemLynis],
    suggestion_items: List[SuggestionItemLynis],
) -> Dict[str, Any]:
    """
    Creates a new report, inserts OpenSCAP rules and Lynis items, and returns the report data.
    """
    logger.info("Creating a new Report.")
    new_report = Report()
    session.add(new_report)
    session.commit()
    logger.debug(f"New report created with ID={new_report.id}")

    logger.info(f"Inserting {len(openscap_rules)} OpenSCAP rules.")
    for rule in openscap_rules:
        osc = OpenSCAP(
            report_id=new_report.id,
            title=rule.title,
            severity=rule.severity,
            description=rule.description,
            rationale=rule.rationale,
            result=rule.result,
        )
        session.add(osc)

    details_type = session.query(LynisTypes).filter_by(name="details").one_or_none()
    if not details_type:
        raise ValueError("LynisTypes entry 'details' not found in database.")
    suggestions_type = (
        session.query(LynisTypes).filter_by(name="suggestions").one_or_none()
    )
    if not suggestions_type:
        raise ValueError("LynisTypes entry 'suggestions' not found in database.")

    logger.info(f"Inserting {len(detail_items)} Lynis detail items.")
    for detail in detail_items:
        desc_obj = detail.description.dict() if detail.description else {}
        lynis_detail = Lynis(
            report_id=new_report.id,
            lynistype_id=details_type.id,
            lynis_json_id=detail.id,
            service=detail.service,
            desc=desc_obj.get("desc"),
            value=desc_obj.get("value"),
            prefval=desc_obj.get("prefval"),
            field=desc_obj.get("field"),
        )
        session.add(lynis_detail)

    logger.info(f"Inserting {len(suggestion_items)} Lynis suggestion items.")
    for suggestion in suggestion_items:
        lynis_suggestion = Lynis(
            report_id=new_report.id,
            lynistype_id=suggestions_type.id,
            lynis_json_id=suggestion.id,
            severity=suggestion.severity,
            long_description=suggestion.description,
        )
        session.add(lynis_suggestion)

    session.commit()
    logger.debug("All items inserted and committed successfully.")

    logger.info("Fetching the newly created report with relations.")
    created_report = (
        session.query(Report)
        .options(selectinload(Report.openscap_items), selectinload(Report.lynis_items))
        .filter(Report.id == new_report.id)
        .one()
    )

    report_data = {
        "report_id": created_report.id,
        "date": str(created_report.date),
        "openscap_items": [],
        "lynis_items": [],
    }
    for osc in created_report.openscap_items:
        report_data["openscap_items"].append(
            {
                "id": osc.id,
                "title": osc.title,
                "severity": osc.severity,
                "description": osc.description,
                "rationale": osc.rationale,
                "result": osc.result,
            }
        )
    for lyn in created_report.lynis_items:
        lynis_dict = {
            "id": lyn.id,
            "lynistype_id": lyn.lynistype_id,
            "lynis_json_id": lyn.lynis_json_id,
            "service": lyn.service,
            "severity": lyn.severity,
            "long_description": lyn.long_description,
            "desc": lyn.desc,
            "value": lyn.value,
            "prefval": lyn.prefval,
            "field": lyn.field,
        }
        if lyn.lynistype:
            lynis_dict["type_name"] = lyn.lynistype.name
        report_data["lynis_items"].append(lynis_dict)

    logger.info(f"put_report completed for Report ID={created_report.id}")
    return report_data


def store_generated_report(
    session: Session, report_id: int, pipeline_results: Dict[str, Any]
) -> None:
    """
    Stores all generated comparisons into the GeneratedReport table.

    The pipeline_results dictionary is expected to have the following keys:
        - "pairs": list of tuples (oscap_rule, candidate, similarity, verified)
        - "unpaired_openscap": list of OpenSCAPRule objects with no verified pairing
        - "unpaired_detail": list of DetailItemLynis objects with no verified pairing
        - "unpaired_suggestion": list of SuggestionItemLynis objects with no verified pairing

    For each verified pair, both object A and object B database IDs are stored.
    For unverified pairs and unpaired objects, only object A's ID is stored.
    """
    pairs = pipeline_results.get("pairs", [])
    unpaired_osc = pipeline_results.get("unpaired_openscap", [])
    unpaired_det = pipeline_results.get("unpaired_detail", [])
    unpaired_sugg = pipeline_results.get("unpaired_suggestion", [])

    logger.debug(f"Pipeline results keys: {list(pipeline_results.keys())}")
    logger.debug(
        f"Found {len(pairs)} pairs, {len(unpaired_osc)} unpaired OpenSCAP, {len(unpaired_det)} unpaired Detail, and {len(unpaired_sugg)} unpaired Suggestion items."
    )

    for obj_a, obj_b, sim_score, verified in pairs:
        if verified:

            object_a_type = "openscap"
            object_b_type = (
                "suggestion"
                if hasattr(obj_b, "severity") and obj_b.severity is not None
                else "detail"
            )
            db_id_a = get_db_id_for_openscap(session, obj_a)
            db_id_b = get_db_id_for_lynis(session, obj_b)
            logger.debug(
                f"Storing verified pair: {db_id_a} ({object_a_type}) and {db_id_b} ({object_b_type}) with sim={sim_score:.3f}"
            )
            new_generated = GeneratedReport(
                report_id=report_id,
                object_a_type=object_a_type,
                object_a_id=db_id_a,
                object_b_type=object_b_type,
                object_b_id=db_id_b,
                similarity_score=sim_score,
                verified=True,
            )
            session.add(new_generated)
        else:
            object_a_type = "openscap"
            db_id_a = get_db_id_for_openscap(session, obj_a)
            logger.debug(
                f"Storing non-verified pair as unpaired: {db_id_a} ({object_a_type})"
            )
            new_generated = GeneratedReport(
                report_id=report_id,
                object_a_type=object_a_type,
                object_a_id=db_id_a,
                object_b_type=None,
                object_b_id=None,
                similarity_score=None,
                verified=False,
            )
            session.add(new_generated)
    for obj in unpaired_osc:
        db_id = get_db_id_for_openscap(session, obj)
        logger.debug(f"Storing unpaired OpenSCAP: {db_id}")
        new_generated = GeneratedReport(
            report_id=report_id,
            object_a_type="openscap",
            object_a_id=db_id,
            object_b_type=None,
            object_b_id=None,
            similarity_score=None,
            verified=False,
        )
        session.add(new_generated)
    for obj in unpaired_det:
        db_id = get_db_id_for_lynis(session, obj)
        logger.debug(f"Storing unpaired Detail: {db_id}")
        new_generated = GeneratedReport(
            report_id=report_id,
            object_a_type="detail",
            object_a_id=db_id,
            object_b_type=None,
            object_b_id=None,
            similarity_score=None,
            verified=False,
        )
        session.add(new_generated)
    for obj in unpaired_sugg:
        db_id = get_db_id_for_lynis(session, obj)
        logger.debug(f"Storing unpaired Suggestion: {db_id}")
        new_generated = GeneratedReport(
            report_id=report_id,
            object_a_type="suggestion",
            object_a_id=db_id,
            object_b_type=None,
            object_b_id=None,
            similarity_score=None,
            verified=False,
        )
        session.add(new_generated)

    session.commit()
    logger.info("All GeneratedReport records stored.")
