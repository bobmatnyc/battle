// Dependency-free runtime checks for the wire contracts (docs/research/67).
// A check reads `unknown`, returns a typed copy, and throws ContractError
// naming the JSON path of the first bad field, e.g. `$.units[2].side`.

/** A JSON value as the Python app serializes it (`json.dumps`). */
export type JsonValue = null | boolean | number | string | JsonValue[] | {[key: string]: JsonValue};
export type JsonObject = {[key: string]: JsonValue};

/** Why: a caller must know which field broke the contract, not only that one did.
 * What: a TypeError whose `path` is the JSON path of the bad field.
 * Test: `every validator rejects a mutated fixture with the path of the bad field`. */
export class ContractError extends TypeError {
  readonly path: string;
  constructor(path: string, problem: string) {
    super(`${path}: ${problem}`);
    this.name = "ContractError";
    this.path = path;
  }
}

/** Reads `input` at `path`; returns a typed copy or throws ContractError. */
export type Check<T> = (input: unknown, path: string) => T;

function describe(input: unknown): string {
  if (input === null) return "null";
  if (Array.isArray(input)) return "array";
  return typeof input;
}

export function fail(path: string, problem: string): never {
  throw new ContractError(path, problem);
}

export const string: Check<string> = (input, path) =>
  typeof input === "string" ? input : fail(path, `expected string, got ${describe(input)}`);

export const boolean: Check<boolean> = (input, path) =>
  typeof input === "boolean" ? input : fail(path, `expected boolean, got ${describe(input)}`);

export const number: Check<number> = (input, path) =>
  typeof input === "number" && Number.isFinite(input)
    ? input : fail(path, `expected finite number, got ${describe(input)}`);

/** A safe integer; Python `int` (never `bool`, which JSON keeps distinct). */
export const integer: Check<number> = (input, path) =>
  Number.isSafeInteger(input) ? input as number : fail(path, `expected integer, got ${describe(input)}`);

export const count: Check<number> = (input, path) => {
  const value = integer(input, path);
  return value >= 0 ? value : fail(path, `expected integer >= 0, got ${value}`);
};

export function literal<const T extends string | number | null>(...values: T[]): Check<T> {
  return (input, path) => values.includes(input as T)
    ? input as T : fail(path, `expected one of ${JSON.stringify(values)}, got ${JSON.stringify(input)}`);
}

export function nullable<T>(check: Check<T>): Check<T | null> {
  return (input, path) => input === null ? null : check(input, path);
}

export function array<T>(item: Check<T>, bounds: {min?: number; max?: number} = {}): Check<T[]> {
  return (input, path) => {
    if (!Array.isArray(input)) return fail(path, `expected array, got ${describe(input)}`);
    if (bounds.min !== undefined && input.length < bounds.min) fail(path, `expected at least ${bounds.min} items, got ${input.length}`);
    if (bounds.max !== undefined && input.length > bounds.max) fail(path, `expected at most ${bounds.max} items, got ${input.length}`);
    return input.map((value, index) => item(value, `${path}[${index}]`));
  };
}

/** A hex reference `[column, row]`; the grid bounds are a rule, checked by Python. */
export const hex: Check<[number, number]> = (input, path) => {
  const pair = array(count, {min: 2, max: 2})(input, path);
  return [pair[0], pair[1]] as [number, number];
};

function isObject(input: unknown): input is Record<string, unknown> {
  return typeof input === "object" && input !== null && !Array.isArray(input);
}

// An own data property, so a JSON key "__proto__" stays data and never sets a prototype.
function put(target: Record<string, unknown>, key: string, value: unknown): void {
  Object.defineProperty(target, key, {value, enumerable: true, writable: true, configurable: true});
}

/** Any JSON value, deep-copied; used where the contract does not pin the shape. */
export const json: Check<JsonValue> = (input, path) => {
  if (input === null || typeof input === "string" || typeof input === "boolean") return input;
  if (typeof input === "number") return number(input, path);
  if (Array.isArray(input)) return input.map((value, index) => json(value, `${path}[${index}]`));
  if (isObject(input)) return jsonObject(input, path);
  return fail(path, `expected JSON value, got ${describe(input)}`);
};

export const jsonObject: Check<JsonObject> = (input, path) => {
  if (!isObject(input)) return fail(path, `expected object, got ${describe(input)}`);
  const result: JsonObject = {};
  for (const [key, value] of Object.entries(input)) put(result, key, json(value, `${path}.${key}`));
  return result;
};

export function record<T>(value: Check<T>): Check<Record<string, T>> {
  return (input, path) => {
    if (!isObject(input)) return fail(path, `expected object, got ${describe(input)}`);
    const result: Record<string, T> = {};
    for (const [key, item] of Object.entries(input)) put(result, key, value(item, `${path}.${key}`));
    return result;
  };
}

type Shape = Record<string, Check<unknown>>;
type Read<S extends Shape> = {[K in keyof S]: S[K] extends Check<infer T> ? T : never};
export type Shaped<R extends Shape, O extends Shape> = Read<R> & Partial<Read<O>>;

export interface ObjectOptions {
  /** `reject` (default): a key outside `required`/`optional` is an error.
   * `keep`: such a key is copied as plain JSON. */
  readonly rest?: "reject" | "keep";
  /** Keys that must be absent; reported by name (the God-only fields). */
  readonly forbidden?: readonly string[];
}

/** Why: one place enforces required, optional, unknown and forbidden keys.
 * What: an object check copying the declared keys through their checks.
 * Test: `every validator rejects a mutated fixture with the path of the bad field`. */
export function object<R extends Shape, O extends Shape = {}>(
  required: R, optional: O = {} as O, options: ObjectOptions = {},
): Check<Shaped<R, O>> {
  return (input, path) => {
    if (!isObject(input)) return fail(path, `expected object, got ${describe(input)}`);
    for (const key of options.forbidden ?? []) {
      if (Object.hasOwn(input, key)) fail(`${path}.${key}`, "field not allowed in this view");
    }
    const result: Record<string, unknown> = {};
    for (const [key, check] of Object.entries(required)) {
      if (!Object.hasOwn(input, key)) fail(`${path}.${key}`, "required field missing");
      put(result, key, check(input[key], `${path}.${key}`));
    }
    for (const [key, value] of Object.entries(input)) {
      // Own keys only: an input key such as "toString" must not match a prototype member.
      if (Object.hasOwn(required, key)) continue;
      const check = Object.hasOwn(optional, key) ? optional[key] : undefined;
      if (check) put(result, key, check(value, `${path}.${key}`));
      else if (options.rest === "keep") put(result, key, json(value, `${path}.${key}`));
      else fail(`${path}.${key}`, "unknown field");
    }
    return result as Shaped<R, O>;
  };
}

/** Adds a cross-field rule to `check`; `rule` throws through `fail`. */
export function refine<T>(check: Check<T>, rule: (value: T, path: string) => void): Check<T> {
  return (input, path) => {
    const value = check(input, path);
    rule(value, path);
    return value;
  };
}

/** Runs `check` at the root path `$`. */
export function parse<T>(check: Check<T>, input: unknown): T {
  return check(input, "$");
}
