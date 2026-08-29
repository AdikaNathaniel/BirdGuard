import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Detection, DetectionDocument } from './schemas/detection.schema';

interface GetDetectionsQuery {
  limit?: number;
  before?: string; // ISO date -- fetch detections older than this, for pagination
}

@Controller()
export class DetectionsController {
  constructor(
    @InjectModel(Detection.name) private readonly detectionModel: Model<DetectionDocument>,
  ) {}

  @MessagePattern({ cmd: 'getDetections' })
  async getDetections(@Payload() query: GetDetectionsQuery) {
    const limit = Math.min(Math.max(query?.limit ?? 50, 1), 200);
    const filter = query?.before ? { detectedAt: { $lt: new Date(query.before) } } : {};

    const detections = await this.detectionModel
      .find(filter)
      .sort({ detectedAt: -1 })
      .limit(limit)
      .lean();

    return { success: true, detections };
  }
}
