import { useEffect } from "react";
import { driver, type DriveStep } from "driver.js";

type SessionTourOptions = {
  sessionKey: string;
  enabled: boolean;
  steps: DriveStep[];
};

const MAX_RETRIES = 20;
const RETRY_DELAY_MS = 250;

function normalizeSteps(steps: DriveStep[]) {
  return steps.filter((step) => {
    if (!step.element || typeof step.element !== "string") {
      return true;
    }
    return Boolean(document.querySelector(step.element));
  });
}

export function useSessionTour({ sessionKey, enabled, steps }: SessionTourOptions) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    if (typeof window === "undefined") {
      return;
    }

    if (window.sessionStorage.getItem(sessionKey) === "done") {
      return;
    }

    let cancelled = false;
    let retries = 0;

    const tryStart = () => {
      if (cancelled) {
        return;
      }

      const availableSteps = normalizeSteps(steps);
      if (!availableSteps.length) {
        if (retries < MAX_RETRIES) {
          retries += 1;
          window.setTimeout(tryStart, RETRY_DELAY_MS);
        }
        return;
      }

      window.sessionStorage.setItem(sessionKey, "done");
      const tour = driver({
        showProgress: true,
        allowClose: true,
        nextBtnText: "Siguiente",
        prevBtnText: "Anterior",
        doneBtnText: "Listo",
        overlayClickBehavior: "close",
        steps: availableSteps,
      });
      tour.drive();
    };

    const timer = window.setTimeout(tryStart, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [enabled, sessionKey, steps]);
}
