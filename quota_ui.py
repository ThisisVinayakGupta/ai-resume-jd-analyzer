"""Quota configuration, browser trial identity, and model-call admission."""

import json

import streamlit as st

from monthly_quota import (
    FirestoreStore, MonthlyQuota, QuotaUnavailable, QuotaExhausted,
    guest_actor, mint_guest_token, user_actor,
)


_browser_storage = st.components.v2.component("resume_trial_identity", js="""
export default function(component) {
    const {data, setStateValue} = component;
    try {
        const key = "resumematch_pro_guest_v1";
        let token = localStorage.getItem(key);
        if (!token) {
            token = data.candidate;
            localStorage.setItem(key, token);
        }
        setStateValue("token", token);
    } catch (_) {
        setStateValue("token", "storage-unavailable");
    }
}
""")


def guest_secret():
    try:
        secret = st.secrets["quota"]["guest_secret"]
        # Validate with the same rules used for submitted browser tokens.
        mint_guest_token(secret)
        return secret
    except (FileNotFoundError, KeyError, TypeError, QuotaUnavailable) as error:
        raise QuotaUnavailable("Browser trial unavailable") from error


def browser_trial_actor():
    secret = guest_secret()
    if "_guest_candidate" not in st.session_state:
        st.session_state["_guest_candidate"] = mint_guest_token(secret)
    result = _browser_storage(data={"candidate": st.session_state["_guest_candidate"]},
                              on_token_change=lambda: None, key="guest_browser_storage")
    if not result.token:
        return None
    actor = guest_actor(result.token, secret)
    st.session_state["_guest_verified_token"] = result.token
    return actor


@st.cache_resource
def get_quota_service():
    try:
        from google.cloud import firestore
        from google.oauth2 import service_account
        settings = st.secrets["firestore"]
        info = json.loads(settings["service_account_json"])
        credentials = service_account.Credentials.from_service_account_info(info)
        client = firestore.Client(project=info["project_id"], credentials=credentials)
        return MonthlyQuota(FirestoreStore(client, firestore))
    except Exception as error:
        raise QuotaUnavailable("Usage service unavailable") from error


def workspace_allowance(identity):
    actor = user_actor(identity) if identity else browser_trial_actor()
    if actor is None:
        return None
    return get_quota_service().status(actor)


def available_credits():
    allowance = st.session_state.get("_quota_allowance")
    return allowance.remaining if allowance else 0


def reserve_credit():
    # Re-derive the authenticated identity at the model boundary. Browser/session
    # fields never decide whether a user is paid or how large their limit is.
    from launch_ui import auth_is_configured, current_identity
    identity = current_identity() if auth_is_configured() else None
    if identity:
        actor = user_actor(identity)
    else:
        actor = guest_actor(st.session_state.get("_guest_verified_token"), guest_secret())
    return get_quota_service().reserve(actor)


def finish_credit(reservation, success):
    get_quota_service().finish(reservation, success)
