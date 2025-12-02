"""Event tracking system."""

from counter import Counter


class EventTracker:
    """Tracks events and their frequencies."""

    def __init__(self):
        self.event_counter = Counter()
        self.event_log = []

    def track_event(self, event_name):
        """Track an event occurrence.

        Args:
            event_name: Name of the event to track

        Returns:
            Current count of total events
        """
        # Using separated query and modifier methods
        self.event_counter.increment()
        count = self.event_counter.get_value()
        self.event_log.append({
            "event": event_name,
            "count": count
        })
        print(f"Event '{event_name}' tracked. Total events: {count}")
        return count

    def get_event_count(self):
        """Get the total number of events tracked.

        Returns:
            Total event count
        """
        # Call site updated to use separated methods
        self.event_counter.increment()
        return self.event_counter.get_value()
