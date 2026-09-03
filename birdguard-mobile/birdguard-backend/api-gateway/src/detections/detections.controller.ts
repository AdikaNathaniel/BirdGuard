import { Controller, Get, Inject, Query, UseGuards } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

// Requires a valid JWT (JwtAuthGuard) -- purely a read-through to
// detection-service, which is the only thing that ever queries the
// detections collection (the Pi writes to it directly, bypassing the
// backend entirely).
@Controller('detections')
@UseGuards(JwtAuthGuard)
export class DetectionsController {
  constructor(@Inject('DETECTION_SERVICE') private readonly detectionClient: ClientProxy) {}

  @Get()
  async getDetections(@Query('limit') limit?: string, @Query('before') before?: string) {
    // `before` (an ISO timestamp) pages further back in history -- the
    // app passes the oldest currently-loaded detection's timestamp to
    // fetch the next older page.
    return firstValueFrom(
      this.detectionClient.send(
        { cmd: 'getDetections' },
        { limit: limit ? Number(limit) : undefined, before },
      ),
    );
  }
}
