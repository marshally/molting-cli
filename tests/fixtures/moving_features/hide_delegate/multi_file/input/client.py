"""Client code that violates Law of Demeter by accessing person.department.manager."""

from person import Person


def get_manager_name(person: Person):
    """Get the name of a person's manager.

    This violates Law of Demeter by reaching through person
    to access department.manager.
    """
    manager = person.department.manager
    return manager


def print_org_structure(person: Person):
    """Print organizational structure for a person."""
    print(f"Employee: {person.get_name()}")
    print(f"Department: {person.department.get_name()}")
    print(f"Manager: {person.department.manager}")


def check_if_manager(person: Person, potential_manager):
    """Check if potential_manager is person's actual manager."""
    return person.department.manager == potential_manager
