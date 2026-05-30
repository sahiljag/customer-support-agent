
"""Streamlit dashboard for support agents."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000",
)

st.set_page_config(
    page_title="Support Copilot",
    layout="wide",
)

st.title("Support Copilot Dashboard")


@st.cache_data(ttl=10)
def fetch_tickets() -> list[dict[str, Any]]:

    response = requests.get(
        f"{API_BASE_URL}/api/tickets",
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


def fetch_draft(
    ticket_id: int,
) -> dict[str, Any] | None:

    response = requests.get(
        f"{API_BASE_URL}/api/drafts/{ticket_id}",
        timeout=20,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    return response.json()


def _extract_api_error(
    response: requests.Response,
) -> str:

    try:
        payload = response.json()

    except ValueError:
        return (
            response.text
            or response.reason
            or "Unknown API error"
        )

    detail = payload.get("detail")

    if isinstance(detail, list):

        parts = []

        for item in detail:

            if isinstance(item, dict):

                loc = ".".join(
                    str(p)
                    for p in item.get("loc", [])
                )

                msg = item.get(
                    "msg",
                    "validation error",
                )

                parts.append(
                    f"{loc}: {msg}"
                    if loc else msg
                )

            else:
                parts.append(str(item))

        return "; ".join(parts)

    if detail:
        return str(detail)

    return str(payload)


def create_ticket(
    payload: dict[str, Any],
) -> dict[str, Any]:

    response = requests.post(
        f"{API_BASE_URL}/api/tickets",
        json=payload,
        timeout=20,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            _extract_api_error(response)
        )

    fetch_tickets.clear()

    return response.json()


def trigger_draft(
    ticket_id: int,
) -> dict[str, Any]:

    response = requests.post(
        f"{API_BASE_URL}/api/tickets/{ticket_id}/generate-draft",
        timeout=60,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            _extract_api_error(response)
        )

    return response.json()["draft"]


def update_draft(
    draft_id: int,
    content: str,
    status: str,
) -> dict[str, Any]:

    response = requests.patch(
        f"{API_BASE_URL}/api/drafts/{draft_id}",
        json={
            "content": content,
            "status": status,
        },
        timeout=20,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            _extract_api_error(response)
        )

    fetch_tickets.clear()

    return response.json()


def ingest_knowledge(
    clear_existing: bool,
) -> dict[str, Any]:

    response = requests.post(
        f"{API_BASE_URL}/api/knowledge/ingest",
        json={
            "clear_existing": clear_existing
        },
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            _extract_api_error(response)
        )

    return response.json()


with st.sidebar:

    st.subheader("API Settings")

    st.code(API_BASE_URL)

    if st.button(
        "Ingest Knowledge Base",
        use_container_width=True,
    ):

        try:

            result = ingest_knowledge(
                clear_existing=False
            )

            st.success(
                f"Indexed "
                f"{result['files_indexed']} files / "
                f"{result['chunks_indexed']} chunks"
            )

        except Exception as exc:
            st.error(
                f"Knowledge ingest failed: {exc}"
            )


st.subheader("Create Ticket")

with st.form("create_ticket_form"):

    col1, col2 = st.columns(2)

    with col1:

        customer_email = st.text_input(
            "Customer Email",
            placeholder="alex@bank.com",
        )

        customer_name = st.text_input(
            "Customer Name",
            placeholder="Alex",
        )

    with col2:

        customer_company = st.text_input(
            "Company",
            placeholder="ABC Bank",
        )

        priority = st.selectbox(
            "Priority",
            ["low", "medium", "high", "urgent"],
            index=1,
        )

    subject = st.text_input("Subject")

    description = st.text_area(
        "Description",
        height=120,
    )

    auto_generate = st.checkbox(
        "Auto-generate AI Draft",
        value=True,
    )

    submitted = st.form_submit_button(
        "Create Ticket"
    )

    if submitted:

        if (
            not customer_email
            or not subject
            or not description
        ):

            st.warning(
                "Email, subject, and description are required."
            )

        elif len(subject.strip()) < 10:

            st.warning(
                "Subject must be at least 10 characters."
            )

        elif len(description.strip()) < 10:

            st.warning(
                "Description must be at least 10 characters."
            )

        else:

            try:

                created = create_ticket(
                    {
                        "customer_email": customer_email,
                        "customer_name": (
                            customer_name or None
                        ),
                        "customer_company": (
                            customer_company or None
                        ),
                        "subject": subject,
                        "description": description,
                        "priority": priority,
                        "auto_generation": auto_generate,
                    }
                )

                st.success(
                    f"Ticket #{created['id']} created successfully"
                )

            except Exception as exc:

                st.error(
                    f"Ticket creation failed: {exc}"
                )


st.divider()

st.subheader("Tickets")


try:

    tickets = fetch_tickets()

except Exception as exc:

    tickets = []

    st.error(
        f"Could not load tickets: {exc}"
    )


if not tickets:

    st.info(
        "No tickets found. Create one above."
    )

else:

    labels = [
        (
            f"#{t['id']} | "
            f"{t['priority']} | "
            f"{t['customer_email']} | "
            f"{t['subject']}"
        )
        for t in tickets
    ]

    selected_label = st.selectbox(
        "Select Ticket",
        labels,
    )

    selected_ticket = tickets[
        labels.index(selected_label)
    ]

    st.markdown("### Ticket Details")

    st.write(
        f"**Customer:** "
        f"{selected_ticket['customer_email']}"
    )

    st.write(
        f"**Priority:** "
        f"{selected_ticket['priority']}"
    )

    st.write(
        f"**Status:** "
        f"{selected_ticket['status']}"
    )

    st.write(
        f"**Description:** "
        f"{selected_ticket['description']}"
    )

    if st.button(
        "Generate AI Draft",
        use_container_width=True,
    ):

        try:

            new_draft = trigger_draft(
                selected_ticket["id"]
            )

            st.session_state[
                f"draft_{selected_ticket['id']}"
            ] = new_draft

            st.success(
                "Draft generated successfully"
            )

        except Exception as exc:

            st.error(
                f"Draft generation failed: {exc}"
            )

    draft_data = (
        st.session_state.get(
            f"draft_{selected_ticket['id']}"
        )
        or fetch_draft(selected_ticket["id"])
    )

    if draft_data:

        st.markdown("### AI Draft")

        edited_content = st.text_area(
            "Edit Draft",
            value=draft_data["content"],
            height=250,
            key=f"draft_{draft_data['id']}",
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Accept Draft",
                use_container_width=True,
            ):

                try:

                    updated = update_draft(
                        draft_data["id"],
                        edited_content,
                        "accepted",
                    )

                    st.session_state[
                        f"draft_{selected_ticket['id']}"
                    ] = updated

                    st.success(
                        "Draft accepted"
                    )

                except Exception as exc:

                    st.error(
                        f"Accept failed: {exc}"
                    )

        with col2:

            if st.button(
                "Discard Draft",
                use_container_width=True,
            ):

                try:

                    updated = update_draft(
                        draft_data["id"],
                        edited_content,
                        "discarded",
                    )

                    st.session_state[
                        f"draft_{selected_ticket['id']}"
                    ] = updated

                    st.warning(
                        "Draft discarded"
                    )

                except Exception as exc:

                    st.error(
                        f"Discard failed: {exc}"
                    )
