import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { Detection, DetectionSchema } from './schemas/detection.schema';
import { DetectionsController } from './detections.controller';

@Module({
  imports: [MongooseModule.forFeature([{ name: Detection.name, schema: DetectionSchema }])],
  controllers: [DetectionsController],
})
export class DetectionsModule {}
