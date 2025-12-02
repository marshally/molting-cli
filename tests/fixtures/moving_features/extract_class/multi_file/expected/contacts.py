"""Contacts module that uses person's phone fields."""

from person import Person


def export_to_vcf(person: Person):
    """Export person to VCF format.

    Uses person.area_code, person.number, and person.extension.
    """
    vcf = f"BEGIN:VCARD\n"
    vcf += f"FN:{person.name}\n"
    vcf += f"TEL;TYPE=work:+1{person.phone_number.area_code}{person.phone_number.number}"
    if person.phone_number.extension:
        vcf += f";ext={person.phone_number.extension}"
    vcf += "\n"
    vcf += "END:VCARD\n"
    return vcf


def validate_phone(person: Person):
    """Validate that person has a valid phone number."""
    if not person.phone_number.area_code or len(person.phone_number.area_code) != 3:
        return False
    if not person.phone_number.number or len(person.phone_number.number) != 7:
        return False
    return True
