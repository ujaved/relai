import streamlit as st
from streamlit_url_fragment import get_fragment
from store import DBClient
import jwt
from gotrue.errors import AuthApiError
from audiorecorder import audiorecorder
import assemblyai as aai
import webvtt
from streamlit_option_menu import option_menu
import altair as alt
from recording_processor import RecordingProcessor
from chatbot import OpenAIChatbot, ModeAnalysis
from collections import defaultdict
import pandas as pd

aai.settings.api_key = st.secrets["ASSEMBLYAI_API_KEY"]


# Initialize connection.
def init_connection() -> None:
    if "db_client" not in st.session_state:
        st.session_state["db_client"] = DBClient(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        )
    if "transcriber" not in st.session_state:
        st.session_state["transcriber"] = aai.Transcriber(
            config=aai.TranscriptionConfig(speaker_labels=True)
        )


def login_submit(is_login: bool, invite_partner: bool = False):
    if is_login:
        if not st.session_state.login_email or not st.session_state.login_password:
            st.error("Please provide login information")
            return
        try:
            st.session_state["user"] = st.session_state.db_client.sign_in(
                st.session_state.login_email, st.session_state.login_password
            )
            st.session_state["authenticated"] = True
        except AuthApiError as e:
            st.error(e)
        return

    try:
        if (
            not st.session_state.register_email
            or not st.session_state.register_first_name
            or not st.session_state.register_last_name
        ):
            st.error("Please provide all requested information")
            return
        user = st.session_state.db_client.invite_user_by_email(
            st.session_state.register_email,
            st.session_state.register_first_name,
            st.session_state.register_last_name,
        )
        st.info(f"An email invite has been sent to {st.session_state.register_email}")
        if invite_partner:
            st.session_state.db_client.insert_couple(
                user_id=st.session_state.user.id, partner_id=user.id
            )
    except AuthApiError as e:
        st.error(e)


def reset_password_submit(user_id: str):
    if (
        not st.session_state.reset_password_password
        or not st.session_state.reset_password_confirm_password
    ):
        st.error("Please enter password and confirm password")
        return
    if (
        st.session_state.reset_password_password
        != st.session_state.reset_password_confirm_password
    ):
        st.error("Passwords don't match")
        return
    try:
        st.session_state["user"] = st.session_state.db_client.update_user_password(
            user_id, st.session_state.reset_password_password
        )
        st.session_state["authenticated"] = True
    except AuthApiError as e:
        st.error(e)


def reset_password(email: str, user_id: str):
    with st.form("login_form", clear_on_submit=True):
        st.text_input("Email", key="reset_password_email", value=email, disabled=True)
        st.text_input("Password", type="password", key="reset_password_password")
        st.text_input(
            "Confirm Password", type="password", key="reset_password_confirm_password"
        )
        st.form_submit_button("Submit", on_click=reset_password_submit, args=(user_id,))


def register_login():
    login_tab, register_tab = st.tabs(["Login", "Sign up"])
    with login_tab:
        with st.form("login_form", clear_on_submit=True):
            st.text_input("Email", key="login_email")
            st.text_input("Password", type="password", key="login_password")
            st.form_submit_button("Submit", on_click=login_submit, args=[True])

    with register_tab:
        with st.form("register", clear_on_submit=True):
            st.text_input("Email", key="register_email")
            st.text_input("First name", key="register_first_name")
            st.text_input("Last name", key="register_last_name")
            st.form_submit_button("Submit", on_click=login_submit, args=[False])


@st.fragment(run_every=1)
def check_partner_status():
    if st.session_state.get("couple_id"):
        return
    record = st.session_state.db_client.get_couple(st.session_state.user.id)
    if not record:
        st.info(
            "You haven't invited your partner yet. Please invite your partner by submitting their information."
        )
        with st.form("register", clear_on_submit=True):
            st.text_input("Email", key="register_email")
            st.text_input("First name", key="register_first_name")
            st.text_input("Last name", key="register_last_name")
            st.form_submit_button("Submit", on_click=login_submit, args=(False, True))
    else:
        partner_id = record["partner_id"]
        if st.session_state.user.id == partner_id:
            partner_id = record["user_id"]
        partner = DBClient(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        ).get_user(partner_id)
        st.session_state["partner"] = partner
        if not partner.confirmed_at:
            st.error("Your partner has not yet accepted the invitation to sign up.")
        else:
            st.session_state["couple_id"] = record["id"]
            st.rerun()


def process_vtt(transcript_vtt: str, utterances: list) -> str:
    cur_utterance_idx = 0
    captions = webvtt.from_string(transcript_vtt)
    for caption in captions:
        if caption.text in utterances[cur_utterance_idx].text:
            caption.text = utterances[cur_utterance_idx].speaker + ": " + caption.text
        else:
            cur_utterance_idx += 1
    return captions.content


def create_recording():
    audio = st.audio_input("Record a conversation")
    if audio:
        with st.spinner("Transcribing audio"):
            transcript = st.session_state.transcriber.transcribe(audio)
        vtt = process_vtt(transcript.export_subtitles_vtt(), transcript.utterances)
        st.session_state.db_client.insert_recording(
            couple_id=st.session_state.couple_id,
            transcript=vtt,
        )


def mode_analysis():
    num_intervals = 0
    mode_counts = defaultdict(lambda: defaultdict(int))
    mode_analysis_by_ts = {}
    for rp in st.session_state.rps:
        print(rp.id)
        mode_analysis_json = st.session_state.db_client.get_mode_analysis(rp.id)
        if mode_analysis_json:
            mode_analysis = ModeAnalysis(**mode_analysis_json)
        else:
            mode_analysis = rp.get_mode_analysis(1)
            mode_analysis_json = mode_analysis.model_dump()
            st.session_state.db_client.insert_mode_analysis(rp.id, mode_analysis_json)
        num_intervals += len(mode_analysis.modes)
        for m in mode_analysis.modes:
            mode_counts[rp.ts][m.label.value] += 1
        mode_analysis_by_ts[rp.ts] = mode_analysis_json

        # modes.sort(key=lambda m: m[1].label)
        # to_label = [random.choice(list(v)) for _, v in groupby(modes, lambda m: m[1].label)]

    mode_data = [
        {
            "timestamp": ts,
            "mode": m,
            "count": c,
            "num_intervals": len(mode_analysis_by_ts[ts]["modes"]),
            "tot_num_intervals": num_intervals,
        }
        for ts, mc in mode_counts.items()
        for m, c in mc.items()
    ]
    mode_data_df = pd.DataFrame(mode_data)
    chart = (
        alt.Chart(
            mode_data_df.groupby(["mode", "tot_num_intervals"])
            .sum("count")
            .reset_index()
        )
        .transform_calculate(percent="datum.count*100/datum.tot_num_intervals")
        .mark_bar()
        .encode(
            x=alt.X(
                "mode:O",
                sort=alt.EncodingSortField(field="percent", order="descending"),
            ),
            y="percent:Q",
            color=alt.Color("mode", scale=alt.Scale(scheme="dark2")),
        )
    )
    st.subheader("Aggregate Modes", divider=True)
    st.altair_chart(chart, use_container_width=True)

    chart = (
        alt.Chart(mode_data_df)
        .mark_bar()
        .encode(
            x=alt.X("count:Q").stack("normalize").title(None),
            y="timestamp:O",
            color=alt.Color("mode", scale=alt.Scale(scheme="dark2")),
            order=alt.Order("count:Q", sort="descending"),
        )
        .add_params(alt.selection_point())
    )
    st.subheader("Modes for each recording", divider=True)
    st.altair_chart(chart, use_container_width=True)


def dashboard():
    with st.sidebar:
        dashboard_option = option_menu(
            "",
            [
                "Mode Analysis",
            ],
            icons=[
                "emoji-heart-eyes",
            ],
        )

    recordings = st.session_state.db_client.get_recordings(st.session_state.couple_id)
    st.session_state["rps"] = [
        RecordingProcessor(
            id=rec["id"],
            ts=rec["created_at"],
            transcript=rec["transcript"],
            chatbot=OpenAIChatbot(model_id="gpt-4o-2024-08-06", temperature=0.0),
            db_client=st.session_state.db_client,
        )
        for rec in recordings
    ]

    match dashboard_option:
        case "Mode Analysis":
            mode_analysis()


def main():

    st.set_page_config(
        page_title="Relait", page_icon=":partner_exchange:", layout="wide"
    )
    init_connection()

    if st.session_state.get("authenticated"):
        st.info(
            f"Welcome {st.session_state.user.user_metadata["first_name"]} {st.session_state.user.user_metadata["last_name"]}!"
        )
        check_partner_status()
        if st.session_state.get("couple_id"):
            st.info(
                f"Your partner is {st.session_state.partner.user_metadata["first_name"]} {st.session_state.partner.user_metadata["last_name"]}"
            )
            pg = st.navigation(
                [
                    st.Page(
                        create_recording,
                        title="Create Recording",
                        icon=":material/mic:",
                        default=True,
                    ),
                    st.Page(
                        dashboard,
                        title="Dashboard",
                        icon=":material/dashboard:",
                    ),
                ]
            )
            pg.run()

    elif "reset_password" in st.query_params:
        fragment = get_fragment()
        if fragment:
            acces_token = (fragment.split("access_token=")[1]).split("&")[0]
            payload = jwt.decode(acces_token, options={"verify_signature": False})
            reset_password(payload["email"], payload["sub"])
    else:
        register_login()


if __name__ == "__main__":
    main()
