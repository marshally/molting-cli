"""Reservation management module."""

from datetime import datetime
from booking import Booking


class ReservationManager:
    """Manages hotel reservations."""

    def __init__(self):
        self.booking_system = Booking()

    def create_reservation(self, guest_info):
        """Create a new reservation for a guest.

        Args:
            guest_info: Dictionary with guest details

        Returns:
            Confirmation number
        """
        start = datetime(2024, 6, 1)
        end = datetime(2024, 6, 5)
        name = guest_info["name"]
        email = guest_info["email"]

        # Call with all individual parameters
        confirmation = self.booking_system.book(start, end, name, email)
        print(f"Reservation created: {confirmation}")
        return confirmation
