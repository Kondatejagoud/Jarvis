import threading

class EventBus:
    """
    A thread-safe publish-subscribe Event Bus for Project Jarvis.
    Allows independent modules to subscribe to lifecycle events 
    and communicate asynchronously without tight coupling.
    """
    def __init__(self):
        self._listeners = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback) -> None:
        """
        Subscribe a callable callback to a specific event type.
        Usage: event_bus.subscribe("WAKE_WORD_DETECTED", my_callback)
        """
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback) -> None:
        """
        Remove a callback from the subscribers list of an event type.
        """
        with self._lock:
            if event_type in self._listeners:
                try:
                    self._listeners[event_type].remove(callback)
                except ValueError:
                    pass

    def publish(self, event_type: str, data: dict = None) -> None:
        """
        Publish an event to all subscribed listeners.
        Usage: event_bus.publish("WAKE_WORD_DETECTED", {"score": 0.82})
        """
        with self._lock:
            # Copy listener references under lock to execute outside lock
            listeners = self._listeners.get(event_type, []).copy()

        for callback in listeners:
            try:
                # Call callback(event_type, data)
                callback(event_type, data)
            except Exception as e:
                print(f"[EventBus] Error executing listener {callback.__name__} for '{event_type}': {e}")
