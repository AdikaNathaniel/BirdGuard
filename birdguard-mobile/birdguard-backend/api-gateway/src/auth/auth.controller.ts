import {
  Body,
  Controller,
  HttpCode,
  HttpException,
  Inject,
  Post,
} from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { LoginDto } from './dto/login.dto';
import { RegisterDto } from './dto/register.dto';

interface ErrorShape {
  statusCode: number;
  message: string;
}

function isErrorShape(value: unknown): value is ErrorShape {
  return (
    !!value &&
    typeof value === 'object' &&
    typeof (value as ErrorShape).statusCode === 'number' &&
    typeof (value as ErrorShape).message === 'string'
  );
}

@Controller('auth')
export class AuthController {
  constructor(@Inject('AUTH_SERVICE') private readonly authClient: ClientProxy) {}

  @Post('register')
  @HttpCode(201)
  async register(@Body() dto: RegisterDto) {
    const result = await firstValueFrom(this.authClient.send({ cmd: 'register' }, dto));

    if (isErrorShape(result)) {
      throw new HttpException(result.message, result.statusCode);
    }

    return result;
  }

  @Post('login')
  @HttpCode(200)
  async login(@Body() dto: LoginDto) {
    const result = await firstValueFrom(this.authClient.send({ cmd: 'login' }, dto));

    if (isErrorShape(result)) {
      throw new HttpException(result.message, result.statusCode);
    }

    return result;
  }
}
