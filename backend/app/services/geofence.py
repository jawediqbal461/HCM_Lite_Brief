"""Office geofence checks for camera attendance.

The phone only reports where it thinks it is; the server decides whether that is
close enough to the office, so a check-in cannot be faked by editing the client.
"""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000.0

# A fix worse than this is too vague to prove someone is on site (brief, Section 5).
MAX_GPS_ACCURACY_M = 100.0


def haversine_metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points, in metres."""
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    d_lat = lat2_r - lat1_r
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(d_lng / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


class GeofenceResult:
    def __init__(self, ok: bool, reason: str | None = None, distance_m: float | None = None):
        self.ok = ok
        self.reason = reason
        self.distance_m = distance_m


def check_camera_attendance(
    settings,
    *,
    face_detected: bool | None,
    faces_count: int | None,
    lat: float | None,
    lng: float | None,
    accuracy: float | None,
) -> GeofenceResult:
    """Decide whether a camera check-in may be accepted.

    Every rule here is enforced server-side even though the browser checks the same
    things first — the client's answer is a convenience, not evidence.
    """
    if settings.office_lat is None or settings.office_lng is None:
        return GeofenceResult(False, "Office location is not set. Ask an Admin to set it in Company setup.")

    if faces_count is not None:
        if faces_count == 0:
            return GeofenceResult(False, "No face detected. Look at the camera and try again.")
        if faces_count > 1:
            return GeofenceResult(False, "More than one face in the frame. Only you should be visible.")
    elif not face_detected:
        return GeofenceResult(False, "No face detected. Look at the camera and try again.")

    if lat is None or lng is None:
        return GeofenceResult(False, "Location unavailable. Allow location access and try again.")

    if accuracy is not None and accuracy > MAX_GPS_ACCURACY_M:
        return GeofenceResult(
            False,
            f"Location is not precise enough ({accuracy:.0f} m). Move outdoors or near a window and try again.",
        )

    distance = haversine_metres(lat, lng, settings.office_lat, settings.office_lng)
    if distance > settings.office_radius_m:
        return GeofenceResult(
            False,
            f"You are about {distance:.0f} m from the office, outside the {settings.office_radius_m} m check-in area.",
            distance,
        )

    return GeofenceResult(True, None, distance)
