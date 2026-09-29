import requests
import streamlit as st


API_BASE_URL = "http://localhost:8000"


st.set_page_config(
    page_title="TicketPilot Reviewer",
    page_icon="",
    layout="wide",
)

st.title("TicketPilot — Reviewer Queue")


def get_reviews():
    response = requests.get(
        f"{API_BASE_URL}/reviews",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def apply_reviewer_action(
    ticket_id: int,
    action: str,
    reviewer_identity: str,
    edited_answer: str | None = None,
    reason: str | None = None,
):
    payload = {
        "action": action,
        "reviewer_identity": reviewer_identity,
        "edited_answer": edited_answer,
        "reason": reason,
    }

    response = requests.post(
        f"{API_BASE_URL}/reviews/{ticket_id}/action",
        json=payload,
        timeout=10,
    )

    response.raise_for_status()
    return response.json()


def get_error_detail(exc: requests.HTTPError) -> str:
    if exc.response is None:
        return str(exc)

    try:
        return exc.response.json().get(
            "detail",
            str(exc),
        )
    except ValueError:
        return str(exc)


# ============================================================
# Reviewer identity
# ============================================================

reviewer_identity = st.sidebar.text_input(
    "Reviewer identity",
    placeholder="e.g. reviewer-001",
)

if not reviewer_identity.strip():
    st.warning(
        "Enter your reviewer identity before taking an action."
    )


# ============================================================
# Load review queue
# ============================================================

try:
    reviews = get_reviews()

except requests.RequestException as exc:
    st.error(
        f"Could not connect to TicketPilot API: {exc}"
    )
    st.stop()


st.subheader(f"Review Queue ({len(reviews)})")


if not reviews:
    st.info(
        "No tickets are currently waiting for review."
    )
    st.stop()


# ============================================================
# Review tickets
# ============================================================

for review in reviews:

    ticket = review["ticket"]
    agent_result = review["agent_result"]
    evidence = review["evidence"]

    ticket_id = int(ticket["ticket_id"])

    proposed_answer = agent_result.get(
        "proposed_answer"
    )

    with st.container(border=True):

        st.markdown(
            f"### Ticket #{ticket_id}"
        )

        col1, col2 = st.columns(2)

        # ----------------------------------------------------
        # Customer / escalation information
        # ----------------------------------------------------

        with col1:

            st.markdown("#### Customer message")

            st.write(
                ticket["original_user_message"]
            )

            st.markdown("#### Escalation reason")

            st.write(
                review["escalation_context"]
            )

        # ----------------------------------------------------
        # Agent result
        # ----------------------------------------------------

        with col2:

            st.markdown("#### Proposed AI answer")

            if proposed_answer:
                st.write(proposed_answer)
            else:
                st.info(
                    "The agent did not produce a proposed answer."
                )

            st.markdown("#### Agent decision")

            st.write(
                agent_result["decision"]
            )

        # ----------------------------------------------------
        # Retrieved evidence
        # ----------------------------------------------------

        st.markdown("#### Retrieved evidence")

        chunks = evidence.get(
            "retrieved_chunks",
            [],
        )

        if not chunks:

            st.write(
                "No retrieved evidence."
            )

        else:

            for index, chunk in enumerate(
                chunks,
                start=1,
            ):

                with st.expander(
                    f"Evidence {index} — {chunk['source']}"
                ):
                    st.write(
                        chunk["content"]
                    )

        st.divider()

        # ====================================================
        # Reviewer actions
        # ====================================================

        st.markdown("#### Reviewer action")

        action_col1, action_col2, action_col3 = (
            st.columns(3)
        )

        # ----------------------------------------------------
        # RESOLVE
        # ----------------------------------------------------

        with action_col1:

            if st.button(
                "Resolve",
                key=f"resolve_{ticket_id}",
                disabled=not reviewer_identity.strip(),
                use_container_width=True,
            ):

                try:

                    apply_reviewer_action(
                        ticket_id=ticket_id,
                        action="RESOLVE",
                        reviewer_identity=(
                            reviewer_identity.strip()
                        ),
                    )

                    st.success(
                        f"Ticket #{ticket_id} "
                        "resolved successfully."
                    )

                    st.rerun()

                except requests.HTTPError as exc:

                    st.error(
                        f"Resolve failed: "
                        f"{get_error_detail(exc)}"
                    )

                except requests.RequestException as exc:

                    st.error(
                        "Could not reach TicketPilot API: "
                        f"{exc}"
                    )

        # ----------------------------------------------------
        # EDIT AND RESOLVE
        # ----------------------------------------------------

        with action_col2:

            edit_expanded = st.checkbox(
                "Edit answer",
                key=f"edit_toggle_{ticket_id}",
            )

            if edit_expanded:

                edited_answer = st.text_area(
                    "Edited answer",
                    value=proposed_answer or "",
                    key=f"edited_answer_{ticket_id}",
                    height=150,
                )

                if st.button(
                    "Edit & Resolve",
                    key=f"edit_resolve_{ticket_id}",
                    disabled=(
                        not reviewer_identity.strip()
                        or not edited_answer.strip()
                    ),
                    use_container_width=True,
                ):

                    try:

                        apply_reviewer_action(
                            ticket_id=ticket_id,
                            action="EDIT_AND_RESOLVE",
                            reviewer_identity=(
                                reviewer_identity.strip()
                            ),
                            edited_answer=(
                                edited_answer.strip()
                            ),
                        )

                        st.success(
                            f"Ticket #{ticket_id} "
                            "edited and resolved."
                        )

                        st.rerun()

                    except requests.HTTPError as exc:

                        st.error(
                            f"Edit & resolve failed: "
                            f"{get_error_detail(exc)}"
                        )

                    except requests.RequestException as exc:

                        st.error(
                            "Could not reach "
                            "TicketPilot API: "
                            f"{exc}"
                        )

        # ----------------------------------------------------
        # TAKE OVER
        # ----------------------------------------------------

        with action_col3:

            takeover_reason = st.text_area(
                "Take-over reason",
                placeholder=(
                    "Why does this require "
                    "human support?"
                ),
                key=f"takeover_reason_{ticket_id}",
                height=100,
            )

            if st.button(
                "Take Over",
                key=f"takeover_{ticket_id}",
                disabled=(
                    not reviewer_identity.strip()
                    or not takeover_reason.strip()
                ),
                use_container_width=True,
            ):

                try:

                    apply_reviewer_action(
                        ticket_id=ticket_id,
                        action="TAKE_OVER",
                        reviewer_identity=(
                            reviewer_identity.strip()
                        ),
                        reason=(
                            takeover_reason.strip()
                        ),
                    )

                    st.success(
                        f"Ticket #{ticket_id} "
                        "handed over to support."
                    )

                    st.rerun()

                except requests.HTTPError as exc:

                    st.error(
                        f"Take over failed: "
                        f"{get_error_detail(exc)}"
                    )

                except requests.RequestException as exc:

                    st.error(
                        "Could not reach "
                        "TicketPilot API: "
                        f"{exc}"
                    )
