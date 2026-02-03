"""
Centralized progress reporting and event system.

This module provides a unified progress tracking system that can be used
across all components for consistent progress reporting.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ProgressEventType(Enum):
    """Types of progress events."""

    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    STATUS_UPDATE = "status_update"


@dataclass
class ProgressEvent:
    """A progress event containing information about operation progress."""

    operation_id: str
    event_type: ProgressEventType
    current: int = 0
    total: int = 0
    message: str = ""
    percentage: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate percentage if not provided."""
        if self.total > 0 and self.percentage == 0.0:
            self.percentage = (self.current / self.total) * 100.0


class ProgressListener(ABC):
    """Abstract base class for progress listeners."""

    @abstractmethod
    def on_progress(self, event: ProgressEvent):
        """Handle a progress event."""
        pass


class ConsoleProgressListener(ProgressListener):
    """Simple console-based progress listener."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def on_progress(self, event: ProgressEvent):
        """Print progress to console."""
        if not self.verbose:
            return

        if event.event_type == ProgressEventType.STARTED:
            print(f"Started: {event.message}")
        elif event.event_type == ProgressEventType.PROGRESS:
            print(f"Progress: {event.percentage:.1f}% - {event.message}")
        elif event.event_type == ProgressEventType.COMPLETED:
            print(f"Completed: {event.message}")
        elif event.event_type == ProgressEventType.ERROR:
            print(f"Error: {event.message}")
        elif event.event_type == ProgressEventType.STATUS_UPDATE:
            print(f"Status: {event.message}")


class ProgressTracker:
    """Individual progress tracker for a specific operation."""

    def __init__(
        self,
        operation_id: str,
        total: int,
        reporter: 'ProgressReporter',
        description: str = ""
    ):
        self.operation_id = operation_id
        self.total = total
        self.current = 0
        self.reporter = reporter
        self.description = description
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.completed = False
        self.cancelled = False
        self._lock = threading.Lock()

        # Emit started event
        self._emit_event(ProgressEventType.STARTED, self.description)

    def update(self, increment: int = 1, message: str = ""):
        """Update progress by incrementing current value."""
        with self._lock:
            if self.completed or self.cancelled:
                return

            self.current = min(self.current + increment, self.total)
            self.last_update_time = time.time()

            # Calculate rate and ETA
            elapsed = self.last_update_time - self.start_time
            if elapsed > 0 and self.current > 0:
                rate = self.current / elapsed
                if rate > 0 and self.current < self.total:
                    remaining = (self.total - self.current) / rate
                    eta_message = f" (ETA: {remaining:.0f}s)"
                else:
                    eta_message = ""
            else:
                eta_message = ""

            progress_message = message or f"{self.description}{eta_message}"
            self._emit_event(ProgressEventType.PROGRESS, progress_message)

            # Auto-complete if we've reached the total
            if self.current >= self.total:
                self.complete("Operation completed")

    def set_current(self, current: int, message: str = ""):
        """Set current progress to a specific value."""
        with self._lock:
            if self.completed or self.cancelled:
                return

            old_current = self.current
            self.current = max(0, min(current, self.total))

            if self.current != old_current:
                self.last_update_time = time.time()
                progress_message = message or self.description
                self._emit_event(ProgressEventType.PROGRESS, progress_message)

                if self.current >= self.total:
                    self.complete("Operation completed")

    def status_update(self, message: str):
        """Send a status update without changing progress."""
        with self._lock:
            if not self.completed and not self.cancelled:
                self._emit_event(ProgressEventType.STATUS_UPDATE, message)

    def complete(self, message: str = ""):
        """Mark the operation as completed."""
        with self._lock:
            if self.completed or self.cancelled:
                return

            self.completed = True
            self.current = self.total
            completion_message = message or f"{self.description} completed"
            self._emit_event(ProgressEventType.COMPLETED, completion_message)

    def cancel(self, message: str = ""):
        """Cancel the operation."""
        with self._lock:
            if self.completed or self.cancelled:
                return

            self.cancelled = True
            cancel_message = message or f"{self.description} cancelled"
            self._emit_event(ProgressEventType.CANCELLED, cancel_message)

    def error(self, message: str):
        """Report an error for this operation."""
        with self._lock:
            error_message = f"{self.description}: {message}"
            self._emit_event(ProgressEventType.ERROR, error_message)

    def get_rate(self) -> float:
        """Get the current processing rate (items per second)."""
        elapsed = self.last_update_time - self.start_time
        if elapsed > 0 and self.current > 0:
            return self.current / elapsed
        return 0.0

    def get_eta(self) -> Optional[float]:
        """Get estimated time to completion in seconds."""
        rate = self.get_rate()
        if rate > 0 and self.current < self.total:
            return (self.total - self.current) / rate
        return None

    def get_percentage(self) -> float:
        """Get completion percentage."""
        if self.total > 0:
            return (self.current / self.total) * 100.0
        return 0.0

    def _emit_event(self, event_type: ProgressEventType, message: str):
        """Emit a progress event."""
        event = ProgressEvent(
            operation_id=self.operation_id,
            event_type=event_type,
            current=self.current,
            total=self.total,
            message=message,
            percentage=self.get_percentage(),
            metadata={
                'start_time': self.start_time,
                'elapsed': self.last_update_time - self.start_time,
                'rate': self.get_rate(),
                'eta': self.get_eta()
            }
        )
        self.reporter.emit_event(event)


class ProgressReporter:
    """Central progress reporting system."""

    def __init__(self):
        self.listeners: List[ProgressListener] = []
        self.active_operations: Dict[str, ProgressTracker] = {}
        self._lock = threading.Lock()

    def add_listener(self, listener: ProgressListener):
        """Add a progress listener."""
        with self._lock:
            if listener not in self.listeners:
                self.listeners.append(listener)

    def remove_listener(self, listener: ProgressListener):
        """Remove a progress listener."""
        with self._lock:
            if listener in self.listeners:
                self.listeners.remove(listener)

    def create_tracker(
        self,
        operation_id: str,
        total: int,
        description: str = ""
    ) -> ProgressTracker:
        """Create a new progress tracker."""
        with self._lock:
            if operation_id in self.active_operations:
                # Cancel the existing operation
                self.active_operations[operation_id].cancel("Replaced by new operation")

            tracker = ProgressTracker(operation_id, total, self, description)
            self.active_operations[operation_id] = tracker
            return tracker

    def get_tracker(self, operation_id: str) -> Optional[ProgressTracker]:
        """Get an existing tracker by ID."""
        with self._lock:
            return self.active_operations.get(operation_id)

    def remove_tracker(self, operation_id: str):
        """Remove a tracker from active operations."""
        with self._lock:
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]

    def emit_event(self, event: ProgressEvent):
        """Emit a progress event to all listeners."""
        with self._lock:
            for listener in self.listeners:
                try:
                    listener.on_progress(event)
                except Exception as e:
                    logger.error(f"Error in progress listener: {e}")

        # Clean up completed operations
        if event.event_type in (
            ProgressEventType.COMPLETED,
            ProgressEventType.CANCELLED,
            ProgressEventType.ERROR
        ):
            # Don't remove immediately - let it exist for a bit for final status checks
            pass

    def get_all_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active operations."""
        with self._lock:
            result = {}
            for op_id, tracker in self.active_operations.items():
                result[op_id] = {
                    'current': tracker.current,
                    'total': tracker.total,
                    'percentage': tracker.get_percentage(),
                    'rate': tracker.get_rate(),
                    'eta': tracker.get_eta(),
                    'completed': tracker.completed,
                    'cancelled': tracker.cancelled,
                    'description': tracker.description
                }
            return result

    def cancel_all(self):
        """Cancel all active operations."""
        with self._lock:
            for tracker in self.active_operations.values():
                if not tracker.completed and not tracker.cancelled:
                    tracker.cancel("System shutdown")

    def cleanup_completed(self, max_age_seconds: float = 60.0):
        """Remove completed operations older than max_age_seconds."""
        current_time = time.time()
        to_remove = []

        with self._lock:
            for op_id, tracker in self.active_operations.items():
                if (tracker.completed or tracker.cancelled):
                    age = current_time - tracker.last_update_time
                    if age > max_age_seconds:
                        to_remove.append(op_id)

            for op_id in to_remove:
                del self.active_operations[op_id]


# Global progress reporter instance
progress_reporter = ProgressReporter()


# Convenience functions
def create_progress_tracker(operation_id: str, total: int, description: str = "") -> ProgressTracker:
    """Create a new progress tracker."""
    return progress_reporter.create_tracker(operation_id, total, description)


def get_progress_tracker(operation_id: str) -> Optional[ProgressTracker]:
    """Get an existing progress tracker."""
    return progress_reporter.get_tracker(operation_id)


def add_progress_listener(listener: ProgressListener):
    """Add a progress listener to the global reporter."""
    progress_reporter.add_listener(listener)


def remove_progress_listener(listener: ProgressListener):
    """Remove a progress listener from the global reporter."""
    progress_reporter.remove_listener(listener)