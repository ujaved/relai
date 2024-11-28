from supabase import create_client, Client


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

    def insert_couple(self, user_id: str, partner_id: str | None = None) -> None:
        self.client.table("couple").insert(
            {"user_id": user_id, "partner_id": partner_id}
        ).execute()

    def get_couple(self, user_id: str) -> dict | None:
        by_user_id = (
            self.client.table("couple")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if by_user_id:
            return by_user_id.data
        by_partner_id = (
            self.client.table("couple")
            .select("*")
            .eq("partner_id", user_id)
            .maybe_single()
            .execute()
        )
        if by_partner_id:
            return by_partner_id.data
        return None

    def get_mode_analysis(self, recording_id: str) -> dict | None:
        mode_analysis = (
            self.client.table("mode_analysis")
            .select("*")
            .eq("recording_id", recording_id)
            .maybe_single()
            .execute()
        )
        if mode_analysis:
            return mode_analysis.data["modes"]
        return None

    def insert_mode_analysis(self, recording_id: str, json: dict) -> None:
        self.client.table("mode_analysis").insert(
            {
                "recording_id": recording_id,
                "modes": json,
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

    def get_recordings(self, couple_id: str) -> list[dict]:
        return (
            self.client.table("recording")
            .select("*")
            .eq("couple_id", couple_id)
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

    def insert_recording(self, couple_id: str, transcript: str) -> None:
        self.client.table("recording").insert(
            {
                "couple_id": couple_id,
                "transcript": transcript,
            }
        ).execute()
