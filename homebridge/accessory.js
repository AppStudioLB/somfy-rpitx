import { PositionEstimator, PositionStates } from "./position-estimator.js";

export class SomfyBlindAccessory {
  constructor(platform, accessory, device) {
    this.platform = platform;
    this.accessory = accessory;
    this.device = device;
    this.log = platform.log;
    this.Service = platform.Service;
    this.Characteristic = platform.Characteristic;
    this.runner = platform.createCommandRunner(device);
    this.queue = Promise.resolve();
    this.updateTimer = undefined;
    this.finishTimer = undefined;
    this.movementGeneration = 0;

    const restoredPosition = Number.isFinite(accessory.context.currentPosition)
      ? accessory.context.currentPosition
      : device.initialPosition;
    this.estimator = new PositionEstimator({
      currentPosition: restoredPosition,
      openTimeSeconds: device.openTimeSeconds,
      closeTimeSeconds: device.closeTimeSeconds,
    });

    accessory.context.deviceId = device.id;
    accessory.context.currentPosition = Math.round(restoredPosition);
    accessory.on("identify", () => {
      this.log.info("Identify requested for %s", device.name);
    });

    this.informationService =
      accessory.getService(this.Service.AccessoryInformation) ||
      accessory.addService(this.Service.AccessoryInformation);
    this.informationService
      .setCharacteristic(this.Characteristic.Manufacturer, "Somfy / rpitx")
      .setCharacteristic(this.Characteristic.Model, "447 JOO RTS virtual remote")
      .setCharacteristic(this.Characteristic.SerialNumber, device.id)
      .setCharacteristic(this.Characteristic.FirmwareRevision, "0.3.0");

    this.service =
      accessory.getService(this.Service.WindowCovering) ||
      accessory.addService(this.Service.WindowCovering, device.name);

    this.service
      .getCharacteristic(this.Characteristic.CurrentPosition)
      .onGet(() => this.estimator.snapshot().currentPosition);
    this.service
      .getCharacteristic(this.Characteristic.TargetPosition)
      .onGet(() => this.estimator.snapshot().targetPosition)
      .onSet((value) => this.setTargetPosition(Number(value)));
    this.service
      .getCharacteristic(this.Characteristic.PositionState)
      .onGet(() => this.homeKitPositionState());
    this.service
      .getCharacteristic(this.Characteristic.HoldPosition)
      .onSet((value) => (value ? this.holdPosition() : undefined));
    this.service
      .getCharacteristic(this.Characteristic.ObstructionDetected)
      .onGet(() => false);

    this.updateCharacteristics();
  }

  setTargetPosition(targetPosition) {
    if (!Number.isFinite(targetPosition)) {
      return Promise.reject(new TypeError("target position must be a number"));
    }
    return this.enqueue(async () => {
      this.estimator.sample();
      const previous = this.estimator.snapshotRaw();
      if (this.estimator.isMoving()) {
        try {
          await this.runner.run("stop");
        } catch (error) {
          this.log.error("%s", error.message);
          throw error;
        }
        this.estimator.stop();
        this.clearMovementTimers();
      }

      const current = this.estimator.snapshotRaw().currentPosition;
      const target = Math.min(100, Math.max(0, Math.round(targetPosition)));
      if (target === current) {
        this.estimator.stop();
        this.updateCharacteristics();
        this.persistPosition();
        return;
      }

      const action = target > current ? "up" : "down";
      this.log.info(
        "%s: %s from %d%% to %d%%",
        this.device.name,
        action.toUpperCase(),
        current,
        target,
      );
      try {
        await this.runner.run(action);
      } catch (error) {
        this.estimator.stop();
        this.updateCharacteristics();
        this.log.error("%s", error.message);
        throw error;
      }

      this.estimator.start(target);
      this.updateCharacteristics();
      this.startMovementTimers();
      this.log.debug(
        "%s movement started; previous state was %s",
        this.device.name,
        previous.state,
      );
    });
  }

  holdPosition() {
    return this.enqueue(async () => {
      if (!this.estimator.isMoving()) {
        return;
      }
      this.estimator.sample();
      try {
        await this.runner.run("stop");
      } catch (error) {
        this.log.error("%s", error.message);
        throw error;
      } finally {
        this.estimator.stop();
        this.clearMovementTimers();
        this.updateCharacteristics();
        this.persistPosition();
      }
      this.log.info(
        "%s: STOP at approximately %d%%",
        this.device.name,
        this.estimator.snapshotRaw().currentPosition,
      );
    });
  }

  startMovementTimers() {
    this.clearMovementTimers();
    const generation = ++this.movementGeneration;
    this.updateTimer = setInterval(() => {
      if (generation !== this.movementGeneration) {
        return;
      }
      this.estimator.sample();
      this.updateCharacteristics();
    }, 500);

    const remainingMs = this.estimator.remainingMs();
    this.finishTimer = setTimeout(() => {
      this.enqueue(() => this.finishMovement(generation)).catch((error) => {
        this.log.error("%s", error.message);
      });
    }, Math.max(1, remainingMs));
  }

  async finishMovement(generation) {
    if (generation !== this.movementGeneration) {
      return;
    }
    const target = this.estimator.snapshotRaw().targetPosition;
    this.estimator.sample();
    let stopError;
    if (target > 0 && target < 100) {
      try {
        await this.runner.run("stop");
      } catch (error) {
        stopError = error;
      }
    }
    this.estimator.sample(Date.now() + this.estimator.remainingMs());
    this.clearMovementTimers();
    this.updateCharacteristics();
    this.persistPosition();
    this.log.info(
      "%s: reached approximately %d%%",
      this.device.name,
      this.estimator.snapshotRaw().currentPosition,
    );
    if (stopError) {
      throw stopError;
    }
  }

  homeKitPositionState() {
    const state = this.estimator.snapshot().state;
    if (state === PositionStates.INCREASING) {
      return this.Characteristic.PositionState.INCREASING;
    }
    if (state === PositionStates.DECREASING) {
      return this.Characteristic.PositionState.DECREASING;
    }
    return this.Characteristic.PositionState.STOPPED;
  }

  updateCharacteristics() {
    const snapshot = this.estimator.snapshot();
    this.service.updateCharacteristic(
      this.Characteristic.CurrentPosition,
      snapshot.currentPosition,
    );
    this.service.updateCharacteristic(
      this.Characteristic.TargetPosition,
      snapshot.targetPosition,
    );
    this.service.updateCharacteristic(
      this.Characteristic.PositionState,
      this.homeKitPositionState(),
    );
    this.service.updateCharacteristic(
      this.Characteristic.ObstructionDetected,
      false,
    );
  }

  persistPosition() {
    this.accessory.context.currentPosition =
      this.estimator.snapshotRaw().currentPosition;
    this.platform.api.updatePlatformAccessories([this.accessory]);
  }

  clearMovementTimers() {
    ++this.movementGeneration;
    if (this.updateTimer !== undefined) {
      clearInterval(this.updateTimer);
      this.updateTimer = undefined;
    }
    if (this.finishTimer !== undefined) {
      clearTimeout(this.finishTimer);
      this.finishTimer = undefined;
    }
  }

  enqueue(operation) {
    const result = this.queue.then(operation, operation);
    this.queue = result.catch(() => undefined);
    return result;
  }

  async destroy() {
    if (this.estimator.isMoving()) {
      this.estimator.sample();
      try {
        await this.runner.run("stop");
      } catch (error) {
        this.log.error(
          "%s: failed to stop during Homebridge shutdown: %s",
          this.device.name,
          error.message,
        );
      }
      this.estimator.stop();
      this.updateCharacteristics();
      this.persistPosition();
    }
    this.clearMovementTimers();
  }
}
