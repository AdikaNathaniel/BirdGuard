import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module';

async function bootstrap() {
  const host = process.env.AUTH_SERVICE_HOST ?? '127.0.0.1';
  const port = Number(process.env.AUTH_SERVICE_PORT ?? 3001);

  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: {
      host,
      port,
    },
  });

  // Defense in depth: validate incoming message payloads even though the
  // api-gateway already validates requests before forwarding them here.
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
    }),
  );

  await app.listen();
  // eslint-disable-next-line no-console
  console.log(`[auth-service] TCP microservice listening on ${host}:${port}`);
}

bootstrap();
