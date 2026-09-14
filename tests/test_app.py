import os
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def test_app_initialization_and_layout():
    """Verify Streamlit app initializes without errors and displays key headers."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()
    assert not at.exception, f"App threw exception: {at.exception}"

    # Verify Sidebar content
    sidebar_titles = [t.value for t in at.sidebar.title]
    assert any("Vehicle Profile" in t for t in sidebar_titles)

    # Verify vehicle metrics rendered
    metric_labels = [m.label for m in at.sidebar.metric]
    assert "Odometer" in metric_labels
    assert "Last Svc" in metric_labels

    # Verify Tabs exist
    assert len(at.tabs) == 4


def test_app_chat_message_flow():
    """Verify initial greeting message is present in session state."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()
    assert not at.exception

    # Check that initial assistant greeting is present
    assert len(at.chat_message) >= 1
    assert "Rahul" in at.chat_message[0].markdown[0].value
    assert "Tata Nexon" in at.chat_message[0].markdown[0].value
