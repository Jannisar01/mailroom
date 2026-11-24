class MailroomError(Exception):
    """A problem Mailroom explains to the user in one plain line."""


class DataError(MailroomError):
    """A data file has a row Mailroom cannot read."""


class SendError(MailroomError):
    """The practice server refused or could not be reached."""
