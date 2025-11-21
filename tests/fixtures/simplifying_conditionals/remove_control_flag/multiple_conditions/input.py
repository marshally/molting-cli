def check_security(people):
    found = False
    for person in people:
        if not found:
            if person == "Don":
                send_alert()
                found = True
            if person == "John":
                send_alert()
                found = True
    return found


def send_alert():
    print("Alert sent!")
