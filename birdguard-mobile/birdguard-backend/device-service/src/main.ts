import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module';

async function bootstrap() {
  const host = process.env.DEVICE_SERVICE_HOST ?? '127.0.0.1';
  const port = Number(process.env.DEVICE_SERVICE_PORT ?? 3002);

  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: {
      host,
      port,
    },
  });

  await app.listen();
  // eslint-disable-next-line no-console
  console.log(`[device-service] TCP microservice listening on ${host}:${port}`);
}

bootstrap();
