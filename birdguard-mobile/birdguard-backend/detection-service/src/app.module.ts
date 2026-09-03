import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { MongooseModule } from '@nestjs/mongoose';
import { DetectionsModule } from './detections/detections.module';

// Read-only from the backend's perspective -- the Pi writes detection
// events directly into the same MongoDB collection this service reads
// from, so there's no create/update endpoint here at all, only queries.
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    MongooseModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        uri: config.get<string>('MONGODB_URI'),
      }),
    }),
    DetectionsModule,
  ],
})
export class AppModule {}
