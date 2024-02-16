"""Facilitates communication between processes."""

import multiprocessing as mp
import os
from enum import Enum
from multiprocessing.synchronize import Event as MpEvent
from typing import Optional

import zmq

from frigate.const import PORT_INTER_PROCESS_DETECTIONS


class DetectionTypeEnum(str, Enum):
    all = ""
    video = "video"
    audio = "audio"


class DetectionsPublisher:
    """Publishes video and audio detections."""

    def __init__(self) -> None:
        INTER_PROCESS_DETECTIONS_PORT = (
            os.environ.get("INTER_PROCESS_DETECTIONS_PORT")
            or PORT_INTER_PROCESS_DETECTIONS
        )
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://127.0.0.1:{INTER_PROCESS_DETECTIONS_PORT}")
        self.stop_event: MpEvent = mp.Event()

    def publish(self, topic: DetectionTypeEnum, payload: any) -> None:
        """There is no communication back to the processes."""
        self.socket.send_string(topic.value, flags=zmq.SNDMORE)
        self.socket.send_pyobj(payload)

    def stop(self) -> None:
        self.stop_event.set()
        self.socket.close()
        self.context.destroy()


class ConfigSubscriber:
    """Simplifies receiving video and audio detections."""

    def __init__(self, topic: DetectionTypeEnum) -> None:
        port = (
            os.environ.get("INTER_PROCESS_DETECTIONS_PORT")
            or PORT_INTER_PROCESS_DETECTIONS
        )
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topic.value)
        self.socket.connect(f"tcp://127.0.0.1:{port}")

    def check_for_update(self) -> Optional[tuple[str, any]]:
        """Returns detections or None if no update."""
        try:
            topic = DetectionTypeEnum[self.socket.recv_string(flags=zmq.NOBLOCK)]
            return (topic, self.socket.recv_pyobj())
        except zmq.ZMQError:
            return (None, None)

    def stop(self) -> None:
        self.socket.close()
        self.context.destroy()
