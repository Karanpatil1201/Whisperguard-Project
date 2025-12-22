"""Minimal CLI entry for WhisperGuard scaffold with end-to-end smoke pipeline.

Wires: AudioCapture -> Ultrasonic detector -> Spectrogram -> CNN placeholder -> Fusion
and prints risk level for each captured chunk.
"""
import argparse
import time

from whisperguard.audio.capture import AudioCapture
from whisperguard.detection.ultrasonic import detect_ultrasonic
from whisperguard.model.spectrogram import waveform_to_log_mel
from whisperguard.model.cnn import CNNSpectrogramClassifier
from whisperguard.fusion import fuse_scores
from whisperguard.response import alert_user, mute_microphone, log_event
from whisperguard.logger import EventLogger


def main():
    parser = argparse.ArgumentParser(description="WhisperGuard smoke pipeline CLI")
    parser.add_argument("--duration", type=int, default=None, help="seconds to capture for smoke test (omit for continuous)")
    parser.add_argument("--continuous", action="store_true", help="run continuously until interrupted")
    parser.add_argument("--sensitivity", type=float, default=0.5, help="0..1 sensitivity")
    parser.add_argument("--system-mute", action="store_true", help="try to mute system microphone when threat detected (platform-dependent)")
    parser.add_argument("--pure", action="store_true", help="pure output mode: print only timestamped status lines")
    args = parser.parse_args()

    ac = AudioCapture(chunk_seconds=1)
    classifier = CNNSpectrogramClassifier()
    logger = EventLogger()

    if not args.pure:
        print("Starting capture pipeline (press Ctrl+C to stop)...")
    ac.start_stream()
    try:
        if args.continuous or args.duration is None:
            t_end = float("inf")
        else:
            t_end = time.time() + args.duration
        while time.time() < t_end:
            chunk = ac.read_chunk(timeout=2.0)
            if chunk is None:
                if not args.pure:
                    print("No audio chunk available")
                continue

            # collapse channels if needed
            if chunk.ndim > 1:
                waveform = chunk.mean(axis=1)
            else:
                waveform = chunk

            rule_ratio, rule_flag = detect_ultrasonic(waveform, ac.samplerate)
            log_mel = waveform_to_log_mel(waveform, sr=ac.samplerate)
            ml_scores = classifier.predict(log_mel, waveform=waveform, sr=ac.samplerate)

            level, score = fuse_scores(rule_ratio, ml_scores, sensitivity=args.sensitivity, whitelist=False)

            # compute RMS and format status line similar to your example
            rms = float((waveform.astype(float) ** 2).mean() ** 0.5)
            low_input = rms < 1e-4
            ts = time.strftime("%H:%M:%S", time.localtime())
            status = level
            if status == "SAFE":
                if low_input:
                    status = "Safe (low input)"
                else:
                    status = "Safe"

            # pure mode: only print the status line
            line = f"{ts} - {status}  RMS:{rms:.6f}"
            print(line)

            if level == "THREAT":
                alert_user(level, "High confidence audio threat detected")
                # Try system mute if requested; otherwise perform app-level mute (stop capture)
                if args.system_mute:
                    try:
                        from whisperguard.response import try_system_mute
                        ok = try_system_mute(5)
                        if not ok:
                            # fallback to app-level mute
                            ac.stop_stream()
                            print("(App) microphone muted for 5 seconds")
                            time.sleep(5)
                            ac.start_stream()
                    except Exception:
                        ac.stop_stream()
                        print("(App) microphone muted for 5 seconds")
                        time.sleep(5)
                        ac.start_stream()
                else:
                    ac.stop_stream()
                    print("(App) microphone muted for 5 seconds")
                    time.sleep(5)
                    ac.start_stream()
                log_event(logger, level, score, fingerprint=None)
            elif level == "SUSPICIOUS":
                alert_user(level, "Suspicious audio detected")
                log_event(logger, level, score)

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        ac.stop_stream()

    if not args.pure:
        print("Logged events:", logger.list())


if __name__ == "__main__":
    main()
