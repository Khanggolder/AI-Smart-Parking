from io import BytesIO
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.preprocessing import InputError, TRANSFORM, decode_image, polygon_pixels, preprocess, validate_spots, make_crop


def test_polygon_conversion_crop_and_validation_equivalence():
    image = np.full((80, 120, 3), (0, 50, 200), dtype=np.uint8)
    polygon = [[20/119, 10/79], [70/119, 15/79], [60/119, 65/79], [15/119, 58/79]]
    before = image.copy()
    pixels = polygon_pixels(polygon, 120, 80)
    assert pixels.tolist() == [[20,10], [70,15], [60,65], [15,58]]
    spots = [{"spot_id":"A", "polygon":polygon}]
    actual = preprocess(image, spots)[0]
    expected_bgr = make_crop(image, [pixels], 224, "mask")
    expected = TRANSFORM(Image.fromarray(cv2.cvtColor(expected_bgr, cv2.COLOR_BGR2RGB)))
    assert torch.equal(actual, expected)
    assert (expected_bgr == 114).any()
    assert np.array_equal(image, before)


@pytest.mark.parametrize("polygon", [
    [[0,0],[1,0]], [[0,0],[1,1],[0,1],[1,0]],
    [[0,0],[0,0],[1,1]], [[0,0],[1.1,0],[0,1]],
    [[0,0],[float('nan'),0],[0,1]], [[0,0],[.5,.5],[1,1]],
])
def test_invalid_polygons(polygon):
    with pytest.raises(InputError):
        polygon_pixels(polygon, 120, 80)


def test_image_errors_and_different_resolution():
    with pytest.raises(InputError, match="empty"):
        decode_image(b"", 1000)
    with pytest.raises(InputError):
        decode_image(b"not an image", 1000)
    im = Image.new("RGB", (40, 30), "white")
    buffer = BytesIO()
    im.save(buffer, format="PNG")
    assert decode_image(buffer.getvalue(), 1200).shape == (30,40,3)
    with pytest.raises(InputError):
        decode_image(buffer.getvalue(), 1199)
    assert polygon_pixels([[0,0],[1,0],[1,1],[0,1]],40,30).tolist() == [[0,0],[39,0],[39,29],[0,29]]


def test_spot_counts_and_duplicate_ids():
    with pytest.raises(InputError):
        validate_spots([], 100)
    with pytest.raises(InputError) as exc:
        validate_spots([{"spot_id":"A","polygon":[]}] * 2, 100)
    assert exc.value.code == "DUPLICATE_SPOT_ID"
    with pytest.raises(InputError):
        validate_spots([{"spot_id":str(i),"polygon":[]} for i in range(101)], 100)
