import json
import hashlib
from datetime import datetime
from typing import Optional, List
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from src.schemas import ScoutReport
from src.logging_config import get_logger

logger = get_logger("database")


class Database:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def save_report(self, report: ScoutReport):
        """Saves a ScoutReport to the 'reports' table."""
        try:
            # We dump the Pydantic model to JSON
            # Note: You need to create a 'reports' table in Supabase with a 'data' jsonb column
            data = json.loads(report.model_dump_json())

            payload = {
                "id": report.report_id, # Assuming uuid or string primary key
                "type": "scout",
                "created_at": datetime.now().isoformat(),
                "data": data
            }

            # Upsert logic (requires id to be primary key)
            response = self.supabase.table("reports").upsert(payload).execute()
            return response
        except Exception as e:
            logger.error("Error saving report to Supabase", error=str(e))
            raise e

    # =========================================================================
    # Meeting State Tracking (for Hybrid Scraping Pipeline)
    # =========================================================================

    def get_meeting(self, meeting_id: str, source_id: str) -> Optional[dict]:
        """Get a meeting by ID and source."""
        try:
            response = self.supabase.table("scraped_meetings").select("*").eq(
                "meeting_id", meeting_id
            ).eq("source_id", source_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error("Error fetching meeting", meeting_id=meeting_id, error=str(e))
            return None

    def get_meetings_by_source(
        self,
        source_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[dict]:
        """Get all meetings for a source, optionally filtered by date range."""
        try:
            query = self.supabase.table("scraped_meetings").select("*").eq(
                "source_id", source_id
            )

            if since:
                query = query.gte("meeting_date", since.isoformat())
            if until:
                query = query.lte("meeting_date", until.isoformat())

            response = query.order("meeting_date", desc=True).execute()
            return response.data or []
        except Exception as e:
            logger.error("Error fetching meetings", source_id=source_id, error=str(e))
            return []

    def upsert_meeting(self, meeting_data: dict) -> bool:
        """
        Insert or update a meeting record.

        Required fields in meeting_data:
        - meeting_id: str (unique ID from source)
        - source_id: str (e.g., 'alachua-civicclerk')
        - title: str
        - meeting_date: datetime or ISO string

        Optional fields:
        - board: str
        - agenda_posted_date: datetime or ISO string
        - agenda_packet_url: str
        - content_hash: str
        - pdf_content: str (extracted text)
        - metadata: dict
        """
        try:
            # Ensure datetime fields are ISO strings
            if isinstance(meeting_data.get('meeting_date'), datetime):
                meeting_data['meeting_date'] = meeting_data['meeting_date'].isoformat()
            if isinstance(meeting_data.get('agenda_posted_date'), datetime):
                meeting_data['agenda_posted_date'] = meeting_data['agenda_posted_date'].isoformat()

            # Add timestamps
            meeting_data['last_scraped_at'] = datetime.now().isoformat()

            response = self.supabase.table("scraped_meetings").upsert(
                meeting_data,
                on_conflict="meeting_id,source_id"
            ).execute()

            logger.debug(
                "Upserted meeting",
                meeting_id=meeting_data.get('meeting_id'),
                source_id=meeting_data.get('source_id')
            )
            return True
        except Exception as e:
            logger.error("Error upserting meeting", error=str(e), data=meeting_data)
            return False

    def mark_meeting_analyzed(self, meeting_id: str, source_id: str, report_id: str) -> bool:
        """Mark a meeting as analyzed with the associated report ID."""
        try:
            response = self.supabase.table("scraped_meetings").update({
                "last_analyzed_at": datetime.now().isoformat(),
                "report_id": report_id
            }).eq("meeting_id", meeting_id).eq("source_id", source_id).execute()
            return True
        except Exception as e:
            logger.error("Error marking meeting analyzed", meeting_id=meeting_id, error=str(e))
            return False

    def get_unanalyzed_meetings(self, source_id: str, with_agenda_only: bool = True) -> List[dict]:
        """Get meetings that haven't been analyzed yet."""
        try:
            query = self.supabase.table("scraped_meetings").select("*").eq(
                "source_id", source_id
            ).is_("last_analyzed_at", "null")

            if with_agenda_only:
                query = query.not_.is_("agenda_posted_date", "null")

            response = query.order("meeting_date", desc=False).execute()
            return response.data or []
        except Exception as e:
            logger.error("Error fetching unanalyzed meetings", source_id=source_id, error=str(e))
            return []

    def meeting_content_changed(self, meeting_id: str, source_id: str, new_content: str) -> bool:
        """Check if meeting content has changed by comparing content hashes."""
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        existing = self.get_meeting(meeting_id, source_id)
        if not existing:
            return True  # New meeting, treat as changed

        old_hash = existing.get('content_hash')
        return old_hash != new_hash

    def compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    # =========================================================================
    # Document Storage (for extracted PDF content)
    # =========================================================================

    def save_document(self, document_data: dict) -> bool:
        """
        Save an extracted document (PDF content).

        Required fields:
        - document_id: str
        - source_id: str
        - meeting_id: str (links to scraped_meetings)
        - content: str (extracted text)
        - content_hash: str

        Optional:
        - title: str
        - document_type: str (agenda, agenda_packet, minutes, etc.)
        - url: str
        - metadata: dict
        """
        try:
            document_data['created_at'] = datetime.now().isoformat()

            response = self.supabase.table("documents").upsert(
                document_data,
                on_conflict="document_id"
            ).execute()

            logger.debug("Saved document", document_id=document_data.get('document_id'))
            return True
        except Exception as e:
            logger.error("Error saving document", error=str(e))
            return False

    def get_document(self, document_id: str) -> Optional[dict]:
        """Get a document by ID."""
        try:
            response = self.supabase.table("documents").select("*").eq(
                "document_id", document_id
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error("Error fetching document", document_id=document_id, error=str(e))
            return None

    # =========================================================================
    # Deep Research Reports (Layer 2 Analysis)
    # =========================================================================

    def get_high_relevance_reports(
        self,
        source_id: str,
        min_relevance: float = 0.7,
        needs_deep_research: bool = True
    ) -> List[dict]:
        """
        Get reports with high relevance scores that may need deep research.

        Args:
            source_id: Source ID to filter by
            min_relevance: Minimum relevance score (0.0-1.0)
            needs_deep_research: If True, only return reports without deep research

        Returns:
            List of report dicts
        """
        try:
            query = self.supabase.table("reports").select("*").eq("type", "scout")

            # Filter by relevance in the JSON data
            # Note: This assumes reports have data->relevance_score field
            response = query.order("created_at", desc=True).limit(50).execute()

            results = []
            for report in response.data or []:
                data = report.get('data', {})
                relevance = data.get('relevance_score', 0)

                # Check relevance threshold
                if relevance < min_relevance:
                    continue

                # Check if deep research already done
                if needs_deep_research and report.get('deep_research_id'):
                    continue

                results.append(report)

            return results
        except Exception as e:
            logger.error("Error fetching high relevance reports", source_id=source_id, error=str(e))
            return []

    def save_deep_research_report(self, original_report_id: str, deep_report: "ScoutReport") -> bool:
        """
        Save a deep research report and link it to the original Scout report.

        Args:
            original_report_id: ID of the original Scout report
            deep_report: The deep research ScoutReport

        Returns:
            True if successful
        """
        try:
            import json

            # Save the deep research report
            data = json.loads(deep_report.model_dump_json())
            deep_report_id = f"deep-{deep_report.report_id}"

            payload = {
                "id": deep_report_id,
                "type": "deep_research",
                "created_at": datetime.now().isoformat(),
                "data": data,
                "original_report_id": original_report_id
            }

            self.supabase.table("reports").upsert(payload).execute()

            # Link the original report to this deep research
            self.supabase.table("reports").update({
                "deep_research_id": deep_report_id
            }).eq("id", original_report_id).execute()

            logger.info(
                "Saved deep research report",
                deep_report_id=deep_report_id,
                original_report_id=original_report_id
            )
            return True
        except Exception as e:
            logger.error(
                "Error saving deep research report",
                original_report_id=original_report_id,
                error=str(e)
            )
            return False

_db: Database | None = None

def get_db() -> Database:
    """Lazy initialization of Database singleton.

    Returns:
        Database: The database instance.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    global _db
    if _db is None:
        _db = Database()
    return _db
