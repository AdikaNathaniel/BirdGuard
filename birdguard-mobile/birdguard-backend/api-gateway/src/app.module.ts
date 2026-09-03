import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AuthModule } from './auth/auth.module';
import { DetectionsModule } from './detections/detections.module';
import { DeviceModule } from './device/device.module';

// This is the single HTTP entry point the mobile app talks to -- it holds
// no business logic of its own, just routes each request to the right
// backend microservice (auth-service, device-service, detection-service)
// over an internal TCP connection, per feature module below.
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    AuthModule,
    DeviceModule,
    DetectionsModule,
  ],
})
export class AppModule {}
