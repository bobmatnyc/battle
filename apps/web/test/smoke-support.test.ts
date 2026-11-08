// The smoke test's own failure paths: no child process outlives a failure, and nothing hangs.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {chmodSync, mkdtempSync, writeFileSync} from "node:fs";
import {createServer} from "node:http";
import type {AddressInfo} from "node:net";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {test} from "node:test";
import {launch, Page, type SocketLike} from "../scripts/cdp.ts";
import {pocRequest, waitForOutput} from "../scripts/smoke-support.ts";

const alive = (pid: number | undefined): boolean => {
  if (pid === undefined) return false;
  try { process.kill(pid, 0); return true; } catch { return false; }
};

test("a child that never prints its ready text is killed and the wait rejects", {timeout: 10000}, async () => {
  const child = spawn(process.execPath, ["-e", "setInterval(() => {}, 1000)"], {stdio: ["ignore", "pipe", "pipe"]});
  await assert.rejects(waitForOutput(child, /never printed/, 300, "test child"), /test child not ready in 300 ms/);
  assert.equal(alive(child.pid), false);
});

test("a child that exits before it is ready rejects with its output", {timeout: 10000}, async () => {
  const child = spawn(process.execPath, ["-e", "console.log('boom'); process.exit(4)"], {stdio: ["ignore", "pipe", "pipe"]});
  await assert.rejects(waitForOutput(child, /ready/, 5000, "test child"), /exited \(4\)[\s\S]*boom/);
});

test("a browser that gives no DevTools endpoint is killed and launch rejects", {timeout: 10000}, async () => {
  const dir = mkdtempSync(join(tmpdir(), "battle-silent-browser."));
  const binary = join(dir, "browser");
  writeFileSync(binary, "#!/bin/sh\nexec sleep 300\n");
  chmodSync(binary, 0o755);
  let pid: number | undefined;
  await assert.rejects(launch(binary, join(dir, "profile"), process.env, 300).catch((error: Error & {pid?: number}) => {
    pid = error.pid;
    throw error;
  }), /no DevTools endpoint/);
  assert.ok(pid, "the error names the killed process");
  assert.equal(alive(pid), false);
});

class FakeSocket extends EventTarget implements SocketLike {
  sent: string[] = [];
  send(data: string): void { this.sent.push(data); }
  close(): void { this.dispatchEvent(new Event("close")); }
}

test("pending DevTools calls reject when the socket closes, and later calls reject at once", {timeout: 5000}, async () => {
  const socket = new FakeSocket();
  const page = Page.attach(socket, "S1");
  const pending = page.evaluate("1 + 1");
  assert.equal(socket.sent.length, 1);
  socket.dispatchEvent(new Event("close"));
  await assert.rejects(pending, /DevTools connection closed/);
  await assert.rejects(page.send("Page.navigate", {url: "about:blank"}), /DevTools connection closed/);
});

test("a socket error also rejects pending calls", {timeout: 5000}, async () => {
  const socket = new FakeSocket();
  const pending = Page.attach(socket, "S1").send("Runtime.enable");
  socket.dispatchEvent(new Event("error"));
  await assert.rejects(pending, /DevTools connection closed/);
});

test("a POC reply that is not JSON rejects instead of throwing", {timeout: 5000}, async () => {
  const server = createServer((_req, res) => { res.writeHead(200); res.end("<html>not json</html>"); });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    await assert.rejects(pocRequest((server.address() as AddressInfo).port, "/api/state"), /not JSON/);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
