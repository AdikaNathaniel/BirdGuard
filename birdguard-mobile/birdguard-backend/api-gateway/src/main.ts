import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.enableCors();

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
      forbidNonWhitelisted: false,
    }),
  );

  const port = Number(process.env.HTTP_PORT ?? 3000);
  await app.listen(port);
  // eslint-disable-next-line no-console
  console.log(`[api-gateway] HTTP server listening on port ${port}`);
}

bootstrap();
