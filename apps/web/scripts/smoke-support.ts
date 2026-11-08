// Process and POC helpers for the desk smoke test. Every failure path rejects
// (never throws from a callback) and kills the child it started, so the smoke
// run always ends with an exit code and leaves no POC or browser behind.
import type {ChildProcess} from "node:child_process";
import {request} from "node:http";

const KILL_GRACE_MS = 2000;

/** Stops `child` and resolves once it has exited (SIGTERM, then SIGKILL after a grace period). */
export function stop(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve();
  return new Promise((done) => {
    const force = setTimeout(() => child.kill("SIGKILL"), KILL_GRACE_MS);
    child.once("exit", () => { clearTimeout(force); done(); });
    child.kill("SIGTERM");
  });
}

/** An error naming the process it stopped, so a caller (or test) can check it is gone. */
export class ChildFailure extends Error {
  readonly pid: number | undefined;
  constructor(message: string, pid: number | undefined) {
    super(message);
    this.name = "ChildFailure";
    this.pid = pid;
  }
}

/** Why: a child that never gets ready must not outlive the smoke run (#1, #2 of the bt-T06 review).
 * What: resolves with the first match of `ready` in the child's stdout/stderr; on timeout,
 * spawn error or early exit it stops the child, waits for its exit, then rejects with ChildFailure.
 * Test: `a child that never prints its ready text is killed and the wait rejects`,
 * `a child that exits before it is ready rejects with its output`. */
export function waitForOutput(child: ChildProcess, ready: RegExp, timeoutMs: number, label: string): Promise<RegExpExecArray> {
  return new Promise((done, failed) => {
    let log = "";
    let settled = false;
    const settle = (finish: () => void): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.stdout?.off("data", read);
      child.stderr?.off("data", read);
      finish();
    };
    const reject = (problem: string): void => settle(() => {
      void stop(child).then(() => failed(new ChildFailure(`${label} ${problem}:\n${log}`, child.pid)));
    });
    const read = (chunk: Buffer): void => {
      log += chunk.toString();
      const found = ready.exec(log);
      if (found) settle(() => done(found));
    };
    const timer = setTimeout(() => reject(`not ready in ${timeoutMs} ms`), timeoutMs);
    child.stdout?.on("data", read);
    child.stderr?.on("data", read);
    child.once("error", (error) => reject(`could not start (${error.message})`));
    // "close", not "exit": it fires after the child's output has been read.
    child.once("close", (code, signal) => reject(`exited (${code ?? signal}) before it was ready`));
  });
}

/** Why: a non-JSON reply must fail the run through `finally`, not crash past it (#5).
 * What: GET (or POST `body`) to the POC on 127.0.0.1:`port` as the POC's own host;
 * resolves with the parsed JSON of a 200 reply, else rejects.
 * Test: `a POC reply that is not JSON rejects instead of throwing`. */
export function pocRequest(port: number, path: string, body?: unknown): Promise<Record<string, any>> {
  return new Promise((done, failed) => {
    const data = body === undefined ? undefined : JSON.stringify(body);
    const req = request({host: "127.0.0.1", port, path, method: data ? "POST" : "GET",
      headers: {Host: `127.0.0.1:${port}`, ...(data ? {"Content-Type": "application/json"} : {})}}, (res) => {
      let text = "";
      res.on("data", (chunk) => { text += chunk; });
      res.on("error", failed);
      res.on("end", () => {
        if (res.statusCode !== 200) return failed(new Error(`${path}: ${res.statusCode} ${text}`));
        try {
          done(JSON.parse(text));
        } catch {
          failed(new Error(`${path}: reply is not JSON: ${text.slice(0, 120)}`));
        }
      });
    });
    req.setTimeout(30000, () => req.destroy(new Error(`${path}: no reply in 30 s`)));
    req.on("error", failed);
    req.end(data);
  });
}
