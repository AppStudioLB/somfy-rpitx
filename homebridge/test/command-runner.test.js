import assert from "node:assert/strict";
import test from "node:test";

import { CommandRunner } from "../command-runner.js";

function options(overrides = {}) {
  return {
    cliPath: "/usr/local/bin/somfy-rpitx",
    helperPath: "/usr/local/bin/somfy-rpitx-homebridge",
    configPath: "/etc/somfy-rpitx/config.json",
    stateFile: "/var/lib/somfy-rpitx/living.json",
    useSudo: true,
    sudoPath: "/usr/bin/sudo",
    commandTimeoutSeconds: 15,
    ...overrides,
  };
}

test("sudo invocation uses fixed argv and no shell", async () => {
  const calls = [];
  const fakeExecFile = (executable, args, execOptions, callback) => {
    calls.push({ executable, args, execOptions });
    callback(null, "sent UP\n", "");
  };
  const runner = new CommandRunner(options(), fakeExecFile);

  const result = await runner.run("up");

  assert.equal(calls[0].executable, "/usr/bin/sudo");
  assert.deepEqual(calls[0].args, [
    "-n",
    "/usr/local/bin/somfy-rpitx-homebridge",
    "--config",
    "/etc/somfy-rpitx/config.json",
    "--state-file",
    "/var/lib/somfy-rpitx/living.json",
    "up",
  ]);
  assert.equal(calls[0].execOptions.shell, undefined);
  assert.equal(calls[0].execOptions.timeout, 15_000);
  assert.equal(result.stdout, "sent UP");
});

test("non-sudo invocation executes the CLI directly", () => {
  const runner = new CommandRunner(options({ useSudo: false }));
  assert.deepEqual(runner.invocation("stop"), {
    executable: "/usr/local/bin/somfy-rpitx",
    arguments: [
      "--config",
      "/etc/somfy-rpitx/config.json",
      "--state-file",
      "/var/lib/somfy-rpitx/living.json",
      "stop",
    ],
  });
});

test("PROG and arbitrary commands are not exposed to HomeKit", () => {
  const runner = new CommandRunner(options());
  assert.throws(() => runner.invocation("prog"), /unsupported/);
  assert.throws(() => runner.invocation("; reboot"), /unsupported/);
});

test("command failures include stderr", async () => {
  const fakeExecFile = (_executable, _args, _options, callback) => {
    callback(new Error("exit 1"), "", "permission denied\n");
  };
  const runner = new CommandRunner(options(), fakeExecFile);
  await assert.rejects(runner.run("down"), /permission denied/);
});
