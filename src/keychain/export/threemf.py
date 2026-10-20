"""One 3MF file per keychain: every part a named, coloured piece of one object.

Adapted from the Tock lid generator; here each part has its own height range."""

from io import BytesIO
from xml.sax.saxutils import quoteattr
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import trimesh

from keychain.export.stl import extruded
from keychain.shape.stack import Part

MODEL_PATH = "3D/3dmodel.model"
CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""
RELATIONSHIPS = f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/{MODEL_PATH}" Id="rel0"
  Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""
MODEL_START = """<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
"""
MATERIALS_ID = 1
FIRST_PART_ID = 2
# The shapes are snapped to a 1e-4 mm grid before extruding, so more decimals add nothing.
COORDINATE_DECIMALS = 4


def keychain_3mf(name: str, parts: list[Part]) -> bytes:
    files = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": RELATIONSHIPS,
        MODEL_PATH: _model_xml(name, parts),
    }
    buffer = BytesIO()
    with ZipFile(buffer, "w") as package:
        for file_name, text in files.items():
            # A bare ZipInfo has a fixed date, so the same keychain always gives the same bytes.
            package.writestr(ZipInfo(file_name), text, compress_type=ZIP_DEFLATED)
    return buffer.getvalue()


def _model_xml(name: str, parts: list[Part]) -> str:
    part_ids = [FIRST_PART_ID + index for index in range(len(parts))]
    whole_id = FIRST_PART_ID + len(parts)
    objects = [
        _part_object(part_id, material_index, part)
        for material_index, (part_id, part) in enumerate(zip(part_ids, parts, strict=True))
    ]
    resources = _materials(parts) + "".join(objects) + _whole_object(whole_id, part_ids, name)
    build = f'<build><item objectid="{whole_id}"/></build>\n'
    return f"{MODEL_START}<resources>\n{resources}</resources>\n{build}</model>\n"


def _materials(parts: list[Part]) -> str:
    bases = [_tag("base", name=part.name, displaycolor=part.colour.upper()) for part in parts]
    return f'<basematerials id="{MATERIALS_ID}">{"".join(bases)}</basematerials>\n'


def _part_object(part_id: int, material_index: int, part: Part) -> str:
    attributes = {
        "id": part_id,
        "type": "model",
        "name": part.name,
        "pid": MATERIALS_ID,
        "pindex": material_index,
    }
    mesh = extruded(part.shape, part.bottom_mm, part.top_mm)
    return f"{_open_tag('object', **attributes)}<mesh>{_mesh_xml(mesh)}</mesh></object>\n"


def _mesh_xml(mesh: trimesh.Trimesh) -> str:
    vertices = [_tag("vertex", x=_number(x), y=_number(y), z=_number(z)) for x, y, z in mesh.vertices]
    triangles = [_tag("triangle", v1=a, v2=b, v3=c) for a, b, c in mesh.faces]
    return f"<vertices>{''.join(vertices)}</vertices><triangles>{''.join(triangles)}</triangles>"


def _whole_object(whole_id: int, part_ids: list[int], name: str) -> str:
    components = "".join(_tag("component", objectid=part_id) for part_id in part_ids)
    whole_tag = _open_tag("object", id=whole_id, type="model", name=name)
    return f"{whole_tag}<components>{components}</components></object>\n"


def _open_tag(element: str, /, **attributes) -> str:
    return f"<{element}{''.join(f' {key}={quoteattr(str(value))}' for key, value in attributes.items())}>"


def _tag(element: str, /, **attributes) -> str:
    return _open_tag(element, **attributes).removesuffix(">") + "/>"


def _number(value: float) -> str:
    return f"{value:.{COORDINATE_DECIMALS}f}".rstrip("0").rstrip(".")
