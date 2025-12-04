"""Booking system for hotel reservations."""


class Booking:
    """Handles hotel room bookings."""

    def __init__(self):
        self.reservations = []

    def book(self, start_date, end_date, guest_name, guest_email):
        """Create a booking with date range and guest information.

        Args:
            start_date: Start date of the booking
            end_date: End date of the booking
            guest_name: Name of the guest
            guest_email: Email address of the guest

        Returns:
            Booking confirmation number
        """
        if start_date >= end_date:
            raise ValueError("Start date must be before end date")

        reservation = {
            "start": start_date,
            "end": end_date,
            "guest": guest_name,
            "email": guest_email,
            "confirmation": self._generate_confirmation_number()
        }
        self.reservations.append(reservation)
        return reservation["confirmation"]

    def _generate_confirmation_number(self):
        """Generate a unique confirmation number."""
        return f"CONF-{len(self.reservations) + 1:04d}"
