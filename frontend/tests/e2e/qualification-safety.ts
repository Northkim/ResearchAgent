import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

export function requireIsolatedQualification(): void {
  const identity = process.env.REAGENT_TEST_DATABASE_IDENTITY;
  if (
    process.env.REAGENT_AUTOMATED_QUALIFICATION !== "1" ||
    !identity ||
    process.env.REAGENT_E2E_QUALIFICATION_IDENTITY !== identity ||
    !process.env.REAGENT_TEST_DATABASE_URL ||
    !process.env.REAGENT_DATABASE_URL
  ) {
    throw new Error(
      "Mutating controlled E2E requires the isolated qualification harness.",
    );
  }
  execFileSync(
    "conda",
    [
      "run",
      "--no-capture-output",
      "-n",
      "reagent-dev",
      "python",
      "-m",
      "backend.database.disposable",
    ],
    {
      cwd: resolve(process.cwd(), ".."),
      env: process.env,
      stdio: "pipe",
    },
  );
}
