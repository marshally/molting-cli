"""System monitoring module."""

from counter import Counter


class SystemMonitor:
    """Monitors system activities and errors."""

    def __init__(self):
        self.request_counter = Counter()
        self.error_counter = Counter()

    def log_request(self, endpoint):
        """Log an incoming request.

        Args:
            endpoint: API endpoint being accessed

        Returns:
            Total number of requests processed
        """
        # Call site updated to use separated methods
        self.request_counter.increment()
        total = self.request_counter.get_value()
        print(f"Request to {endpoint} - Total requests: {total}")
        return total

    def log_error(self, error_type):
        """Log an error occurrence.

        Args:
            error_type: Type of error that occurred

        Returns:
            Total number of errors logged
        """
        # Call site updated to use separated methods
        self.error_counter.increment()
        error_count = self.error_counter.get_value()
        if error_count > 100:
            print(f"WARNING: High error count ({error_count})")
        return error_count

    def check_health(self):
        """Check system health based on error count.

        Returns:
            Boolean indicating if system is healthy
        """
        # Call site updated to use separated methods
        self.error_counter.increment()
        current_errors = self.error_counter.get_value()
        return current_errors < 50
