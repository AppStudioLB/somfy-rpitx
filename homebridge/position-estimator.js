const STOPPED = "stopped";
const INCREASING = "increasing";
const DECREASING = "decreasing";

function clampPosition(value) {
  if (!Number.isFinite(value)) {
    throw new TypeError("position must be a finite number");
  }
  return Math.min(100, Math.max(0, value));
}

export class PositionEstimator {
  constructor({
    currentPosition,
    openTimeSeconds,
    closeTimeSeconds,
    now = () => Date.now(),
  }) {
    this.now = now;
    this.openTimeMs = openTimeSeconds * 1000;
    this.closeTimeMs = closeTimeSeconds * 1000;
    this.currentPosition = clampPosition(currentPosition);
    this.targetPosition = this.currentPosition;
    this.state = STOPPED;
    this.startedAt = 0;
    this.startPosition = this.currentPosition;
    this.durationMs = 0;
  }

  start(targetPosition, startedAt = this.now()) {
    this.sample(startedAt);
    const target = clampPosition(targetPosition);
    const distance = target - this.currentPosition;
    this.targetPosition = target;
    this.startPosition = this.currentPosition;
    this.startedAt = startedAt;

    if (Math.abs(distance) < 0.001) {
      this.currentPosition = target;
      this.state = STOPPED;
      this.durationMs = 0;
      return this.snapshot(startedAt);
    }

    this.state = distance > 0 ? INCREASING : DECREASING;
    const fullTravelMs = distance > 0 ? this.openTimeMs : this.closeTimeMs;
    this.durationMs = (Math.abs(distance) / 100) * fullTravelMs;
    return this.snapshot(startedAt);
  }

  sample(at = this.now()) {
    if (this.state === STOPPED) {
      return this.snapshotRaw();
    }

    const elapsed = Math.max(0, at - this.startedAt);
    const progress =
      this.durationMs === 0 ? 1 : Math.min(1, elapsed / this.durationMs);
    this.currentPosition =
      this.startPosition +
      (this.targetPosition - this.startPosition) * progress;

    if (progress >= 1) {
      this.currentPosition = this.targetPosition;
      this.state = STOPPED;
      this.durationMs = 0;
    }
    return this.snapshotRaw();
  }

  stop(at = this.now()) {
    this.sample(at);
    this.targetPosition = this.currentPosition;
    this.state = STOPPED;
    this.durationMs = 0;
    return this.snapshotRaw();
  }

  remainingMs(at = this.now()) {
    if (this.state === STOPPED) {
      return 0;
    }
    return Math.max(0, this.durationMs - Math.max(0, at - this.startedAt));
  }

  isMoving() {
    return this.state !== STOPPED;
  }

  snapshot(at = this.now()) {
    this.sample(at);
    return this.snapshotRaw();
  }

  snapshotRaw() {
    return {
      currentPosition: Math.round(clampPosition(this.currentPosition)),
      targetPosition: Math.round(clampPosition(this.targetPosition)),
      state: this.state,
    };
  }
}

export const PositionStates = Object.freeze({
  STOPPED,
  INCREASING,
  DECREASING,
});
