"""Main runtime for motor vibration simulation, detection, and MQTT publishing."""

import signal
import time

from anomaly_detector import AnomalyDetector
from mqtt_client import create_client, publish_alert, publish_data
from vibration_simulator import simulate_stream

RUNNING = True


def handle_shutdown(signum, frame) -> None:
    """Handle SIGINT/SIGTERM and request graceful shutdown."""
    global RUNNING
    RUNNING = False
    print("\nShutdown signal received. Stopping application...")


def build_payload(vibration: float, status: str) -> dict:
    """Construct a normalized sensor payload following project schema."""
    return {
        "timestamp": int(time.time()),
        "sensor_id": "motor_01",
        "vibration": round(vibration, 4),
        "unit": "g",
        "status": status,
    }


def main() -> None:
    """Run the data generation, anomaly detection, and MQTT publish loop."""
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    detector = AnomalyDetector(threshold=0.6, window_size=10)
    client = create_client()
    stream = simulate_stream()

    counter = 0

    try:
        while RUNNING:
            vibration = next(stream)
            status = detector.detect(vibration)
            payload = build_payload(vibration=vibration, status=status)

            publish_data(client, payload)
            if status == "FAULT":
                publish_alert(client, status=status, vibration_value=vibration)

            print(
                f"[{payload['timestamp']}] vibration={payload['vibration']:.4f} "
                f"| status={status}"
            )

            counter += 1
            if counter % 30 == 0:
                stats = detector.get_stats()
                print(
                    "Rolling stats: "
                    f"mean={stats['mean']:.4f}, std={stats['std']:.4f}, "
                    f"threshold={stats['threshold']}, window={stats['window']}"
                )
    except Exception as exc:
        print(f"Runtime error: {exc}")
    finally:
        print("Closing MQTT client...")
        client.loop_stop()
        client.disconnect()
        print("Application stopped.")


if __name__ == "__main__":
    main()
