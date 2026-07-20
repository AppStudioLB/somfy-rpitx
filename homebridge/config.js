import path from "node:path";

const DEFAULTS = Object.freeze({
  cliPath: "/usr/local/bin/somfy-rpitx",
  sudoPath: "/usr/bin/sudo",
  useSudo: true,
  commandTimeoutSeconds: 15,
});

function requiredString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TypeError(`${field} must be a non-empty string`);
  }
  return value;
}

function absolutePath(value, field) {
  const result = requiredString(value, field);
  if (!path.isAbsolute(result)) {
    throw new TypeError(`${field} must be an absolute path`);
  }
  return result;
}

function numberInRange(value, field, minimum, maximum) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    throw new TypeError(`${field} must be between ${minimum} and ${maximum}`);
  }
  return number;
}

export function normalizeConfig(config) {
  if (!config || typeof config !== "object") {
    throw new TypeError("platform configuration is required");
  }
  if (!Array.isArray(config.blinds) || config.blinds.length === 0) {
    throw new TypeError("blinds must contain at least one blind");
  }

  const globalOptions = {
    name: requiredString(config.name || "Somfy rpitx", "name"),
    cliPath: absolutePath(
      config.cliPath || DEFAULTS.cliPath,
      "cliPath",
    ),
    sudoPath: absolutePath(
      config.sudoPath || DEFAULTS.sudoPath,
      "sudoPath",
    ),
    useSudo:
      config.useSudo === undefined ? DEFAULTS.useSudo : config.useSudo,
    commandTimeoutSeconds: numberInRange(
      config.commandTimeoutSeconds ?? DEFAULTS.commandTimeoutSeconds,
      "commandTimeoutSeconds",
      1,
      60,
    ),
  };
  if (typeof globalOptions.useSudo !== "boolean") {
    throw new TypeError("useSudo must be true or false");
  }

  const identifiers = new Set();
  const blinds = config.blinds.map((blind, index) => {
    if (!blind || typeof blind !== "object") {
      throw new TypeError(`blinds[${index}] must be an object`);
    }
    const id = requiredString(blind.id, `blinds[${index}].id`);
    if (!/^[A-Za-z0-9._-]+$/.test(id)) {
      throw new TypeError(
        `blinds[${index}].id may contain only letters, digits, '.', '_' and '-'`,
      );
    }
    if (identifiers.has(id)) {
      throw new TypeError(`duplicate blind id: ${id}`);
    }
    identifiers.add(id);

    return {
      ...globalOptions,
      id,
      name: requiredString(blind.name, `blinds[${index}].name`),
      configPath: absolutePath(
        blind.configPath,
        `blinds[${index}].configPath`,
      ),
      stateFile: absolutePath(
        blind.stateFile,
        `blinds[${index}].stateFile`,
      ),
      openTimeSeconds: numberInRange(
        blind.openTimeSeconds,
        `blinds[${index}].openTimeSeconds`,
        1,
        600,
      ),
      closeTimeSeconds: numberInRange(
        blind.closeTimeSeconds,
        `blinds[${index}].closeTimeSeconds`,
        1,
        600,
      ),
      initialPosition: numberInRange(
        blind.initialPosition ?? 0,
        `blinds[${index}].initialPosition`,
        0,
        100,
      ),
    };
  });

  return { ...globalOptions, blinds };
}
