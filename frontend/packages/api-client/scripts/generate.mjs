// Regenerates src/schema.ts from the backend's API description. Run after any backend API change:
//   npm run generate:api   (from frontend/)
// It imports the FastAPI app directly, so the server does not need to be running.
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const backend = resolve(here, "../../../../backend");
const schemaFile = resolve(here, "../src/schema.ts");

const spec = execFileSync(
  "uv",
  ["run", "python", "-c", "import json; from vb.main import create_app; print(json.dumps(create_app().openapi()))"],
  { cwd: backend, encoding: "utf8" },
);

const ast = await openapiTS(JSON.parse(spec));
const header = "// GENERATED from the backend API by scripts/generate.mjs. Do not edit by hand.\n\n";
writeFileSync(schemaFile, header + astToString(ast));
console.log(`Wrote ${schemaFile}`);
