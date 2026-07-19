"""Directory module that uses person's phone fields."""

from person import Person


def print_directory_entry(person: Person):
    """Print a directory entry with person's phone information.

    Accesses person.area_code and person.number directly.
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
