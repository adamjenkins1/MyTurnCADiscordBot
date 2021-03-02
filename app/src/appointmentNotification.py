class AppointmentNotification:
    def __init__(self, channel_id: int, message: str, zip_code: int, user_id: int):
        self.channel_id = channel_id
        self.message = message
        self.user_id = user_id
        self.zip_code = zip_code