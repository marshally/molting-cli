"""Booking system for hotel reservations."""


class DateRange:
    """Represents a date range for bookings."""

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    def is_valid(self):
        """Check if the date range is valid."""
        return self.start_date < self.end_date


class Booking:
    """Handles hotel room bookings."""

    def __init__(self):
        self.reservations = []

    def book(self, date_range, guest_name, guest_email):
        """Create a booking with date range and guest information.

        Args:
            date_range: DateRange object with start and end dates
            guest_name: Name of the guest
            guest_email: Email address of the guest

        Returns:
            Booking confirmation number
        """
        if not date_range.is_valid():
            raise ValueError("Start date must be before end date")

        reservation = {
            "start": date_range.start_date,
            "end": date_range.end_date,
            "guest": guest_name,
            "email": guest_email,
            "confirmation": self._generate_confirmation_number()
        }
        self.reservations.append(reservation)
        return reservation["confirmation"]

    def _generate_confirmation_number(self):
        """Generate a unique confirmation number."""
        return f"CONF-{len(self.reservations) + 1:04d}"
