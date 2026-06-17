from sqlalchemy.orm import Session


class NotificationService:
    """Stub NotificationService for core-service to support old signatures.

    All actual notifications are handled by notification-service via RabbitMQ
    events.
    """

    def __init__(self, db: Session = None):
        self.db = db

    def notify_request_created(self, request) -> None:
        pass

    def notify_request_matched(self, request, donor_id: int) -> None:
        pass

    def notify_request_accepted(self, request) -> None:
        pass

    def notify_request_fulfilled(self, request) -> None:
        pass

    def send_broadcast(self, blood_group: str, message: str) -> None:
        pass
