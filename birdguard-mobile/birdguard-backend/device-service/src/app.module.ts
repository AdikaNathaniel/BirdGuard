import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { DeviceModule } from './device/device.module';

// Holds the Pi's SSH credentials and is the only service that ever
// connects to it -- see device/commands.ts for the fixed, whitelisted
// command registry that keeps this from becoming an arbitrary-command
// execution surface.
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    DeviceModule,
  ],
})
export class AppModule {}
