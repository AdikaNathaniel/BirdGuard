import { IsInt, IsNumber, IsOptional, Max, Min } from 'class-validator';

// Mirrors the bounds enforced again in device-service's
// buildServoSweepCommand() - validated here too so a bad request gets a
// clean 400 at the gateway instead of only failing deep in device-service.
// Two steps, matching the interactive `recur` command's two-entry sequence
// (e.g. p90,0.70 then p140,0.90): the servo cycles between them.
export class StartServoSweepDto {
  @IsNumber()
  @Min(0)
  @Max(180)
  angle1!: number;

  @IsNumber()
  @Min(0.05)
  @Max(5)
  seconds1!: number;

  @IsNumber()
  @Min(0)
  @Max(180)
  angle2!: number;

  @IsNumber()
  @Min(0.05)
  @Max(5)
  seconds2!: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(15)
  channel?: number;
}
