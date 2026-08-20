import { describe, expect, it } from "vitest";

import { sanitizeCommand } from "@/components/copy-command";

describe("sanitizeCommand", () => {
  it("replaces non-breaking spaces and typographic punctuation with plain ASCII", () => {
    expect(
      sanitizeCommand(
        "python\u00a0reagent_local.py\u00a0run\u00a0.\u00a0--workflow\u00a0literature-search-local-experimental",
      ),
    ).toBe("python reagent_local.py run . --workflow literature-search-local-experimental");
    expect(
      sanitizeCommand("python reagent_local.py run . --workflow \u2018idea\u2019 \u2014 ok"),
    ).toBe("python reagent_local.py run . --workflow 'idea' - ok");
    expect(
      sanitizeCommand("  python reagent_local.py sync .  "),
    ).toBe("python reagent_local.py sync .");
  });

  it("keeps already-clean commands unchanged", () => {
    const command = "python reagent_local.py run . --workflow-instance wfi-11111111111111111111111111111111";
    expect(sanitizeCommand(command)).toBe(command);
  });
});
