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
  START_DETECTOR:
    'cd ~/BirdGuard/pi-nano-laser && source /home/pi/birdguard-env/bin/activate && nohup python pi_person_detector_cpu.py > /home/pi/detector.log 2>&1 & echo $!',
  STOP_DETECTOR: 'pkill -f pi_person_detector_cpu.py || true',
  DETECTOR_STATUS: 'pgrep -f pi_person_detector_cpu.py || true',
} as const;

export type CommandKey = keyof typeof COMMANDS;
