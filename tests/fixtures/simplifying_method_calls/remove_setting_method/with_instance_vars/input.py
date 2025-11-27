class User:
    def __init__(self, user_id, creation_timestamp):
        self._user_id = user_id
        self._creation_timestamp = creation_timestamp
        self.name = None
        self.email = None

    def get_user_id(self):
        return self._user_id

    def set_user_id(self, user_id):
        self._user_id = user_id

    def get_creation_timestamp(self):
        return self._creation_timestamp

    def set_creation_timestamp(self, timestamp):
        self._creation_timestamp = timestamp
