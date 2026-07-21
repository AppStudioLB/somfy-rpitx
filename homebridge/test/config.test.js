import assert from "node:assert/strict";
import fs from "node:fs";
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
  assert.equal(result.configPath, "/etc/somfy-rpitx/config.json");
  assert.equal(result.stateDirectory, "/var/lib/somfy-rpitx");
  assert.equal(result.blinds[0].remoteType, "individual");
  assert.equal(result.blinds[0].initialPosition, 0);
});

test("simple UI configuration derives per-remote paths", () => {
  const result = normalizeConfig({
    name: "Somfy",
    configPath: "/etc/somfy-rpitx/shared.json",
    stateDirectory: "/var/lib/somfy-rpitx/remotes",
    blinds: [
      {
        id: "blind-1",
        name: "Blind 1",
        openTimeSeconds: 25,
        closeTimeSeconds: 25,
      },
      {
        id: "all-blinds",
        name: "All Blinds",
        remoteType: "group",
        openTimeSeconds: 25,
        closeTimeSeconds: 25,
      },
    ],
  });

  assert.equal(result.blinds[0].configPath, "/etc/somfy-rpitx/shared.json");
  assert.equal(
    result.blinds[0].stateFile,
    "/var/lib/somfy-rpitx/remotes/blind-1.json",
  );
  assert.equal(result.blinds[1].remoteType, "group");
  assert.equal(
    result.blinds[1].stateFile,
    "/var/lib/somfy-rpitx/remotes/all-blinds.json",
  );
});

test("Homebridge UI starter configuration is immediately valid", () => {
  const schema = JSON.parse(
    fs.readFileSync(new URL("../../config.schema.json", import.meta.url)),
  );
  const starterConfig = {
    name: schema.schema.properties.name.default,
    configPath: schema.schema.properties.configPath.default,
    stateDirectory: schema.schema.properties.stateDirectory.default,
    blinds: schema.schema.properties.blinds.default,
  };
  const result = normalizeConfig(starterConfig);

  assert.deepEqual(
    result.blinds.map(({ id, remoteType }) => ({ id, remoteType })),
    [
      { id: "blind-1", remoteType: "individual" },
      { id: "blind-2", remoteType: "individual" },
      { id: "blind-3", remoteType: "individual" },
      { id: "all-blinds", remoteType: "group" },
    ],
  );
  assert.equal(
    new Set(result.blinds.map((blind) => blind.stateFile)).size,
    result.blinds.length,
  );
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

test("duplicate rolling-code state files are rejected", () => {
  const config = validConfig();
  config.blinds.push({
    ...config.blinds[0],
    id: "bedroom",
    name: "Bedroom",
  });
  assert.throws(
    () => normalizeConfig(config),
    /duplicate rolling-code state file/,
  );
});

test("unknown remote types are rejected", () => {
  const config = validConfig();
  config.blinds[0].remoteType = "broadcast";
  assert.throws(() => normalizeConfig(config), /remoteType/);
});

test("invalid travel time is rejected", () => {
  const config = validConfig();
  config.blinds[0].openTimeSeconds = 0;
  assert.throws(() => normalizeConfig(config), /between 1 and 600/);
});
