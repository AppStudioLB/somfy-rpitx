import { SomfyBlindAccessory } from "./accessory.js";
import { CommandRunner } from "./command-runner.js";
import { normalizeConfig } from "./config.js";
import { PLATFORM_NAME, PLUGIN_NAME } from "./settings.js";

export class SomfyRpitxPlatform {
  constructor(log, config, api) {
    this.log = log;
    this.api = api;
    this.Service = api.hap.Service;
    this.Characteristic = api.hap.Characteristic;
    this.accessories = new Map();
    this.handlers = new Map();
    this.configuration = undefined;

    try {
      this.configuration = normalizeConfig(config);
      this.log.debug("Initialized platform %s", this.configuration.name);
    } catch (error) {
      this.log.error("Invalid SomfyRpitx configuration: %s", error.message);
    }

    api.on("didFinishLaunching", () => this.discoverDevices());
    api.on("shutdown", async () => {
      await Promise.allSettled(
        [...this.handlers.values()].map((handler) => handler.destroy()),
      );
    });
  }

  configureAccessory(accessory) {
    this.log.info("Loading cached accessory: %s", accessory.displayName);
    this.accessories.set(accessory.UUID, accessory);
  }

  createCommandRunner(device) {
    return new CommandRunner(device);
  }

  discoverDevices() {
    if (!this.configuration) {
      return;
    }

    const discovered = new Set();
    for (const device of this.configuration.blinds) {
      const uuid = this.api.hap.uuid.generate(`${PLUGIN_NAME}:${device.id}`);
      discovered.add(uuid);
      let accessory = this.accessories.get(uuid);
      if (accessory) {
        this.log.info("Restoring blind: %s", device.name);
        accessory.context.deviceId = device.id;
        this.api.updatePlatformAccessories([accessory]);
      } else {
        this.log.info("Adding blind: %s", device.name);
        accessory = new this.api.platformAccessory(device.name, uuid);
        accessory.context.deviceId = device.id;
        this.api.registerPlatformAccessories(
          PLUGIN_NAME,
          PLATFORM_NAME,
          [accessory],
        );
        this.accessories.set(uuid, accessory);
      }
      this.handlers.set(
        uuid,
        new SomfyBlindAccessory(this, accessory, device),
      );
    }

    for (const [uuid, accessory] of this.accessories) {
      if (!discovered.has(uuid)) {
        this.log.info("Removing stale blind: %s", accessory.displayName);
        this.api.unregisterPlatformAccessories(
          PLUGIN_NAME,
          PLATFORM_NAME,
          [accessory],
        );
        this.accessories.delete(uuid);
      }
    }
  }
}
