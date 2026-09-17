"""Public website and native Google sign-in for the existing analyzer."""

from html import escape

import streamlit as st
from quota_ui import workspace_allowance
from monthly_quota import QuotaUnavailable


PAGES = ("Home", "Workspace", "Account", "Plans", "Help", "Privacy")
GOOGLE_METADATA = "https://accounts.google.com/.well-known/openid-configuration"


def auth_is_configured():
    """Incomplete credentials never enable access to the analyzer."""
    try:
        auth = st.secrets.get("auth", {})
        google = auth.get("google", {})
        values = (
            auth.get("redirect_uri"), auth.get("cookie_secret"),
            google.get("client_id"), google.get("client_secret"),
        )
        return (
            all(isinstance(value, str) and bool(value.strip())
                and not value.strip().startswith("REPLACE_") for value in values)
            and google.get("server_metadata_url") == GOOGLE_METADATA
        )
    except (FileNotFoundError, KeyError, TypeError, AttributeError):
        return False


def current_identity():
    """Trust Streamlit's verified OIDC identity, never a session-state flag."""
    user = st.user
    if not user.get("is_logged_in", False):
        return None
    subject = user.get("sub")
    email = user.get("email")
    if not subject or not email or user.get("email_verified") is not True:
        return None
    return {
        "owner": f"{user.get('iss', 'google')}|{subject}",
        "name": str(user.get("name") or "there"),
        "email": str(email),
    }


def bind_session(identity):
    """Discard previous analysis and upload widgets on an account change."""
    owner = identity["owner"] if identity else "guest"
    previous = st.session_state.get("_launch_owner")
    # Existing anonymous sessions from the earlier app must not survive sign-in.
    if previous != owner:
        st.session_state.clear()
        if identity:
            st.session_state["_launch_page"] = "Workspace"
    st.session_state["_launch_owner"] = owner


def go_to(page):
    if page in PAGES:
        st.session_state["_launch_page"] = page


def clear_workspace():
    owner = st.session_state.get("_launch_owner")
    st.session_state.clear()
    st.session_state["_launch_owner"] = owner
    st.session_state["_launch_page"] = "Workspace"


def logout():
    st.session_state.clear()
    st.logout()


def login():
    # Recheck configuration even if a stale browser event invokes this callback.
    if not auth_is_configured():
        st.session_state["_launch_login_error"] = True
        return
    try:
        st.login("google")
    except Exception:
        # Provider errors can contain credentials/URLs: never display raw errors.
        st.session_state["_launch_login_error"] = True


def _styles():
    st.markdown("""
    <style>
    .rm-hero {padding: 2rem 0 1.5rem; display:grid; grid-template-columns:1.2fr 1fr;
        align-items:center; gap:3rem;}
    .rm-eyebrow {color:#2457a7; font-size:.78rem; letter-spacing:.12em;
        font-weight:700; text-transform:uppercase;}
    .rm-hero h1 {font-size:clamp(2.3rem,4.5vw,3.8rem); line-height:1.15;
        letter-spacing:-.035em; color:#18324f; margin:.9rem 0 1.2rem; font-weight:550;}
    .rm-hero h1 span {color:#2457a7;}
    .rm-hero p {font-size:1.08rem; line-height:1.7; color:#526577; max-width:570px;}
    .rm-preview {background:#f5f8fc; border:1px solid #d6e0ec; border-radius:12px; padding:1.7rem;}
    .rm-preview-label {font-size:.7rem; letter-spacing:.12em; color:#526577; text-transform:uppercase;}
    .rm-preview-title {font-size:1.35rem; font-weight:650; color:#18324f; margin:.6rem 0 1rem;}
    .rm-preview-row {background:#fff; border:1px solid #e2e8f0; padding:.8rem 1rem;
        margin-top:.65rem; border-radius:7px; font-size:.94rem; color:#18324f;}
    .rm-preview-row small {display:block; color:#526577; margin-top:.2rem;}
    .rm-note {color:#526577; font-size:.9rem; padding:.8rem 0;}
    .rm-footer {border-top:1px solid #dde7e7; margin-top:2rem; padding-top:1rem;
        color:#64748b; font-size:.82rem;}
    .rm-greeting {color:#102a43; font-size:1.4rem; font-weight:600; margin:.5rem 0;}
    .rm-brand {font-size:1.1rem; font-weight:750; color:#18324f; padding:.4rem 0;}
    .rm-monogram {background:#2457a7; color:#fff; border-radius:5px; padding:.3rem;
        margin-right:.4rem; font-size:.88rem;}
    .rm-footer a {color:#2457a7; margin-left:1rem; text-decoration:none;}
    @media(max-width:800px) {.rm-hero {grid-template-columns:1fr; gap:1rem;} .rm-preview {display:none;}}
    @media(max-width:640px) {.rm-hero {padding-top:1rem;} .block-container {padding-top:1rem;}}
    </style>
    """, unsafe_allow_html=True)


def _home(identity):
    st.markdown("""
    <section class="rm-hero">
      <div>
      <div class="rm-eyebrow">Your next opportunity starts here</div>
      <h1>Make your next<br><span>application count.</span></h1>
      <p>Compare your resume with a job description. See the evidence behind
      your match, understand the gaps, and prepare for your interview.</p>
      </div>
      <aside class="rm-preview" aria-label="Sample report preview">
        <div class="rm-preview-label">Sample preview · not your analysis</div>
        <div class="rm-preview-title">Clear strengths. Honest gaps.</div>
        <div class="rm-preview-row">✓ SQL<small>Applied evidence · keep the example</small></div>
        <div class="rm-preview-row">→ Python<small>Proof gap · add a genuine example</small></div>
        <div class="rm-preview-row">→ Data visualization<small>Wording opportunity · check your dashboard work</small></div>
      </aside>
    </section>
    """, unsafe_allow_html=True)
    st.button("Open my workspace" if identity else "Get started",
              type="primary", on_click=go_to, args=("Workspace",), key="home_start")
    st.caption("3 guest analyses each month · Sign in for 10 monthly analyses · Text PDF upload")
    st.divider()
    st.subheader("A clearer view of your application")
    features = (
        ("Understand your match", "See skills, experience, tools, and responsibility alignment in one report."),
        ("Improve clarity", "Separate missing wording, weak evidence, and unsupported requirements."),
        ("Prepare with purpose", "Use tailored interview questions to explain your real experience."),
    )
    for column, (title, description) in zip(st.columns(3), features):
        with column:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(description)
    st.subheader("Three steps to a better-informed application")
    for column, (title, description) in zip(st.columns(3), (
        ("01 · Upload", "Choose a text-based PDF of your resume."),
        ("02 · Add the job", "Paste the complete target job description."),
        ("03 · Review", "Check your match and recommendations against your own experience."),
    )):
        with column:
            st.markdown(f"**{title}**")
            st.write(description)
    st.info("Improve how you present genuine experience. Never add skills or achievements you cannot support.")


def _sign_in(configured):
    st.title("Your next step starts here")
    st.write("Sign in with Google to open your resume workspace. Your first sign-in creates your app session.")
    with st.container(border=True):
        st.subheader("Welcome to ResumeMatch Pro")
        if configured:
            st.button("Continue with Google", type="primary", on_click=login,
                      key="google_sign_in", use_container_width=True)
        else:
            st.info("Sign-in is being prepared. Please check back shortly.")
        if st.session_state.get("_launch_login_error"):
            st.warning("Sign-in could not start. Please try again or return later.")
        st.caption("Your Google password stays with Google. ResumeMatch Pro does not ask for it.")
    st.button("Back to home", on_click=go_to, args=("Home",), key="login_home")
    if st.user.get("is_logged_in", False):
        if configured:
            st.warning("This account did not provide a verified email. Please use another Google account.")
        st.button("Sign out", on_click=logout, key="invalid_account_logout")


def _dashboard(identity):
    name = identity["name"] if identity else "guest"
    st.markdown(f'<p class="rm-greeting">Welcome, {escape(name)}.</p>',
                unsafe_allow_html=True)
    st.caption("Your workspace · Results are available in this session")
    if "analysis" in st.session_state:
        columns = st.columns(3)
        for column, (label, key) in zip(columns, (
            ("Latest match", "final_score"),
            ("Requirement coverage", "ats_score"),
            ("Keyword coverage", "keyword_score"),
        )):
            column.metric(label, f"{st.session_state.get(key, 0)}%")
    else:
        st.info("Start with your resume and a target job below. Your analysis will appear here.")
    st.divider()


def _account(identity):
    st.title("Your account")
    with st.container(border=True):
        st.text(f"Name: {identity['name']}")
        st.text(f"Email: {identity['email']}")
        st.write("Sign-in method: Google")
    st.write("This first version keeps your analysis in the current session. Saved history across visits is not available yet.")
    st.button("Clear current analysis", on_click=clear_workspace, key="clear_workspace")
    st.button("Sign out", on_click=logout, key="account_logout")


def _help():
    st.title("Help")
    with st.expander("Which resume files work?", expanded=True):
        st.write("Upload a text-based PDF up to 10 MB. Scanned or image-only resumes may not contain readable text; export a PDF from your document editor.")
    with st.expander("What do the recommendations mean?"):
        st.write("Strong Match: keep the evidence. Proof Gap: add a genuine example if you have one. Wording Gap: consider clearer wording only if it describes your actual work. True Gap: supporting evidence was not found in this resume.")
    with st.expander("Why can my score change?"):
        st.write("AI may interpret your resume or job description differently on a new analysis. The score is guidance, not a hiring decision or an employer's ATS result.")
    with st.expander("Where is my previous analysis?"):
        st.write("Results remain in your current session. Clearing the session or signing out removes them from this workspace. Saved history is not available yet.")
    with st.expander("How many analyses can I run?"):
        st.write("Guests get 3 analyses per browser each month. A free Google account gets a separate allowance of 10 each month. Only an active paid plan grants more than 10 account analyses. Allowances reset on the first day of each calendar month at 00:00 UTC; refreshing or clearing the current analysis does not reset usage.")
    st.link_button("Report a problem", "https://github.com/ThisisVinayakGupta/ai-resume-jd-analyzer/issues")


def _privacy():
    st.title("How your information is used")
    st.subheader("Sign-in")
    st.write("Google authenticates your account. The app receives your name, email, and account identifier. Streamlit uses a sign-in cookie to remember your login.")
    st.subheader("Resume analysis")
    st.write("When you click Analyze Resume, text from your PDF and the job description is sent to Google Gemini to generate the analysis. Upload only information you are comfortable sharing with that service.")
    st.subheader("Current-session results")
    st.write("Resumes and reports are held in the active app session, rather than saved to the application database. A database stores monthly usage, request status, account email, and paid entitlements to enforce allowances. Guests have a signed trial identifier stored in their browser. Clearing your analysis or signing out clears the workspace, but does not reset database usage or delete data already processed by the AI or hosting provider.")
    st.subheader("Your choices")
    st.write("You can omit sensitive details before uploading, clear the current analysis from Account, and sign out. AI and hosting providers have their own data handling policies.")
    st.link_button("Google privacy policy", "https://policies.google.com/privacy")


def _plans():
    st.title("Choose how you use ResumeMatch Pro")
    for column, (name, allowance, description) in zip(st.columns(3), (
        ("Guest", "3 / month", "Try the analyzer without signing in. Allowance is per browser."),
        ("Free account", "10 / month", "Sign in with Google for an account-based monthly allowance."),
        ("Paid", "More than 10 / month", "A larger allowance requires an active, verified paid plan."),
    )):
        with column:
            with st.container(border=True):
                st.subheader(name)
                st.markdown(f"**{allowance}**")
                st.write(description)
    st.button("Try as a guest", on_click=go_to, args=("Workspace",), key="plans_guest")
    st.button("Sign in", on_click=go_to, args=("Account",), key="plans_signin")
    st.info("Paid checkout is being prepared. This version does not accept payments yet.")


def render_launch_shell():
    """Allow the workspace for a verified browser trial or signed-in account."""
    _styles()
    configured = auth_is_configured()
    identity = current_identity() if configured else None
    bind_session(identity)
    if not st.session_state.get("_launch_route_initialized"):
        requested = st.query_params.get("page", "").casefold()
        if requested in {page.casefold() for page in PAGES}:
            st.session_state["_launch_page"] = next(page for page in PAGES if page.casefold() == requested)
        st.session_state["_launch_route_initialized"] = True
    with st.sidebar:
        st.subheader("🚀 ResumeMatch Pro")
        st.caption("Honest applications. Better decisions.")
        page = st.radio("Navigation", PAGES, key="_launch_page", label_visibility="collapsed")
        if identity:
            st.text(identity["email"])
            st.button("Sign out", on_click=logout, key="sidebar_logout", use_container_width=True)
    if st.query_params.get("page") != page.casefold():
        st.query_params["page"] = page.casefold()
    brand, plans, action = st.columns([4, 1, 1])
    brand.markdown('<div class="rm-brand"><span class="rm-monogram">RM</span>ResumeMatch Pro</div>', unsafe_allow_html=True)
    with plans:
        st.button("Plans", on_click=go_to, args=("Plans",), key="header_plans", use_container_width=True)
    with action:
        if identity:
            st.button("Sign out", on_click=logout, key="header_logout", use_container_width=True)
        else:
            st.button("Sign in", on_click=go_to, args=("Account",), key="header_signin", use_container_width=True)
    show_workspace = False
    if page == "Home":
        _home(identity)
    elif page == "Account" and identity is None:
        _sign_in(configured)
    elif page == "Workspace":
        try:
            allowance = workspace_allowance(identity)
            if allowance is None:
                st.info("Preparing your browser trial…")
            else:
                st.session_state["_quota_allowance"] = allowance
                st.caption(f"{allowance.plan} · {allowance.remaining} of {allowance.limit} monthly analyses remaining · Resets on the 1st at 00:00 UTC")
                if allowance.remaining == 0:
                    st.warning("Your monthly allowance is used. Sign in for your free account allowance, choose a paid plan, or return next month." if identity is None else "Your monthly allowance is used. More than 10 account analyses require an active paid plan, or you can return next month.")
                    st.button("Sign in" if identity is None else "View plans", on_click=go_to,
                              args=("Account" if identity is None else "Plans",), key="quota_upgrade")
                _dashboard(identity)
                show_workspace = True
        except QuotaUnavailable:
            st.info("Resume analysis is being prepared. Please try again shortly.")
    elif page == "Account":
        _account(identity)
    elif page == "Plans":
        _plans()
    elif page == "Help":
        _help()
    elif page == "Privacy":
        _privacy()
    if not show_workspace:
        st.markdown('<div class="rm-footer">ResumeMatch Pro · Present your real experience with confidence. <a href="?page=help">Help</a><a href="?page=privacy">Privacy</a></div>',
                    unsafe_allow_html=True)
    return show_workspace
