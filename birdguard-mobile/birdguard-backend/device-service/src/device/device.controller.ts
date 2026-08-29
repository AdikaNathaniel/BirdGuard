import { Controller } from '@nestjs/common';
import { MessagePattern } from '@nestjs/microservices';
import { DeviceService } from './device.service';

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
