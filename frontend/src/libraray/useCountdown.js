import { useEffect, useState } from "react";

/** 32 -> "0:32", 75 -> "1:15" */
export function formatWait(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

/**
 * A countdown in whole seconds.
 *   const { secondsLeft, totalSeconds, start } = useCountdown()
 *   start(32)   // secondsLeft becomes 32, then 31, 30 ... down to 0
 * It compares against the clock, so it stays correct even if the browser slows
 * down timers in a background tab. `totalSeconds` is the length of the last
 * countdown (for a progress bar).
 */
export function useCountdown() {
  const [endsAt, setEndsAt] = useState(0);
  const [now, setNow] = useState(0);
  const [totalSeconds, setTotalSeconds] = useState(0);

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
    setTotalSeconds(seconds);
    setEndsAt(current + seconds * 1000);
  }

  const secondsLeft = endsAt > now ? Math.ceil((endsAt - now) / 1000) : 0;
  return { secondsLeft, totalSeconds, start };
}
