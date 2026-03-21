"""
WebSocket Client — Driver Safety System.

The server returns a ready-to-display composite image (video + dashboard panel),
so the client only captures frames, sends them, and shows the result.

Protocol:
    Client → Server:  raw JPEG bytes (one frame per message)
    Server → Client:  JSON text (metrics), then JPEG bytes (composite frame)

Usage:
    python -m data_pipeline.client
    python -m data_pipeline.client --url ws://20.219.128.113:5000/stream
    python -m data_pipeline.client --source 1

Press 'x' to quit, 'r' to recalibrate.
"""

import argparse
import asyncio
import json
import sys
import time

import cv2
import numpy as np
import websockets

from utils.logger import get_logger

logger = get_logger(__name__)

CAPTURE_WIDTH = 640
CAPTURE_HEIGHT = 480
SEND_JPEG_QUALITY = 75
# First server frame can take 30–90s on cold start (TF/MediaPipe); keep high enough.
RECV_TIMEOUT = 120.0

_encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), SEND_JPEG_QUALITY]


async def stream(url: str, source, verbose: bool = False):
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        logger.error("Cannot open video source: %s", source)
        sys.exit(1)

    logger.info("Connecting to %s (source=%s)", url, source)

    try:
        ws = await asyncio.wait_for(
            websockets.connect(url, max_size=None), timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.error("Connection timed out — is the server running at %s?", url)
        sys.exit(1)
    except OSError as e:
        logger.error("Cannot connect to %s: %s", url, e)
        sys.exit(1)
    except Exception as e:
        logger.error("WebSocket connection failed: %s", e, exc_info=True)
        sys.exit(1)

    try:
        logger.info("Connected — streaming frames...")
        fps_time = time.time()
        fps_count = 0
        fps_display = 0.0
        frame_i = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            _, buffer = cv2.imencode(".jpg", frame, _encode_params)
            try:
                await ws.send(buffer.tobytes())
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning("Server closed connection during send: %s", e.reason or e.code)
                break

            # Receive metrics JSON (kept for logging / future use)
            try:
                metrics_raw = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
            except asyncio.TimeoutError:
                logger.error("No metrics response (timeout=%.1fs)", RECV_TIMEOUT)
                break
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning("Server closed connection waiting for metrics: %s", e.reason or e.code)
                break
            try:
                metrics = json.loads(metrics_raw)
            except json.JSONDecodeError:
                metrics = {}

            frame_i += 1
            if verbose and (frame_i == 1 or frame_i % 15 == 0):
                logger.info(
                    "metrics sample: driver_state=%s attention=%s ear=%s",
                    metrics.get("driver_state"),
                    metrics.get("attention_state"),
                    metrics.get("ear"),
                )

            # Receive composite JPEG (video + dashboard already composed)
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
            except asyncio.TimeoutError:
                logger.error("No frame response (timeout=%.1fs)", RECV_TIMEOUT)
                break
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning("Server closed connection waiting for frame: %s", e.reason or e.code)
                break

            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                fps_count += 1
                now = time.time()
                elapsed = now - fps_time
                if elapsed >= 1.0:
                    fps_display = fps_count / elapsed
                    fps_count = 0
                    fps_time = now

                cv2.putText(
                    img,
                    f"{fps_display:.0f} FPS",
                    (img.shape[1] - 90, img.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,
                    (120, 125, 130),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Driver Safety System", img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("x"):
                break
            if key == ord("r"):
                logger.info("Recalibration requested by user")
    finally:
        try:
            await ws.close()
        except Exception:
            pass

    cap.release()
    cv2.destroyAllWindows()
    logger.info("Client shutdown complete")


def main():
    parser = argparse.ArgumentParser(description="Driver Safety System — WebSocket client")
    parser.add_argument("--url", default="ws://localhost:5000/stream", help="WebSocket server URL")
    parser.add_argument("--source", default="0", help="Camera index or video file path")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Log server metrics samples (driver_state, etc.)"
    )
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    asyncio.run(stream(args.url, source, verbose=args.verbose))


if __name__ == "__main__":
    main()
