import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const helper = path.join(root, "scripts", "parse_cast_uint.py");
const consolidate = path.join(root, "consolidate.sh");

const CRASHING = "4665996001982801717720208990 [4.665e27]";
const CRASHING_INT = 4665996001982801717720208990n;

function runHelper(args, options = {}) {
  return spawnSync("python3", [helper, ...args], {
    encoding: "utf8",
    ...options,
  });
}

function parse(raw) {
  const result = runHelper([raw]);
  assert.equal(
    result.status,
    0,
    result.stderr || `parse failed for ${JSON.stringify(raw)}`,
  );
  return result.stdout.trim();
}

test("parses foundry INTEGER [SCI] annotation without precision loss", () => {
  const decimal = parse(CRASHING);
  assert.equal(decimal, "4665996001982801717720208990");
  assert.equal(BigInt(decimal), CRASHING_INT);
});

test("parses plain integers, whitespace, empty input, and scientific-only tokens", () => {
  assert.equal(parse("0"), "0");
  assert.equal(parse("123"), "123");
  assert.equal(parse(" 123 \n"), "123");
  assert.equal(parse("1.5e3"), "1500");
  assert.equal(parse(""), "0");
});

test("legacy python int() crashes on annotated cast output; helper succeeds", () => {
  const legacy = spawnSync(
    "python3",
    ["-c", "import sys; print(int(sys.argv[1] or 0))", CRASHING],
    { encoding: "utf8" },
  );
  assert.notEqual(legacy.status, 0);
  assert.match(legacy.stderr, /invalid literal for int\(\)/);

  const helperResult = runHelper([CRASHING]);
  assert.equal(helperResult.status, 0, helperResult.stderr);
  assert.equal(helperResult.stdout.trim(), "4665996001982801717720208990");
});

test("never uses IEEE float for wei", () => {
  const source = fs.readFileSync(helper, "utf8");
  assert.doesNotMatch(source, /\bfloat\s*\(/);
  assert.doesNotMatch(source, /int\(\s*float\s*\(/);

  const floatWrong = spawnSync(
    "python3",
    ["-c", 'print(int(float("4665996001982801717720208990")))'],
    { encoding: "utf8" },
  );
  assert.equal(floatWrong.status, 0, floatWrong.stderr);
  assert.notEqual(floatWrong.stdout.trim(), "4665996001982801717720208990");
  assert.equal(parse(CRASHING), "4665996001982801717720208990");
});

test("adds annotated cast uints for --check totaling", () => {
  const result = runHelper(["--add", CRASHING, "10"]);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), "4665996001982801717720209000");
});

test("compares parsed wei without bash 64-bit arithmetic", () => {
  const gt = runHelper(["--gt", CRASHING, "0"]);
  assert.equal(gt.status, 0, gt.stderr);
  assert.equal(gt.stdout.trim(), "1");

  const eq = runHelper(["--gt", "1000000000000", "1000000000000"]);
  assert.equal(eq.status, 0, eq.stderr);
  assert.equal(eq.stdout.trim(), "0");
});

test("consolidate.sh parses every cast uint through the helper", () => {
  const source = fs.readFileSync(consolidate, "utf8");
  assert.match(source, /scripts\/parse_cast_uint\.py/);
  assert.match(source, /parse_cast_uint\(\)/);
  assert.doesNotMatch(source, /int\('\$W_/);
  assert.doesNotMatch(source, /int\(\\?["']\$W_/);
  assert.doesNotMatch(source, /int\(\\?"\$W_/);
  assert.doesNotMatch(source, /int\(\s*["']\$W_/);
  assert.doesNotMatch(source, /\$\(\(\s*TOTAL_\w+\s*\+\s*W_/);
  for (const name of [
    "W_WQFLOP",
    "W_QFLOP",
    "W_ETH",
    "W_WETH",
    "LP_ETH",
    "LP_WQFLOP",
    "LP_WETH",
    "LP_QFLOP",
  ]) {
    assert.match(
      source,
      new RegExp(`${name}=\\$\\(parse_cast_uint`),
      `${name} must be assigned from parse_cast_uint`,
    );
  }
});

test("consolidation remains valid shell syntax", () => {
  const result = spawnSync("bash", ["-n", consolidate], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
});
