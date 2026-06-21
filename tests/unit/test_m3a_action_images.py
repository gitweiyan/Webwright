import numpy as np

from webwright.android_agent.m3a import _action_selection_images


def test_action_selection_images_som_only():
    raw = np.zeros((4, 4, 3), dtype=np.uint8)
    som = np.ones((4, 4, 3), dtype=np.uint8)
    images = _action_selection_images("som_only", raw, som)
    assert len(images) == 1
    assert images[0] is som


def test_action_selection_images_raw_and_som():
    raw = np.zeros((4, 4, 3), dtype=np.uint8)
    som = np.ones((4, 4, 3), dtype=np.uint8)
    images = _action_selection_images("raw_and_som", raw, som)
    assert len(images) == 2
    assert images[0] is raw
    assert images[1] is som
