from chatbot import EmotionAnalysis, ModeAnalysis
from openai import OpenAI
from chatbot import Chatbot
from datetime import datetime
from store import DBClient


class RecordingProcessor:
    def __init__(
        self,
        id: str,
        ts: datetime,
        transcript: str,
        chatbot: Chatbot,
        db_client: DBClient,
    ) -> None:
        self.id = id
        self.ts = ts
        self.transcript = transcript
        self.chatbot = chatbot
        self.db_client = db_client
        self.duration_secs = 0

    @property
    def date(self) -> str:
        return self.ts.date().isoformat()

    def get_emotion_analysis(self, interval: int) -> EmotionAnalysis:
        prompt = f"Following is a transcript of a group discussion with timestamps. For every interval of {interval} minutes, perform emotion analysis, choosing emotion labels from the given list. \n\n {self.transcript}"
        messages = [{"role": "user", "content": prompt}]
        response = OpenAI().beta.chat.completions.parse(
            model=self.chatbot.model_id,
            messages=messages,
            response_format=EmotionAnalysis,
        )
        return response.choices[0].message.parsed

    def get_mode_analysis(self, interval: int) -> ModeAnalysis:
        prompt = f"Following is a transcript with timestamps of a conversation between a couple. For every interval of {interval} minutes, classify it as a mode, choosing mode labels from the given list. \n\n {self.transcript}"
        messages = [{"role": "user", "content": prompt}]
        response = OpenAI().beta.chat.completions.parse(
            model=self.chatbot.model_id,
            messages=messages,
            response_format=ModeAnalysis,
        )
        return response.choices[0].message.parsed
