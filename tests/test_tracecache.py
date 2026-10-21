from keychain.web.tracecache import TraceCache

REQUEST = {
    "image": "data:image/png;base64,picture",
    "mask": None,
    "connections": [],
    "colours": [{"name": "black", "hex": "#000000"}, {"name": "red", "hex": "#e03838"}],
    "spec": {"width_mm": 50, "rim_mm": 1.5, "hole_mm": 4, "thickness_mm": 3, "core_mm": 1.4},
    "rim": None,
    "hole": None,
}


def changed(**fields) -> dict:
    return {**REQUEST, **fields}


def resized(**spec) -> dict:
    return changed(spec={**REQUEST["spec"], **spec})


def test_only_a_change_that_goes_into_tracing_traces_the_picture_again():
    cache = TraceCache()
    traces = []

    def traces_for(request: dict) -> int:
        cache.traced(request, lambda: traces.append(request) or object())
        return len(traces)

    assert traces_for(REQUEST) == 1
    # Around the picture, or only names: the traced picture is kept.
    assert traces_for(changed(rim="black")) == 1
    assert traces_for(changed(hole=[-20, 0])) == 1
    assert traces_for(resized(hole_mm=5, thickness_mm=4, core_mm=2, rim_mm=2.5)) == 1
    assert traces_for(changed(colours=[{"name": "ink", "hex": "#000000"}, REQUEST["colours"][1]])) == 1
    # The picture itself: traced again.
    assert traces_for(resized(width_mm=45)) == 2
    assert traces_for(changed(colours=[REQUEST["colours"][0], {"name": "red", "hex": "#ff0000"}])) == 3
    assert traces_for(changed(mask="data:image/png;base64,painted")) == 4
    assert traces_for(changed(connections=[[[1, 2], [3, 4]]])) == 5
    assert traces_for(REQUEST) == 5  # kept from the start
