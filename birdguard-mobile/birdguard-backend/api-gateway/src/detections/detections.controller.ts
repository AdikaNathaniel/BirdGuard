import { Controller, Get, Inject, Query, UseGuards } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

@Controller('detections')
@UseGuards(JwtAuthGuard)
export class DetectionsController {
  constructor(@Inject('DETECTION_SERVICE') private readonly detectionClient: ClientProxy) {}

  @Get()
  async getDetections(@Query('limit') limit?: string, @Query('before') before?: string) {
    return firstValueFrom(
      this.detectionClient.send(
        { cmd: 'getDetections' },
        { limit: limit ? Number(limit) : undefined, before },
      ),
    );
  }
}
