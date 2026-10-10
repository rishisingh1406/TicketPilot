import os

import requests
import streamlit as st


API_BASE_URL = os.getenv(
    "TICKETPILOT_API_URL",
    "https://ticketpilot-api.onrender.com",
).rstrip("/")


st.set_page_config(
    page_title="TicketPilot Reviewer",
    page_icon="TP",
    layout="wide",
)


# ---------------------------------------------------------
# API helpers
# ---------------------------------------------------------

def api_request(method: str, endpoint: str, **kwargs):
    """Make a request to the TicketPilot API."""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.request(
            method,
            url,
            timeout=30,
            **kwargs,
        )

        if response.status_code >= 400:
            st.error(
                f"API error {response.status_code}: "
                f"{response.text}"
            )
            return None

        return response.json()

    except requests.RequestException as exc:
        st.error(f"Could not connect to API: {exc}")
        return None


def get_tickets():
    return api_request("GET", "/tickets")


def get_reviews():
    return api_request("GET", "/reviews")


def create_ticket(user_id: int, message: str):
    return api_request(
        "POST",
        "/tickets",
        json={
            "user_id": user_id,
            "message": message,
        },
    )


def apply_reviewer_action(
    ticket_id: int,
    action: str,
    reviewer_identity: str,
    edited_answer: str,
    reason: str,
):
    return api_request(
        "POST",
        f"/reviews/{ticket_id}/action",
        json={
            "action": action,
            "reviewer_identity": reviewer_identity,
            "edited_answer": edited_answer,
            "reason": reason,
        },
    )


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.title("TicketPilot")

st.sidebar.caption(
    f"API: {API_BASE_URL}"
)

if st.sidebar.button("Check API Health"):
    health = api_request("GET", "/health")

    if health:
        st.sidebar.success(
            f"API healthy: {health.get('status')}"
        )


# ---------------------------------------------------------
# Main UI
# ---------------------------------------------------------

st.title("TicketPilot Reviewer")

tab1, tab2, tab3 = st.tabs(
    [
        "Create Ticket",
        "Tickets",
        "Review Queue",
    ]
)


# ---------------------------------------------------------
# Create Ticket
# ---------------------------------------------------------

with tab1:
    st.subheader("Create Ticket")

    user_id = st.number_input(
        "User ID",
        min_value=1,
        value=1001,
        step=1,
    )

    message = st.text_area(
        "Customer message",
        placeholder="Describe the customer's problem...",
        height=150,
    )

    if st.button(
        "Create Ticket",
        type="primary",
        use_container_width=True,
    ):
        if not message.strip():
            st.warning("Message cannot be empty.")

        else:
            with st.spinner("Creating ticket..."):
                result = create_ticket(
                    user_id=int(user_id),
                    message=message.strip(),
                )

            if result:
                st.success("Ticket created.")

                # Store latest result so it survives reruns.
                st.session_state["latest_ticket"] = result

                # -------------------------------------------------
                # Ticket information
                # -------------------------------------------------

                st.subheader("Ticket")

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Ticket ID",
                        result.get("ticket_id", "N/A"),
                    )

                with col2:
                    st.metric(
                        "Status",
                        result.get("status", "N/A"),
                    )

                # -------------------------------------------------
                # Agent response
                # -------------------------------------------------

                agent_response = (
                    result.get("generated_answer")
                    or result.get("agent_response")
                    or result.get("answer")
                    or result.get("final_answer")
                )

                st.subheader("Agent Response")

                if agent_response:
                    st.info(agent_response)

                else:
                    st.warning(
                        "No agent response was returned by the API."
                    )

                    st.caption(
                        "The current POST /tickets response may only "
                        "contain ticket creation information."
                    )

                # -------------------------------------------------
                # Raw API response
                # -------------------------------------------------

                with st.expander("Raw API Response"):
                    st.json(result)


# ---------------------------------------------------------
# Show latest ticket response
# ---------------------------------------------------------

if "latest_ticket" in st.session_state:
    latest_ticket = st.session_state["latest_ticket"]

    # This is outside the tabs so the latest result remains
    # visible after Streamlit reruns.

    st.sidebar.divider()
    st.sidebar.subheader("Latest Ticket")

    st.sidebar.write(
        f"Ticket: #{latest_ticket.get('ticket_id', 'N/A')}"
    )

    latest_answer = (
        latest_ticket.get("generated_answer")
        or latest_ticket.get("agent_response")
        or latest_ticket.get("answer")
        or latest_ticket.get("final_answer")
    )

    if latest_answer:
        st.sidebar.success("Agent response available")

    else:
        st.sidebar.warning("No agent response returned")


# ---------------------------------------------------------
# Tickets
# ---------------------------------------------------------

with tab2:
    st.subheader("Tickets")

    if st.button(
        "Refresh Tickets",
        use_container_width=True,
    ):
        st.session_state["tickets"] = get_tickets()

    tickets = st.session_state.get("tickets")

    if tickets is not None:

        if not tickets:
            st.info("No tickets found.")

        else:
            for ticket in tickets:

                # Support the expected API field.
                ticket_id = ticket.get("ticket_id")

                # Fallback in case API returns "id".
                if ticket_id is None:
                    ticket_id = ticket.get("id")

                if ticket_id is None:
                    st.warning(
                        "Skipping ticket with missing ticket ID."
                    )
                    continue

                with st.expander(
                    f"Ticket #{ticket_id}",
                    expanded=False,
                ):

                    # -----------------------------
                    # Ticket information
                    # -----------------------------

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(
                            "**User ID:**",
                            ticket.get("user_id", "N/A"),
                        )

                    with col2:
                        st.write(
                            "**Status:**",
                            ticket.get("status", "N/A"),
                        )

                    st.write("**Message:**")

                    st.write(
                        ticket.get(
                            "user_message",
                            ticket.get(
                                "message",
                                "N/A",
                            ),
                        )
                    )

                    # -----------------------------
                    # Agent response
                    # -----------------------------

                    agent_response = (
                        ticket.get("generated_answer")
                        or ticket.get("agent_response")
                        or ticket.get("answer")
                        or ticket.get("final_answer")
                    )

                    st.divider()

                    st.write("### Agent Response")

                    if agent_response:
                        st.info(agent_response)

                    else:
                        st.caption(
                            "No agent response available for this ticket."
                        )

                    # -----------------------------
                    # Raw ticket data
                    # -----------------------------

                    with st.expander("Raw Ticket Data"):
                        st.json(ticket)


# ---------------------------------------------------------
# Review Queue
# ---------------------------------------------------------

with tab3:
    st.subheader("Review Queue")

    if st.button(
        "Refresh Review Queue",
        use_container_width=True,
    ):
        st.session_state["reviews"] = get_reviews()

    reviews = st.session_state.get("reviews")

    if reviews is None:

        st.info(
            "Click 'Refresh Review Queue' to load tickets."
        )

    elif not reviews:

        st.success("Review queue is empty.")

    else:

        for review_index, review in enumerate(reviews):

            # -------------------------------------------------
            # Resolve ticket ID
            # -------------------------------------------------

            ticket_id = review.get("ticket_id")

            # Fallback if API returns a generic "id".
            if ticket_id is None:
                ticket_id = review.get("id")

            # A review without a ticket ID cannot safely be
            # acted upon because the action endpoint requires it.
            if ticket_id is None:

                st.warning(
                    f"Skipping review #{review_index + 1}: "
                    "missing ticket ID."
                )

                with st.expander(
                    f"Malformed Review #{review_index + 1}"
                ):
                    st.json(review)

                continue

            # -------------------------------------------------
            # Unique widget namespace
            # -------------------------------------------------

            widget_id = f"review_{ticket_id}_{review_index}"

            with st.expander(
                f"Ticket #{ticket_id}",
                expanded=True,
            ):

                # -------------------------------------------------
                # Customer message
                # -------------------------------------------------

                st.write("### Customer Message")

                st.write(
                    review.get(
                        "user_message",
                        review.get(
                            "message",
                            "N/A",
                        ),
                    )
                )

                # -------------------------------------------------
                # Agent response
                # -------------------------------------------------

                agent_response = (
                    review.get("generated_answer")
                    or review.get("agent_response")
                    or review.get("answer")
                    or review.get("final_answer")
                )

                st.write("### Agent Response")

                if agent_response:
                    st.info(agent_response)

                else:
                    st.warning(
                        "No generated answer is available."
                    )

                st.divider()

                # -------------------------------------------------
                # Reviewer fields
                # -------------------------------------------------

                reviewer_identity = st.text_input(
                    "Reviewer",
                    value="local-reviewer",
                    key=f"{widget_id}_reviewer",
                )

                edited_answer = st.text_area(
                    "Answer",
                    value=agent_response or "",
                    key=f"{widget_id}_answer",
                    height=150,
                )

                reason = st.text_area(
                    "Reason",
                    key=f"{widget_id}_reason",
                    placeholder=(
                        "Why are you resolving, editing, "
                        "or escalating this ticket?"
                    ),
                    height=100,
                )

                # -------------------------------------------------
                # Reviewer actions
                # -------------------------------------------------

                col1, col2, col3 = st.columns(3)

                with col1:

                    if st.button(
                        "Resolve",
                        key=f"{widget_id}_resolve",
                        use_container_width=True,
                    ):

                        result = apply_reviewer_action(
                            ticket_id=int(ticket_id),
                            action="RESOLVE",
                            reviewer_identity=reviewer_identity,
                            edited_answer=edited_answer,
                            reason=reason,
                        )

                        if result:

                            st.success(
                                "Ticket resolved."
                            )

                            st.json(result)

                with col2:

                    if st.button(
                        "Edit",
                        key=f"{widget_id}_edit",
                        use_container_width=True,
                    ):

                        result = apply_reviewer_action(
                            ticket_id=int(ticket_id),
                            action="EDIT",
                            reviewer_identity=reviewer_identity,
                            edited_answer=edited_answer,
                            reason=reason,
                        )

                        if result:

                            st.success(
                                "Ticket edited."
                            )

                            st.json(result)

                with col3:

                    if st.button(
                        "Escalate",
                        key=f"{widget_id}_escalate",
                        use_container_width=True,
                    ):

                        result = apply_reviewer_action(
                            ticket_id=int(ticket_id),
                            action="ESCALATE",
                            reviewer_identity=reviewer_identity,
                            edited_answer=edited_answer,
                            reason=reason,
                        )

                        if result:

                            st.success(
                                "Ticket escalated."
                            )

                            st.json(result)

                # -------------------------------------------------
                # Raw review data
                # -------------------------------------------------

                with st.expander("Raw Review Data"):
                    st.json(review)