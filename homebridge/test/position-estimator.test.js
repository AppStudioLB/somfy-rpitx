import assert from "node:assert/strict";
import test from "node:test";

import {
  PositionEstimator,
  PositionStates,
} from "../position-estimator.js";

test("opening position is estimated from configured full travel time", () => {
  let now = 1_000;
  const estimator = new PositionEstimator({
    currentPosition: 20,
    openTimeSeconds: 20,
    closeTimeSeconds: 10,
    now: () => now,
  });

  estimator.start(70);
  assert.equal(estimator.remainingMs(), 10_000);
  assert.equal(estimator.snapshotRaw().state, PositionStates.INCREASING);

  now += 5_000;
  assert.equal(estimator.snapshot().currentPosition, 45);
  now += 5_000;
  assert.deepEqual(estimator.snapshot(), {
    currentPosition: 70,
    targetPosition: 70,
    state: PositionStates.STOPPED,
  });
});

test("closing uses the independently configured close time", () => {
  let now = 0;
  const estimator = new PositionEstimator({
    currentPosition: 100,
    openTimeSeconds: 30,
    closeTimeSeconds: 10,
    now: () => now,
  });
  estimator.start(0);
  now = 2_500;
  assert.deepEqual(estimator.snapshot(), {
    currentPosition: 75,
    targetPosition: 0,
    state: PositionStates.DECREASING,
  });
});

test("stop freezes the estimated position and target", () => {
  let now = 0;
  const estimator = new PositionEstimator({
    currentPosition: 0,
    openTimeSeconds: 20,
    closeTimeSeconds: 20,
    now: () => now,
  });
  estimator.start(100);
  now = 8_000;
  assert.deepEqual(estimator.stop(), {
    currentPosition: 40,
    targetPosition: 40,
    state: PositionStates.STOPPED,
  });
  now = 20_000;
  assert.equal(estimator.snapshot().currentPosition, 40);
});

test("invalid positions are rejected before use", () => {
  assert.throws(
    () =>
      new PositionEstimator({
        currentPosition: Number.NaN,
        openTimeSeconds: 20,
        closeTimeSeconds: 20,
      }),
    /finite number/,
  );
});
