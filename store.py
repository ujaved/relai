from supabase import create_client, Client
from datetime import date


class DBClient:
    def __init__(self, supabase_url: str, supabase_key: str) -> Client:
        self.client = create_client(supabase_url, supabase_key)

    def sign_in(self, email: str, password: str):
        return self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        ).user

    def get_user(self, user_id: str):
        return self.client.auth.admin.get_user_by_id(user_id).user

    def update_user_password(self, user_id: str, password: str):
        return self.client.auth.admin.update_user_by_id(
            user_id, {"password": password}
        ).user

    def invite_user_by_email(self, email: str, first_name: str, last_name: str):
        return self.client.auth.admin.invite_user_by_email(
            email,
            options={
                "data": {
                    "first_name": first_name,
                    "last_name": last_name,
                }
            },
        ).user

    def upsert_partner(self, user_id: str, partner_id: str | None = None) -> None:
        self.client.table("partner").upsert(
            {"id": user_id, "partner_id": partner_id}
        ).execute()

    def get_partner_id(self, user_id: str) -> str | None:
        return (
            self.client.table("partner")
            .select("partner_id")
            .eq("id", user_id)
            .limit(1)
            .single()
            .execute()
        ).data["partner_id"]

    def get_mode_analysis(self, recording_id: str, interval: int) -> dict | None:
        mode_analysis = (
            self.client.table("mode_analysis")
            .select("mode_analysis")
            .eq("recording_id", recording_id)
            .eq("interval", interval)
            .maybe_single()
            .execute()
        )
        if mode_analysis:
            return mode_analysis.data["mode_analysis"]
        return None

    def insert_mode_analysis(
        self, recording_id: str, interval: int, json: dict
    ) -> None:
        self.client.table("mode_analysis").insert(
            {
                "recording_id": recording_id,
                "interval": interval,
                "mode_analysis": json,
            }
        ).execute()

    def get_emotion_analysis(self, recording_id: str, interval: int) -> dict | None:
        emotion_analysis = (
            self.client.table("emotion_analysis")
            .select("emotion_analysis")
            .eq("recording_id", recording_id)
            .eq("interval", interval)
            .maybe_single()
            .execute()
        )
        if emotion_analysis:
            return emotion_analysis.data["emotion_analysis"]
        return None

    def insert_emotion_analysis(
        self, recording_id: str, interval: int, json: dict
    ) -> None:
        self.client.table("emotion_analysis").insert(
            {
                "recording_id": recording_id,
                "interval": interval,
                "emotion_analysis": json,
            }
        ).execute()

    def get_recording_stats(self, recordind_ids: list[str]) -> list[dict]:
        return (
            self.client.table("recording_stats")
            .select("*")
            .in_("recording_id", recordind_ids)
            .execute()
            .data
        )

    def get_recordings(self, teacher_id: str, class_id: str) -> list[dict]:
        return (
            self.client.table("recordings")
            .select("*")
            .eq("user_id", teacher_id)
            .eq("class_id", class_id)
            .execute()
            .data
        )

    def get_classes(self, teacher_id: str) -> list[dict]:
        return (
            self.client.table("classes")
            .select("*")
            .eq("teacher_id", teacher_id)
            .execute()
            .data
        )

    def get_speakers(self, class_id: str) -> dict:
        return (
            self.client.table("speakers")
            .select("*")
            .eq("class_id", class_id)
            .execute()
            .data
        )

    def insert_speaker(
        self,
        class_id: str,
        name: str,
        image_s3_key: str | None = None,
        alt_names: list[str] | None = None,
    ) -> None:
        self.client.table("speakers").insert(
            {
                "class_id": class_id,
                "name": name,
                "s3_key": image_s3_key,
                "alt_names": alt_names,
            }
        ).execute()

    def update_speaker(
        self,
        class_id: str,
        name: str,
        alt_names: list[str],
    ) -> None:
        self.client.table("speakers").update({"alt_names": alt_names}).eq(
            "class_id", class_id
        ).eq("name", name).execute()

    def get_orgs(self) -> dict:
        return self.client.table("organizations").select("*").execute().data

    def insert_org(self, name: str) -> None:
        self.client.table("organizations").insert({"name": name}).execute()

    def insert_recording(
        self, user_id: str, link: str, date: date, class_id: str
    ) -> None:
        self.client.table("recordings").insert(
            {
                "user_id": user_id,
                "link": link,
                "date": date.isoformat(),
                "class_id": class_id,
            }
        ).execute()

    def insert_class(self, name: str, teacher_id: str, org_id: str) -> None:
        self.client.table("classes").insert(
            {
                "name": name,
                "teacher_id": teacher_id,
                "org_id": org_id,
            }
        ).execute()
