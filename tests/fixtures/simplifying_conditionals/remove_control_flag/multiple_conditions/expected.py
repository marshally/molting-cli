def check_security(people):
    for person in people:
        if person == "Don":
            send_alert()
            return True
        if person == "John":
            send_alert()
            return True
    return False

def send_alert():
    print("Alert sent!")
