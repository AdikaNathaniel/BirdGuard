import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { AuthModule } from '../auth/auth.module';
import { DeviceController } from './device.controller';

@Module({
  imports: [
    AuthModule,
    // TCP client pointed at device-service -- default port 3002,
    // matches DEVICE_SERVICE_PORT in that service's own .env.
    ClientsModule.registerAsync([
      {
        name: 'DEVICE_SERVICE',
        imports: [ConfigModule],
        inject: [ConfigService],
        useFactory: (config: ConfigService) => ({
          transport: Transport.TCP,
          options: {
            host: config.get<string>('DEVICE_SERVICE_HOST') ?? '127.0.0.1',
            port: Number(config.get('DEVICE_SERVICE_PORT') ?? 3002),
          },
        }),
      },
    ]),
  ],
  controllers: [DeviceController],
})
export class DeviceModule {}
