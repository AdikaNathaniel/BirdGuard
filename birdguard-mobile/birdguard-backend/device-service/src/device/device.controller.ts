import { Controller } from '@nestjs/common';
import { MessagePattern } from '@nestjs/microservices';
import { DeviceService } from './device.service';

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
}
