import streamlit as st
from streamlit_url_fragment import get_fragment
from store import DBClient
import jwt
from gotrue.errors import AuthApiError
import time


# Initialize connection.
# @st.cache_resource
def init_connection() -> None:
    if "db_client" not in st.session_state:
        st.session_state["db_client"] = DBClient(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
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
            st.session_state.db_client.upsert_partner(
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
        record = st.session_state.db_client.get_partner(st.session_state.user.id)
        if not record:
            st.session_state.db_client.upsert_partner(user_id=st.session_state.user.id)
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
    record = st.session_state.db_client.get_partner(st.session_state.user.id)
    if not record["partner_id"]:
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
            partner_id = record["id"]
        partner = st.session_state.db_client.get_user(partner_id)
        if not partner.confirmed_at:
            st.error("Your partner has not yet accepted the invitation to sign up.")
        else:
            st.info(
                f"Your partner {partner.user_metadata["first_name"]} {partner.user_metadata["last_name"]} has also signed up!!"
            )


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
