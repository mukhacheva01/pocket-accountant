"""Tests for bot.callbacks."""

from bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback


def test_event_action_pack_unpack():
    cb = EventActionCallback(action="done", event_id="ev123")
    packed = cb.pack()
    assert "event" in packed
    unpacked = EventActionCallback.unpack(packed)
    assert unpacked.action == "done"
    assert unpacked.event_id == "ev123"


def test_page_callback_pack_unpack():
    cb = PageCallback(screen="events", page=2)
    packed = cb.pack()
    unpacked = PageCallback.unpack(packed)
    assert unpacked.screen == "events"
    assert unpacked.page == 2


def test_navigation_callback():
    cb = NavigationCallback(target="home")
    packed = cb.pack()
    assert "nav" in packed
    unpacked = NavigationCallback.unpack(packed)
    assert unpacked.target == "home"


def test_subscription_callback():
    cb = SubscriptionCallback(action="buy", plan="basic")
    packed = cb.pack()
    unpacked = SubscriptionCallback.unpack(packed)
    assert unpacked.action == "buy"
    assert unpacked.plan == "basic"
