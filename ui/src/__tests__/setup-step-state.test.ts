import { describe, expect, it } from "vitest";
import { getSetupStepStates } from "@/routes/setup";

describe("getSetupStepStates", () => {
  it("does not mark later setup steps done just because the user navigated forward", () => {
    const states = getSetupStepStates({
      hasResume: true,
      directionDone: false,
      mastersDone: false,
      experiencesDone: false,
    });

    expect(states).toEqual([
      { n: 1, label: "Resume", done: true },
      { n: 2, label: "Direction", done: false },
      { n: 3, label: "Masters", done: false },
      { n: 4, label: "Experiences", done: false },
      { n: 5, label: "Done", done: false },
    ]);
  });

  it("marks setup steps done only from real completion signals", () => {
    const states = getSetupStepStates({
      hasResume: true,
      directionDone: true,
      mastersDone: true,
      experiencesDone: true,
    });

    expect(states.map((s) => s.done)).toEqual([true, true, true, true, false]);
  });
});

