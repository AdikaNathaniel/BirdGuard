/**
 * Fixed, whitelisted SSH command registry.
 *
 * This is a hard security boundary: DeviceService only ever looks up a command
 * by one of these known keys. No client-supplied string is ever interpolated
 * into a shell command. Do not add any code path that builds a command from
 * request input - to expose a new device action, add a new named entry here
 * and a matching message pattern / gateway route, following the existing
 * pattern (see device.controller.ts and device.service.ts).
 */
export const COMMANDS = {
  // `< /dev/null` fully detaches stdin from the SSH session -- without it,
  // the backgrounded (nohup ... &) long-running process can keep the SSH
  // exec channel open indefinitely, since the channel doesn't consider
  // itself "done" until stdin closes too.
  // After backgrounding, wait briefly and confirm the process is actually
  // still alive before reporting success - camera-open failures (e.g. the
  // device still held by a just-killed previous run) happen a moment after
  // launch, not at launch, so echoing $! alone can report a false success.
  // `python -u` disables stdout buffering: without it, output redirected to
  // a file (rather than an interactive terminal) is block-buffered, so the
  // script's print()s sit in memory and never reach detector.log until the
  // buffer fills or the process exits - the process runs fine, the log just
  // looks frozen.
  // Reverted from the pan/tilt-tracking variant (pi_person_detector_cpu_offset.py)
  // back to this one on 2026-08-31 -- that variant's servo turned out to
  // keep spinning even after being commanded back to center (evidence
  // points to a continuous-rotation servo, which needs a different control
  // scheme than angle-hold). Revisit once the servo type is confirmed and
  // the tracking logic is redesigned to match.
  START_DETECTOR:
    'cd ~/BirdGuard/pi-nano-laser && source /home/pi/birdguard-env/bin/activate && ' +
    'nohup python -u pi_person_detector_cpu.py > /home/pi/detector.log 2>&1 < /dev/null & ' +
    'PID=$!; sleep 2; ' +
    'if kill -0 $PID 2>/dev/null; then echo "STARTED $PID"; else echo "FAILED"; tail -n 20 /home/pi/detector.log; fi',
  // SIGTERM alone returns immediately, before the process has actually
  // exited (it can be blocked in a camera read and only notices the signal
  // once it returns to the interpreter). Poll for real death, escalating to
  // SIGKILL, so status checks made right after this command see the true
  // state instead of a stale "still running".
  STOP_DETECTOR:
    'pkill -f pi_person_detector_cpu.py || true; ' +
    'for i in $(seq 1 10); do pgrep -f pi_person_detector_cpu.py >/dev/null 2>&1 || break; sleep 0.5; done; ' +
    'pkill -9 -f pi_person_detector_cpu.py || true; sleep 0.3; ' +
    'pgrep -f pi_person_detector_cpu.py >/dev/null 2>&1 && echo STILL_RUNNING || echo STOPPED',
  DETECTOR_STATUS: 'pgrep -f pi_person_detector_cpu.py || true',
} as const;

export type CommandKey = keyof typeof COMMANDS;
