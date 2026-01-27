// src/utils/activityTracker.js
// Singleton activity tracker: user events + optional API activity.
// - Logs out after 30 min of inactivity (no user events AND no API activity).
// - Every 5 min: if there was activity since last ping, sends a ping.
// - DOM activity is sampled: record once, then detach listeners for 5 minutes (super low overhead).

const DEFAULTS = {
  inactivityMs: 30 * 60 * 1000,        // 30 minutes
  pingIntervalMs: 5 * 60 * 1000,       // ping decision window
  idleCheckMs: 30 * 1000,              // check idle every 30s (accurate logout timing)

  // NEW: reduce client load
  eventCooldownMs: 5 * 60 * 1000,      // record DOM activity at most once per 5 min
  detachListenersDuringCooldown: true, // after first DOM event, detach listeners for eventCooldownMs

  // still used if detachListenersDuringCooldown is false
  mousemoveThrottleMs: 5000,           // treat mousemove as activity at most once/5s

  debug: false,
};

const state = {
  started: false,
  listenersAttached: false,
  idleTimerId: null,

  // activity timestamps
  lastUserAt: 0,
  lastApiAt: 0,

  // ping control
  lastPingAt: 0,
  activitySinceLastPing: false,

  // throttled logs
  lastActivityLogAt: 0,

  // config + callbacks
  cfg: { ...DEFAULTS },
  getToken: null,
  pingFn: null,
  onLogout: null,

  // listener refs
  handlers: null,

  // cooldown
  userCooldownUntil: 0,
  cooldownReattachId: null,
};

function nowMs() {
  return Date.now();
}

function maxActivityAt() {
  return Math.max(state.lastUserAt || 0, state.lastApiAt || 0);
}

function dbg(...args) {
  if (!state.cfg.debug) return;
  console.log("[ActivityTracker]", ...args);
}

function inUserCooldown() {
  return nowMs() < (state.userCooldownUntil || 0);
}

function enterUserCooldown() {
  const t = nowMs();
  state.userCooldownUntil = t + state.cfg.eventCooldownMs;

  dbg("user event cooldown entered", {
    cooldownMs: state.cfg.eventCooldownMs,
    until: new Date(state.userCooldownUntil).toLocaleTimeString(),
    detach: !!state.cfg.detachListenersDuringCooldown,
  });

  if (!state.cfg.detachListenersDuringCooldown) return;

  // detach listeners to truly reduce overhead
  detachListeners();

  // schedule reattach
  if (state.cooldownReattachId) {
    window.clearTimeout(state.cooldownReattachId);
    state.cooldownReattachId = null;
  }

  state.cooldownReattachId = window.setTimeout(() => {
    state.cooldownReattachId = null;
    if (!state.started) return; // safety: don't reattach after stop()
    attachListeners();
    dbg("user event cooldown ended → listeners reattached");
  }, Math.max(0, state.userCooldownUntil - nowMs()));
}

function setUserActivity(kind = "event") {
  const t = nowMs();
  state.lastUserAt = t;
  state.activitySinceLastPing = true;

  // log only occasionally (avoid spam)
  if (state.cfg.debug && t - state.lastActivityLogAt > 5000) {
    state.lastActivityLogAt = t;
    dbg(`user activity recorded (${kind})`);
  }
}

function setApiActivity(kind = "api") {
  const t = nowMs();
  state.lastApiAt = t;
  state.activitySinceLastPing = true;

  if (state.cfg.debug && t - state.lastActivityLogAt > 5000) {
    state.lastActivityLogAt = t;
    dbg(`api activity detected (${kind})`);
  }
}

function handleUserEvent(kind, eType) {
  // If we're in cooldown, do nothing (no logs, minimal work)
  if (inUserCooldown()) return;

  // Record activity once per cooldown window
  setUserActivity(kind || eType || "dom");

  // After first activity, enter cooldown (optionally detaching listeners)
  if (state.cfg.eventCooldownMs > 0) {
    enterUserCooldown();
  }
}

async function maybePing() {
  const token = state.getToken ? state.getToken() : null;
  if (!token) return; // not logged in

  const t = nowMs();
  const due = (t - (state.lastPingAt || 0)) >= state.cfg.pingIntervalMs;
  if (!due) return;

  if (!state.activitySinceLastPing) {
    state.lastPingAt = t; // move window forward
    dbg("ping skipped (no activity since last window)");
    return;
  }

  state.lastPingAt = t;
  state.activitySinceLastPing = false;

  dbg("pinging server (activity detected in last window)...");
  try {
    await state.pingFn(token);
    dbg("ping success");
  } catch (e) {
    const status = e?.response?.status;
    dbg("ping failed", status || "", e?.message || e);

    if (status === 401) {
      if (typeof state.onLogout === "function") {
        state.onLogout("Session expired. Please log in again.");
      }
    }
  }
}

function checkIdleAndLogout() {
  const token = state.getToken ? state.getToken() : null;
  if (!token) return;

  const t = nowMs();
  const idleFor = t - maxActivityAt();

  if (idleFor >= state.cfg.inactivityMs) {
    dbg(`idle timeout reached (${Math.round(idleFor / 1000)}s) → logout`);
    if (typeof state.onLogout === "function") {
      state.onLogout("Logged out after 30 minutes of inactivity.");
    }
  }
}

function tick() {
  checkIdleAndLogout();
  maybePing();
}

function ensureHandlers() {
  if (state.handlers) return;

  let lastMouseAt = 0;

  state.handlers = {
    onGeneric: (e) => handleUserEvent("generic", e?.type),
    onMouseMove: (e) => {
      // If we are *not* detaching listeners during cooldown, keep mousemove extra-throttled
      if (!state.cfg.detachListenersDuringCooldown) {
        const t = nowMs();
        if (t - lastMouseAt < state.cfg.mousemoveThrottleMs) return;
        lastMouseAt = t;
      }
      handleUserEvent("mousemove", e?.type);
    },
    onVisibility: () => {
      if (document.visibilityState === "visible") {
        handleUserEvent("visible", "visibilitychange");
      }
    },
    onInputCapture: (e) => handleUserEvent("input", e?.type),
    onChangeCapture: (e) => handleUserEvent("change", e?.type),
  };
}

function addListeners() {
  ensureHandlers();

  // window-level events
  window.addEventListener("click", state.handlers.onGeneric, { passive: true });
  window.addEventListener("keydown", state.handlers.onGeneric, { passive: true });
  window.addEventListener("scroll", state.handlers.onGeneric, { passive: true });
  window.addEventListener("touchstart", state.handlers.onGeneric, { passive: true });
  window.addEventListener("pointerdown", state.handlers.onGeneric, { passive: true });
  window.addEventListener("wheel", state.handlers.onGeneric, { passive: true });
  window.addEventListener("focus", state.handlers.onGeneric, { passive: true });
  window.addEventListener("mousemove", state.handlers.onMouseMove, { passive: true });

  // capture ensures deep child components still count
  document.addEventListener("input", state.handlers.onInputCapture, true);
  document.addEventListener("change", state.handlers.onChangeCapture, true);

  // returning to tab counts as activity
  document.addEventListener("visibilitychange", state.handlers.onVisibility);
}

function removeListeners() {
  if (!state.handlers) return;

  window.removeEventListener("click", state.handlers.onGeneric);
  window.removeEventListener("keydown", state.handlers.onGeneric);
  window.removeEventListener("scroll", state.handlers.onGeneric);
  window.removeEventListener("touchstart", state.handlers.onGeneric);
  window.removeEventListener("pointerdown", state.handlers.onGeneric);
  window.removeEventListener("wheel", state.handlers.onGeneric);
  window.removeEventListener("focus", state.handlers.onGeneric);
  window.removeEventListener("mousemove", state.handlers.onMouseMove);

  document.removeEventListener("input", state.handlers.onInputCapture, true);
  document.removeEventListener("change", state.handlers.onChangeCapture, true);
  document.removeEventListener("visibilitychange", state.handlers.onVisibility);
}

function attachListeners() {
  if (state.listenersAttached) return;
  state.listenersAttached = true;
  addListeners();
}

function detachListeners() {
  if (!state.listenersAttached) return;
  state.listenersAttached = false;
  removeListeners();
}

function startTimer() {
  if (state.idleTimerId) return;
  state.idleTimerId = window.setInterval(tick, state.cfg.idleCheckMs);
}

function stopTimer() {
  if (!state.idleTimerId) return;
  window.clearInterval(state.idleTimerId);
  state.idleTimerId = null;
}

/**
 * Start the tracker (idempotent).
 *
 * @param {Object} options
 * @param {Function} options.getToken  -> returns current auth token (string|null)
 * @param {Function} options.pingFn    -> async (token) => Promise
 * @param {Function} options.onLogout  -> (message) => void
 * @param {Object} [options.config]    -> overrides DEFAULTS
 */
function start(options = {}) {
  const { getToken, pingFn, onLogout, config } = options;

  if (state.started) {
    dbg("start called but already started");
    return;
  }

  state.cfg = { ...DEFAULTS, ...(config || {}) };
  state.getToken = getToken;
  state.pingFn = pingFn;
  state.onLogout = onLogout;

  const t = nowMs();
  state.lastUserAt = t;
  state.lastApiAt = 0;
  state.lastPingAt = 0;
  state.activitySinceLastPing = false;

  state.userCooldownUntil = 0;
  if (state.cooldownReattachId) {
    window.clearTimeout(state.cooldownReattachId);
    state.cooldownReattachId = null;
  }

  attachListeners();
  startTimer();
  state.started = true;

  dbg("started", {
    inactivityMs: state.cfg.inactivityMs,
    pingIntervalMs: state.cfg.pingIntervalMs,
    idleCheckMs: state.cfg.idleCheckMs,
    eventCooldownMs: state.cfg.eventCooldownMs,
    detachListenersDuringCooldown: state.cfg.detachListenersDuringCooldown,
  });
}

/** Stop the tracker (safe to call multiple times). */
function stop() {
  if (!state.started) return;

  stopTimer();

  if (state.cooldownReattachId) {
    window.clearTimeout(state.cooldownReattachId);
    state.cooldownReattachId = null;
  }

  // Ensure everything is detached
  detachListeners();

  state.started = false;

  dbg("stopped");
}

/** Mark API activity (call this from axios interceptors or any request wrapper). */
function markApiActivity(kind = "api") {
  setApiActivity(kind);
}

export default {
  start,
  stop,
  markApiActivity,
};
