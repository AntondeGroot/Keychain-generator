"""The last few traced pictures, so a change that leaves the picture itself alone, such as the
rim colour, the ring or the thickness, only reassembles the keychain: a fraction of a second
instead of several seconds."""

import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Callable

from keychain.design import TracedPicture

MOST_PICTURES = 8  # a few pictures, so switching back and forth stays fast too
# What the page sends that goes into tracing. The rim is not: it comes round the picture.
TRACING_FIELDS = ("image", "mask", "detail", "paint", "connections", "edges", "shapes")
TRACING_SPEC_FIELDS = ("width_mm", "height_mm", "curve_tolerance_mm")


class TraceCache:
    def __init__(self, size: int = MOST_PICTURES) -> None:
        self._size = size
        self._traced: OrderedDict[str, TracedPicture] = OrderedDict()
        self._lock = threading.Lock()  # the server answers requests side by side

    def traced(self, request: dict, trace: Callable[[], TracedPicture]) -> TracedPicture:
        """The traced picture for this request, tracing it only when it is not kept yet."""
        key = tracing_key(request)
        with self._lock:
            if key in self._traced:
                self._traced.move_to_end(key)
                return self._traced[key]
        traced = trace()
        with self._lock:
            self._traced[key] = traced
            while len(self._traced) > self._size:
                self._traced.popitem(last=False)
        return traced


def tracing_key(request: dict) -> str:
    """The same for two requests that would trace the same picture."""
    spec = request.get("spec") or {}
    parts = {name: request.get(name) for name in TRACING_FIELDS}
    parts["colours"] = [colour["hex"] for colour in request["colours"]]  # names change nothing here
    parts["spec"] = {field: spec.get(field) for field in TRACING_SPEC_FIELDS}
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()
