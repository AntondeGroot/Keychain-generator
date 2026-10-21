import pytest

from keychain.spec import KeychainSpec

# The tests are about shapes and colours, not size: half the default width is a quarter of the
# pixels to work through, while a printed line still spans several pixels of the drawings.
SMALL_KEYCHAIN_MM = 25


@pytest.fixture
def spec() -> KeychainSpec:
    return KeychainSpec(width_mm=SMALL_KEYCHAIN_MM)
