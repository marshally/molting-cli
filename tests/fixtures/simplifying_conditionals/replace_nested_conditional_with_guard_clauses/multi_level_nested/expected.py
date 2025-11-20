def process_status(status, code, flag, extra):
    if status == "error":
        return "ERROR"
    if code == 404:
        return "NOT_FOUND"
    if flag:
        return "PROCESSING"
    if extra:
        return "EXTRA"
    return "OK"
