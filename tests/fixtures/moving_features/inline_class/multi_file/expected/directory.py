"""Directory module that accesses person.phone_number fields."""

from person import Person


def print_directory_entry(person: Person):
    """Print a directory entry with person's phone information.

    Accesses person.phone_number.area_code through the PhoneNumber object.
    """
    print(f"Name: {person.get_name()}")
    print(f"Phone: ({person.area_code}) {person.number}")


def search_by_area_code(people: list, area_code: str):
    """Find all people with a given area code."""
    return [p for p in people if p.area_code == area_code]


def format_contact_list(people: list):
    """Format a list of people with their phone numbers."""
    entries = []
    for person in people:
        entry = f"{person.name}: ({person.area_code}) {person.number}"
        entries.append(entry)
    return entries


def get_phone_parts(person: Person):
    """Get area code and number separately."""
    return person.get_area_code(), person.get_number()
