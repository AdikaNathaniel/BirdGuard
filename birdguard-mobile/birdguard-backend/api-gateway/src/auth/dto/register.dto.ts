import { IsEmail, IsIn, IsOptional, IsString, MinLength } from 'class-validator';

const USER_TYPES = ['ADMIN', 'CUSTOMER', 'SELLER', 'ANALYST'] as const;

export class RegisterDto {
  @IsEmail()
  email!: string;

  @IsString()
  @MinLength(3)
  username!: string;

  @IsString()
  @MinLength(8)
  password!: string;

  @IsOptional()
  @IsIn(USER_TYPES)
  userType?: (typeof USER_TYPES)[number];
}
