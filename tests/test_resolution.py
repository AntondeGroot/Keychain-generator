from keychain.picture.resolution import Resolution


def test_a_picture_with_too_few_pixels_for_its_size_gets_a_warning_with_the_size_to_aim_for():
    # CatDog: 360 pixels high, printed 75 mm high, so each pixel is about 0.21 mm.
    assert "at least 500 pixels" in Resolution(75, 75 / 360).warning()
    assert Resolution(30, 30 / 360).warning() is None  # the same picture, smaller: 0.08 mm a pixel
