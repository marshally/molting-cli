def process_status(status, code, flag, extra):
    if status == "error":
        result = "ERROR"
    else:
        if code == 404:
            result = "NOT_FOUND"
        else:
            if flag:
                result = "PROCESSING"
            else:
                if extra:
                    result = "EXTRA"
                else:
                    result = "OK"
    return result
