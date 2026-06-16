"""Generate watertight ASCII STL meshes by revolving an axisymmetric profile.

A *profile* is an ordered list of ``(r, z)`` points (radius, axial position) in
metres describing the outer (and, for hollow parts, inner) boundary of a solid
of revolution. ``revolve_solid`` sweeps a closed profile around the z-axis and
emits triangles, including flat caps so the mesh is closed.

These meshes let the user pull the simulated motor grain, nozzle and airframe
straight into a CAD package (STL import is universal) for further design work.
"""

from __future__ import annotations

import math

from ..sim.grain import Grain, GrainType
from ..sim.motor import Nozzle, exit_mach


def _tri(n, a, b, c) -> str:
    return (
        f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n"
        f"    outer loop\n"
        f"      vertex {a[0]:.6e} {a[1]:.6e} {a[2]:.6e}\n"
        f"      vertex {b[0]:.6e} {b[1]:.6e} {b[2]:.6e}\n"
        f"      vertex {c[0]:.6e} {c[1]:.6e} {c[2]:.6e}\n"
        f"    endloop\n"
        f"  endfacet\n"
    )


def _normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / mag, ny / mag, nz / mag)


def revolve_solid(
    profile: list[tuple[float, float]], name: str, segments: int = 64
) -> str:
    """Revolve a closed (r, z) profile around the z-axis into an STL solid."""
    facets: list[str] = []
    pts = profile
    npts = len(pts)
    dtheta = 2.0 * math.pi / segments

    def vert(r, z, k):
        ang = k * dtheta
        return (r * math.cos(ang), r * math.sin(ang), z)

    for i in range(npts):
        r0, z0 = pts[i]
        r1, z1 = pts[(i + 1) % npts]
        for k in range(segments):
            a = vert(r0, z0, k)
            b = vert(r0, z0, k + 1)
            c = vert(r1, z1, k + 1)
            d = vert(r1, z1, k)
            n1 = _normal(a, b, c)
            facets.append(_tri(n1, a, b, c))
            n2 = _normal(a, c, d)
            facets.append(_tri(n2, a, c, d))

    body = "".join(facets)
    return f"solid {name}\n{body}endsolid {name}\n"


def grain_stl(grain: Grain, segments: int = 96) -> str:
    """STL of a single grain segment (hollow cylinder for BATES)."""
    ro = grain.outer_radius
    ri = grain.core_radius if grain.grain_type == GrainType.BATES else 0.0
    h = grain.segment_length
    if ri <= 0.0:
        profile = [(0.0, 0.0), (ro, 0.0), (ro, h), (0.0, h)]
    else:
        profile = [(ri, 0.0), (ro, 0.0), (ro, h), (ri, h)]
    return revolve_solid(profile, "grain_segment", segments)


def nozzle_stl(nozzle: Nozzle, gamma: float = 1.2,
               chamber_radius: float | None = None, segments: int = 96) -> str:
    """STL of a conical converging-diverging nozzle (outer shell)."""
    rt = nozzle.throat_diameter / 2.0
    re = rt * math.sqrt(nozzle.expansion_ratio)
    rc = chamber_radius if chamber_radius else rt * 3.0
    wall = max(rt * 0.25, 0.003)

    conv_len = (rc - rt) / math.tan(math.radians(45.0))
    div_len = (re - rt) / math.tan(math.radians(15.0))

    z0, z1, z2 = 0.0, conv_len, conv_len + div_len
    # inner contour (gas side), then outer shell back to start -> closed profile
    inner = [(rc, z0), (rt, z1), (re, z2)]
    outer = [(re + wall, z2), (rt + wall, z1), (rc + wall, z0)]
    profile = inner + outer
    return revolve_solid(profile, "nozzle", segments)


def airframe_stl(body_diameter: float, body_length: float,
                 nose_length: float, segments: int = 96) -> str:
    """STL of a body tube with an ogive-like (here conical) nose cone."""
    r = body_diameter / 2.0
    profile = [
        (0.0, 0.0),
        (r, 0.0),
        (r, body_length),
        (0.0, body_length + nose_length),
    ]
    return revolve_solid(profile, "airframe", segments)


__all__ = ["revolve_solid", "grain_stl", "nozzle_stl", "airframe_stl", "exit_mach"]
