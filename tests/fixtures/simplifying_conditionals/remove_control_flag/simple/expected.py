def check_security(people):
    for person in people:
        if person == "Don":
            send_alert()
            return
        if person == "John":
            send_alert()
            return


def send_alert():
    pass
