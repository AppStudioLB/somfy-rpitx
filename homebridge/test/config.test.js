import assert from "node:assert/strict";
import test from "node:test";

import { normalizeConfig } from "../config.js";

function validConfig() {
  return {
    name: "Somfy",
    blinds: [
      {
        id: "living-room",
        name: "Living Room",
        configPath: "/etc/somfy-rpitx/config.json",
        stateFile: "/var/lib/somfy-rpitx/state.json",
        openTimeSeconds: 24,
        closeTimeSeconds: 23,
      },
    ],
  };
}

test("configuration applies safe executable defaults", () => {
  const result = normalizeConfig(validConfig());
  assert.equal(result.cliPath, "/usr/local/bin/somfy-rpitx");
  assert.equal(result.sudoPath, "/usr/bin/sudo");
  assert.equal(result.useSudo, true);
  assert.equal(result.blinds[0].initialPosition, 0);
});

test("duplicate IDs are rejected", () => {
  const config = validConfig();
  config.blinds.push({ ...config.blinds[0], name: "Duplicate" });
  assert.throws(() => normalizeConfig(config), /duplicate blind id/);
});

test("relative and unsafe paths are rejected", () => {
  const config = validConfig();
  config.blinds[0].stateFile = "state.json";
  assert.throws(() => normalizeConfig(config), /absolute path/);
});

test("invalid travel time is rejected", () => {
  const config = validConfig();
  config.blinds[0].openTimeSeconds = 0;
  assert.throws(() => normalizeConfig(config), /between 1 and 600/);
});
