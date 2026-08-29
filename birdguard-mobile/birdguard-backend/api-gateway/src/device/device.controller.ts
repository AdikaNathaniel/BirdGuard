import { Controller, Get, Inject, Post, UseGuards } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

@Controller('device')
@UseGuards(JwtAuthGuard)
export class DeviceController {
  constructor(@Inject('DEVICE_SERVICE') private readonly deviceClient: ClientProxy) {}

  @Post('detector/start')
  async startDetector() {
    return firstValueFrom(this.deviceClient.send({ cmd: 'startDetector' }, {}));
  }

  @Post('detector/stop')
  async stopDetector() {
    return firstValueFrom(this.deviceClient.send({ cmd: 'stopDetector' }, {}));
  }

  @Get('detector/status')
  async getDetectorStatus() {
    return firstValueFrom(this.deviceClient.send({ cmd: 'getDetectorStatus' }, {}));
  }
}
