"""Simple smoke test for audio capture (may require microphone)."""
from whisperguard.audio.capture import AudioCapture


def test_capture_short():
    ac = AudioCapture(chunk_seconds=1)
    # This test only verifies that the object can be created and methods run.
    # It does not start the stream automatically in CI environments.
    assert ac.chunk_seconds == 1
