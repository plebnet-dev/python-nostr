import json
import threading

from .event import Event, AuthMessage
from .filter import Filters
from .message_pool import MessagePool
from .message_type import ClientMessageType
from .relay import Relay, RelayPolicy


class RelayException(Exception):
    pass


class RelayManager:
    def __init__(self) -> None:
        self.relays: dict[str, Relay] = {}
        self.threads: dict[str, threading.Thread] = {}
        self.queue_threads: dict[str, threading.Thread] = {}        
        self.message_pool = MessagePool()

    def add_relay(
        self, url: str, read: bool = True, write: bool = True, subscriptions={}
    ):
        policy = RelayPolicy(read, write)
        relay = Relay(url, policy, self.message_pool, subscriptions)
        self.relays[url] = relay

    def remove_relay(self, url: str):
        if url in self.relays:
            self.relays[url].close()
            self.relays.pop(url, None)
        if url in self.threads:
            self.threads[url].join(timeout=1)
            self.threads.pop(url, None)
        if url in self.queue_threads:
            self.queue_threads[url].join(timeout=1)
            self.queue_threads.pop(url, None)

    def add_subscription(self, id: str, filters: Filters):
        for relay in self.relays.values():
            relay.add_subscription(id, filters)

    def close_subscription(self, id: str):
        for relay in self.relays.values():
            relay.close_subscription(id)

    def open_connections(self, ssl_options: dict = None, proxy: dict = None):
        for relay in self.relays.values():
            self.threads[relay.url] = threading.Thread(
                target=relay.connect,
                args=(ssl_options, proxy),
                name=f"{relay.url}-thread",
                daemon=True,
            )
            self.threads[relay.url].start()

            self.queue_threads[relay.url] = threading.Thread(
                target=relay.queue_worker,
                args=(lambda: relay.shutdown,),
                name=f"{relay.url}-queue",
                daemon=True,
            )
            self.queue_threads[relay.url].start()

    def close_connections(self):
        for relay in self.relays.values():
            relay.close()

    def publish_message(self, message: str, url: str = None):
        for relay in self.relays.values():
            if relay.policy.should_write:
                if url is None or url == relay.url:
                    relay.publish(message)

    def publish_event(self, event: Event):
        """Verifies that the Event is publishable before submitting it to relays"""
        if event.signature is None:
            raise RelayException(f"Could not publish {event.id}: must be signed")

        if not event.verify():
            raise RelayException(
                f"Could not publish {event.id}: failed to verify signature {event.signature}"
            )
        self.publish_message(event.to_message())

    def publish_auth(self, auth: AuthMessage):
        """Verifies that the Event is publishable before submitting it to relays"""
        if auth.signature is None:
            raise RelayException(f"Could not publish {auth.id}: must be signed")

        if not auth.verify():
            raise RelayException(
                f"Could not publish {auth.id}: failed to verify signature {auth.signature}"
            )
        self.publish_message(auth.to_message(), auth.relay_url)
