import { useEffect, useRef } from "react";
import { rememberScroll, scrollFor } from "../../session";

/**
 * Hash navigation does not restore the scroll position: coming Back from a
 * page would land at the top of the grid. So the home remembers where it was
 * scrolled for its address, and goes back there once its grid is on screen
 * (`isReady`); for a new address, it starts at the top.
 */
export function useScrollRestoration(isReady: boolean): void {
  useEffect(() => {
    const remember = () => rememberScroll(window.location.hash, window.scrollY);
    window.addEventListener("scroll", remember, { passive: true });
    return () => window.removeEventListener("scroll", remember);
  }, []);

  // Once per visit of the home: later loads must not move the page.
  const restored = useRef(false);
  useEffect(() => {
    if (!isReady || restored.current) return;
    restored.current = true;
    window.scrollTo(0, scrollFor(window.location.hash));
  }, [isReady]);
}
