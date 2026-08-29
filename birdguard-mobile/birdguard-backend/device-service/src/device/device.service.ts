import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NodeSSH } from 'node-ssh';
import { COMMANDS, CommandKey } from './commands';

export interface CommandResult {
  success: boolean;
  output?: string;
  error?: string;
}

export interface DetectorStatusResult {
  success: boolean;
  running?: boolean;
  pid?: string;
  error?: string;
}

@Injectable()
export class DeviceService {
  private readonly logger = new Logger(DeviceService.name);

  constructor(private readonly configService: ConfigService) {}

  /**
   * Connects to the Pi fresh, runs one fixed command from the COMMANDS
   * registry, and disconnects. Never accepts a raw command string from a
   * caller - only a key of COMMANDS.
   */
  private async runCommand(key: CommandKey): Promise<CommandResult> {
    const command = COMMANDS[key];
    const ssh = new NodeSSH();
    const execTimeoutMs = Number(this.configService.get('PI_SSH_EXEC_TIMEOUT_MS') ?? 15000);

    try {
      await ssh.connect(this.buildConnectionConfig());

      const result = await Promise.race([
        ssh.execCommand(command),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error(`Command timed out after ${execTimeoutMs}ms`)), execTimeoutMs),
        ),
      ]);

      if (result.code !== 0 && result.code !== null) {
        this.logger.warn(`Command ${key} exited with code ${result.code}: ${result.stderr}`);
      }

      return {
        success: true,
        output: (result.stdout || result.stderr || '').trim(),
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown SSH error';
      this.logger.error(`Failed to run command ${key}: ${message}`);
      return { success: false, error: message };
    } finally {
      ssh.dispose();
    }
  }

  private buildConnectionConfig() {
    const host = this.configService.get<string>('PI_HOST') ?? '192.168.43.233';
    const username = this.configService.get<string>('PI_USERNAME') ?? 'pi';
    const privateKeyPath = this.configService.get<string>('PI_PRIVATE_KEY_PATH');
    const password = this.configService.get<string>('PI_PASSWORD');
    const readyTimeout = Number(this.configService.get('PI_SSH_TIMEOUT_MS') ?? 10000);

    if (privateKeyPath) {
      return { host, username, privateKeyPath, readyTimeout };
    }

    return { host, username, password, readyTimeout };
  }

  async startDetector(): Promise<CommandResult> {
    const result = await this.runCommand('START_DETECTOR');
    if (!result.success) return result;

    const output = result.output ?? '';
    if (output.startsWith('STARTED')) {
      return { success: true, output };
    }
    // Process was launched but had already exited by the time we checked -
    // surface the log tail so the failure is actionable instead of a bare
    // false "started".
    return { success: false, error: output || 'Detector process exited immediately after launch' };
  }

  async stopDetector(): Promise<CommandResult> {
    const result = await this.runCommand('STOP_DETECTOR');
    if (!result.success) return result;

    const output = result.output ?? '';
    if (output.includes('STILL_RUNNING')) {
      return { success: false, error: 'Detector did not stop within the timeout' };
    }
    return { success: true, output };
  }

  async getDetectorStatus(): Promise<DetectorStatusResult> {
    const result = await this.runCommand('DETECTOR_STATUS');

    if (!result.success) {
      return { success: false, error: result.error };
    }

    const pid = (result.output ?? '').split('\n')[0]?.trim();
    const running = Boolean(pid);

    return running ? { success: true, running: true, pid } : { success: true, running: false };
  }
}
