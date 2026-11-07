import pytest

from conceptdesign import geometry as g


def test_union_area_counts_overlaps_once():
    assert g.union_area([(0, 0, 4, 4), (2, 2, 6, 6)]) == pytest.approx(28.0)


def test_rect_minus_leaves_disjoint_pieces():
    pieces = g.rect_minus((0, 0, 4, 4), [(1, 1, 2, 2)])
    assert sum(g.area(p) for p in pieces) == pytest.approx(15.0)
    assert g.union_area(pieces) == pytest.approx(15.0)


def test_split_rect_cuts_openings_out_of_a_wall():
    assert g.split_rect((0, 0, 5, 0.3), [(1, 0, 2, 0.3), (3, -1, 3.5, 1)]) == [
        (0, 0, 1, 0.3), (2, 0, 3, 0.3), (3.5, 0, 5, 0.3)]


@pytest.mark.parametrize("footprint", [
    [(0, 0, 11.4, 7.2)],                                  # rectangle
    [(0, 0, 10, 5), (0, 5, 5, 10)],                       # L-shape: one inside corner
    [(0, 0, 12, 4), (0, 4, 4, 10), (8, 4, 12, 10)],       # U-shape: two inside corners
])
def test_exterior_walls_meet_without_gaps_or_overlaps(footprint):
    t = 0.3
    walls = [w for w, _side in g.exterior_walls(footprint, t)]
    assert sum(g.area(w) for w in walls) == pytest.approx(g.union_area(walls))   # no overlaps
    for w in walls:
        assert all(g.in_union(footprint, p) for p in ((w[0], w[1]), (w[2], w[3])))
    # every point just inside the outline is wall, every point deeper in is not
    for side, fixed, a, b in g.outline_edges(footprint):
        mid = (a + b) / 2
        inward = {"N": (mid, fixed - t / 2), "S": (mid, fixed + t / 2),
                  "E": (fixed - t / 2, mid), "W": (fixed + t / 2, mid)}[side]
        assert any(g.contains(w, inward) for w in walls)


def test_outline_edges_face_outwards():
    sides = sorted(side for side, *_ in g.outline_edges([(0, 0, 10, 5), (0, 5, 5, 10)]))
    assert sides == ["E", "E", "N", "N", "S", "W"]


def test_distance_rect_segment():
    assert g.distance_rect_segment((3, 3, 5, 5), (0, 0), (10, 0)) == pytest.approx(3.0)
