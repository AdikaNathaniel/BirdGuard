import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AuthModule } from './auth/auth.module';
import { DetectionsModule } from './detections/detections.module';
import { DeviceModule } from './device/device.module';

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
