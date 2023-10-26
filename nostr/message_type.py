class ClientMessageType:
    EVENT = "EVENT"
    REQUEST = "REQ"
    CLOSE = "CLOSE"
    AUTH = "AUTH"

class RelayMessageType:
    EVENT = "EVENT"
    NOTICE = "NOTICE"
    END_OF_STORED_EVENTS = "EOSE"
    AUTH = "AUTH"

    @staticmethod
    def is_valid(type: str) -> bool:
        if type == RelayMessageType.EVENT or type == RelayMessageType.NOTICE or type == RelayMessageType.END_OF_STORED_EVENTS:
            return True
        return False
