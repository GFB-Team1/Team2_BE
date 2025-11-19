from supabase import create_client, Client
from config import settings


# Supabase 클라이언트 생성
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key
)
