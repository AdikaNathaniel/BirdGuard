import { IsInt, IsNumber, IsOptional, Max, Min } from 'class-validator';

// Mirrors the bounds enforced again in device-service's
// buildServoSweepCommand() - validated here too so a bad request gets a
// clean 400 at the gateway instead of only failing deep in device-service.
export class StartServoSweepDto {
  @IsNumber()
  @Min(0)
  @Max(180)
  angle!: number;

  @IsNumber()
  @Min(0.05)
  @Max(5)
  seconds!: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(15)
  channel?: number;
}
