import socket

def is_online(host="generativelanguage.googleapis.com", port=443, timeout=2.0) -> bool:
    """
    Check if the Gemini API host is reachable.
    Pings the Google API gateway directly on port 443 with a 2.0s timeout,
    preventing false-offline detections on slow or fluctuating networks.
    """
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False
