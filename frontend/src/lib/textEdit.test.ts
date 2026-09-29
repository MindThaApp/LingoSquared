import { describe, expect, it } from "vitest";
import { backspaceAtSelection, insertAtSelection } from "./textEdit";

describe("insertAtSelection", () => {
  it("inserts at the end", () => {
    expect(insertAtSelection("ab", 2, 2, "c")).toEqual({ value: "abc", caret: 3 });
  });
  it("inserts mid-string", () => {
    expect(insertAtSelection("ac", 1, 1, "b")).toEqual({ value: "abc", caret: 2 });
  });
  it("replaces a selection", () => {
    expect(insertAtSelection("aXXc", 1, 3, "b")).toEqual({ value: "abc", caret: 2 });
  });
  it("handles reversed and out-of-range indices", () => {
    expect(insertAtSelection("abc", 3, 1, "-")).toEqual({ value: "a-", caret: 2 });
    expect(insertAtSelection("ab", 99, 99, "c")).toEqual({ value: "abc", caret: 3 });
  });
});

describe("backspaceAtSelection", () => {
  it("deletes the char before the caret", () => {
    expect(backspaceAtSelection("abc", 2, 2)).toEqual({ value: "ac", caret: 1 });
  });
  it("deletes a selection", () => {
    expect(backspaceAtSelection("abcd", 1, 3)).toEqual({ value: "ad", caret: 1 });
  });
  it("is a no-op at position 0", () => {
    expect(backspaceAtSelection("abc", 0, 0)).toEqual({ value: "abc", caret: 0 });
  });
  it("deletes a whole surrogate pair", () => {
    expect(backspaceAtSelection("a\u{1F600}b", 3, 3)).toEqual({ value: "ab", caret: 1 });
  });
});
