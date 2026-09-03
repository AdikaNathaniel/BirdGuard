import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { DeviceService } from './device.service';

interface StartServoSweepPayload {
  angle1: number;
  seconds1: number;
  angle2: number;
  seconds2: number;
  channel?: number;
}

// Thin dispatch layer only -- every real decision (which SSH command to
// run, how to verify its result) lives in DeviceService, not here.
@Controller()
export class DeviceController {
  constructor(private readonly deviceService: DeviceService) {}

  @MessagePattern({ cmd: 'startDetector' })
  startDetector() {
    return this.deviceService.startDetector();
  }

  @MessagePattern({ cmd: 'stopDetector' })
  stopDetector() {
    return this.deviceService.stopDetector();
  }

  @MessagePattern({ cmd: 'getDetectorStatus' })
  getDetectorStatus() {
    return this.deviceService.getDetectorStatus();
  }

  @MessagePattern({ cmd: 'startServoSweep' })
  startServoSweep(@Payload() payload: StartServoSweepPayload) {
    return this.deviceService.startServoSweep(
      payload.angle1,
      payload.seconds1,
      payload.angle2,
      payload.seconds2,
      payload.channel,
    );
  }

  @MessagePattern({ cmd: 'stopServoSweep' })
  stopServoSweep() {
    return this.deviceService.stopServoSweep();
  }

  @MessagePattern({ cmd: 'getServoSweepStatus' })
  getServoSweepStatus() {
    return this.deviceService.getServoSweepStatus();
  }
}
