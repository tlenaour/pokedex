/**
 * jsdom, but keeping Node's AbortController / AbortSignal.
 *
 * jsdom replaces them with its own implementation, which Node's fetch rejects
 * ("Expected signal to be an instance of AbortSignal"): every request made
 * with an AbortSignal (TanStack Query cancels outdated requests that way)
 * would fail in tests. A browser has a single, consistent implementation, so
 * this only concerns the test environment.
 */
import type { Environment } from "vitest/environments";
import { builtinEnvironments } from "vitest/environments";

export default {
  name: "jsdom-node-abort",
  transformMode: "web",
  async setup(global, options) {
    const { AbortController, AbortSignal } = global;
    const jsdom = await builtinEnvironments.jsdom.setup(global, options);
    global.AbortController = AbortController;
    global.AbortSignal = AbortSignal;
    return jsdom;
  },
} satisfies Environment;
