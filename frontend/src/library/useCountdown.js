import { useEffect, useState } from "react";

/**
 * A countdown in whole seconds.
 *   const { secondsLeft, start } = useCountdown()
 *   start(32)   // secondsLeft becomes 32, then 31, 30 ... down to 0
 * It compares against the clock, so it stays correct even if the browser slows
 * down timers in a background tab.
 */
export function useCountdown() {
  const [endsAt, setEndsAt] = useState(0);
  const [now, setNow] = useState(0);

  useEffect(() => {
    if (!endsAt) return undefined;
    const timer = setInterval(() => {
      const current = Date.now();
      setNow(current);
      if (current >= endsAt) clearInterval(timer);
    }, 250);
    return () => clearInterval(timer);
  }, [endsAt]);

  function start(seconds) {
    const current = Date.now();
    setNow(current);
    setEndsAt(current + seconds * 1000);
  }

  const secondsLeft = endsAt > now ? Math.ceil((endsAt - now) / 1000) : 0;
  return { secondsLeft, start };
}
