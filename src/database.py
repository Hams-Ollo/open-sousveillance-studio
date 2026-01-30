import json
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from src.schemas import ScoutReport

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
                "created_at": report.date_generated.isoformat(),
                "data": data
            }
            
            # Upsert logic (requires id to be primary key)
            response = self.supabase.table("reports").upsert(payload).execute()
            return response
        except Exception as e:
            print(f"Error saving report to Supabase: {e}")
            raise e

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
