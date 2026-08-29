import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { AuthModule } from '../auth/auth.module';
import { DetectionsController } from './detections.controller';

@Module({
  imports: [
    AuthModule,
    ClientsModule.registerAsync([
      {
        name: 'DETECTION_SERVICE',
        imports: [ConfigModule],
        inject: [ConfigService],
        useFactory: (config: ConfigService) => ({
          transport: Transport.TCP,
          options: {
            host: config.get<string>('DETECTION_SERVICE_HOST') ?? '127.0.0.1',
            port: Number(config.get('DETECTION_SERVICE_PORT') ?? 3003),
          },
        }),
      },
    ]),
  ],
  controllers: [DetectionsController],
})
export class DetectionsModule {}
