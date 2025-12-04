"""API endpoints for booking system."""

from datetime import datetime
from booking import Booking, DateRange


class BookingAPI:
    """REST API for booking operations."""

    def __init__(self):
        self.booking = Booking()

    def handle_booking_request(self, request_data):
        """Handle an API booking request.

        Args:
            request_data: Dictionary with request parameters

        Returns:
            Response dictionary with confirmation
        """
        # Parse request
        start_date = datetime.fromisoformat(request_data["start_date"])
        end_date = datetime.fromisoformat(request_data["end_date"])
        guest_name = request_data["guest_name"]
        guest_email = request_data["guest_email"]

        # Create booking with individual parameters
        try:
            date_range = DateRange(start_date, end_date)
            confirmation = self.booking.book(
                date_range, guest_name,
                guest_email
            )
            return {
                "status": "success",
                "confirmation": confirmation
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e)
            }
