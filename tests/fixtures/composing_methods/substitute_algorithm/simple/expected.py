def found_person(people):
    candidates = ["Don", "John", "Kent"]
    for person in people:
        if person in candidates:
            return person
    return ""
