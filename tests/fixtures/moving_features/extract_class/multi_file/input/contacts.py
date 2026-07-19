"""Contacts module that uses person's phone fields."""

from person import Person


def export_to_vcf(person: Person):
    """Export person to VCF format.

    Uses person.area_code, person.number, and person.extension.
    """
    vcf = f"BEGIN:VCARD\n"
    vcf += f"FN:{person.name}\n"
    vcf += f"TEL;TYPE=work:+1{person.area_code}{person.number}"
    if person.extension:
        vcf += f";ext={person.extension}"
    vcf += "\n"
    vcf += "END:VCARD\n"
    return vcf


def validate_phone(person: Person):
    """Validate that person has a valid phone number."""
    if not person.area_code or len(person.area_code) != 3:
        return False
    if not person.number or len(person.number) != 7:
        return False
    return True
