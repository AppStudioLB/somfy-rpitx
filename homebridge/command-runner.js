import { execFile } from "node:child_process";

const ALLOWED_ACTIONS = new Set(["up", "down", "stop"]);

export class CommandRunner {
  constructor(options, execFileImplementation = execFile) {
    this.cliPath = options.cliPath;
    this.helperPath = options.helperPath;
    this.configPath = options.configPath;
    this.stateFile = options.stateFile;
    this.useSudo = options.useSudo;
    this.sudoPath = options.sudoPath;
    this.timeoutMs = options.commandTimeoutSeconds * 1000;
    this.execFile = execFileImplementation;
  }

  invocation(action) {
    if (!ALLOWED_ACTIONS.has(action)) {
      throw new TypeError(`unsupported somfy-rpitx action: ${action}`);
    }

    const cliArguments = [
      "--config",
      this.configPath,
      "--state-file",
      this.stateFile,
      action,
    ];
    if (this.useSudo) {
      return {
        executable: this.sudoPath,
        arguments: ["-n", this.helperPath, ...cliArguments],
      };
    }
    return {
      executable: this.cliPath,
      arguments: cliArguments,
    };
  }

  run(action) {
    const { executable, arguments: commandArguments } = this.invocation(action);
    return new Promise((resolve, reject) => {
      this.execFile(
        executable,
        commandArguments,
        {
          encoding: "utf8",
          timeout: this.timeoutMs,
          maxBuffer: 64 * 1024,
          windowsHide: true,
        },
        (error, stdout, stderr) => {
          if (error) {
            const detail = String(stderr || stdout || error.message).trim();
            const wrapped = new Error(
              `somfy-rpitx ${action} failed: ${detail || "unknown error"}`,
              { cause: error },
            );
            reject(wrapped);
            return;
          }
          resolve({
            stdout: String(stdout || "").trim(),
            stderr: String(stderr || "").trim(),
          });
        },
      );
    });
  }
}
