import { Body, Controller, Get, Inject, Post, UseGuards } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { StartServoSweepDto } from './dto/start-servo-sweep.dto';

// Requires a valid JWT -- every route here just forwards to device-service,
// which holds the Pi's SSH credentials and is the only place a raw
// command ever gets constructed (see device-service/src/device/commands.ts).
// This gateway never accepts or forwards a free-text command from the app.
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

  // Settings page: field-of-view sweep. `dto` is already validated by the
  // global ValidationPipe (main.ts) against StartServoSweepDto's bounds
  // before this method ever runs.
  @Post('servo/start')
  async startServoSweep(@Body() dto: StartServoSweepDto) {
    return firstValueFrom(this.deviceClient.send({ cmd: 'startServoSweep' }, dto));
  }

  @Post('servo/stop')
  async stopServoSweep() {
    return firstValueFrom(this.deviceClient.send({ cmd: 'stopServoSweep' }, {}));
  }

  @Get('servo/status')
  async getServoSweepStatus() {
    return firstValueFrom(this.deviceClient.send({ cmd: 'getServoSweepStatus' }, {}));
  }
}
