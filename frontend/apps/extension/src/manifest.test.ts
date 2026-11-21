// Guards the privacy promises in the manifest (research §7, spec F2): we never read course pages.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const manifest = JSON.parse(readFileSync(new URL("../public/manifest.json", import.meta.url), "utf8"));

// Permissions are added here only together with the feature that needs them (tabCapture, offscreen: slice 1).
const ALLOWED_PERMISSIONS = ["sidePanel", "storage"];

describe("extension manifest", () => {
  it("has no content scripts, so it never reads or changes a web page", () => {
    expect(manifest.content_scripts).toBeUndefined();
  });

  it("asks only for allow-listed permissions", () => {
    for (const permission of manifest.permissions) expect(ALLOWED_PERMISSIONS).toContain(permission);
  });

  it("can only reach our own API", () => {
    expect(manifest.host_permissions).toEqual(["http://localhost:8000/*"]);
  });
});
