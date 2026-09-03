import 'dart:async';

import 'package:flutter/material.dart';

import 'services/api_client.dart';

/// Lets the user configure and control the pan servo's field-of-view sweep:
/// how wide an angle it oscillates across, and how long it holds each side
/// before reversing. Talks to the same start/stop/status pattern already
/// proven by the Detector tab, just against the `/device/servo/*` routes.
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _formKey = GlobalKey<FormState>();
  final _angleController = TextEditingController(text: '30');
  final _secondsController = TextEditingController(text: '0.6');

  Timer? _statusTimer;

  bool? _isRunning; // null = unknown/loading
  String? _pid;
  bool _statusError = false;

  bool _startInFlight = false;
  bool _stopInFlight = false;

  @override
  void initState() {
    super.initState();
    _refreshStatus();
    _statusTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      // Same reasoning as DetectorTab: skip while a start/stop is already
      // in flight, since that action refreshes status itself on completion.
      if (_startInFlight || _stopInFlight) return;
      _refreshStatus();
    });
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    _angleController.dispose();
    _secondsController.dispose();
    super.dispose();
  }

  Future<void> _refreshStatus() async {
    try {
      final result = await ApiClient.instance.getServoSweepStatus();
      if (!mounted) return;
      setState(() {
        _isRunning = result['running'] == true;
        _pid = result['pid']?.toString();
        _statusError = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _statusError = true);
    }
  }

  String? _validateAngle(String? value) {
    final parsed = double.tryParse(value ?? '');
    if (parsed == null) return 'Enter a number';
    if (parsed < 0 || parsed > 180) return 'Must be between 0 and 180';
    return null;
  }

  String? _validateSeconds(String? value) {
    final parsed = double.tryParse(value ?? '');
    if (parsed == null) return 'Enter a number';
    if (parsed < 0.05 || parsed > 5) return 'Must be between 0.05 and 5';
    return null;
  }

  Future<void> _startSweep() async {
    if (!_formKey.currentState!.validate()) return;

    final angle = double.parse(_angleController.text);
    final seconds = double.parse(_secondsController.text);

    setState(() => _startInFlight = true);
    try {
      final result = await ApiClient.instance.startServoSweep(angle: angle, seconds: seconds);
      if (!mounted) return;
      final success = result['success'] != false;
      _showSnackBar(
        success ? 'Sweep started' : 'Failed to start sweep',
        isError: !success,
      );
      if (success) {
        // Backend already verifies the process is actually alive before
        // reporting success -- trust it directly rather than spending a
        // second SSH round trip just to re-confirm what this already told us.
        final output = result['output']?.toString() ?? '';
        final pid = RegExp(r'STARTED\s+(\d+)').firstMatch(output)?.group(1);
        setState(() {
          _isRunning = true;
          _pid = pid;
          _statusError = false;
        });
      } else {
        unawaited(_refreshStatus());
      }
    } on ApiException catch (e) {
      _showSnackBar('Failed to start sweep: ${e.message}', isError: true);
      unawaited(_refreshStatus());
    } catch (_) {
      _showSnackBar('Failed to start sweep: connection error', isError: true);
      unawaited(_refreshStatus());
    } finally {
      if (mounted) setState(() => _startInFlight = false);
    }
  }

  Future<void> _stopSweep() async {
    setState(() => _stopInFlight = true);
    try {
      final result = await ApiClient.instance.stopServoSweep();
      if (!mounted) return;
      final success = result['success'] != false;
      _showSnackBar(
        success ? 'Sweep stopped' : 'Failed to stop sweep',
        isError: !success,
      );
      if (success) {
        setState(() {
          _isRunning = false;
          _pid = null;
          _statusError = false;
        });
      } else {
        unawaited(_refreshStatus());
      }
    } on ApiException catch (e) {
      _showSnackBar('Failed to stop sweep: ${e.message}', isError: true);
      unawaited(_refreshStatus());
    } catch (_) {
      _showSnackBar('Failed to stop sweep: connection error', isError: true);
      unawaited(_refreshStatus());
    } finally {
      if (mounted) setState(() => _stopInFlight = false);
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.redAccent : Colors.green,
      ),
    );
  }

  Widget _buildStatusCard() {
    final bool running = _isRunning == true;
    final bool unknown = _isRunning == null || _statusError;

    final Color dotColor = unknown ? Colors.grey : (running ? Colors.green : Colors.grey);

    String label;
    if (_startInFlight) {
      label = 'Sweep: Starting…';
    } else if (_stopInFlight) {
      label = 'Sweep: Stopping…';
    } else if (_statusError && _isRunning == null) {
      label = 'Sweep: Unknown (status unavailable)';
    } else if (unknown) {
      label = 'Sweep: Checking…';
    } else {
      label = running ? 'Sweep: Running' : 'Sweep: Stopped';
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300, width: 1.5),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
          if (_pid != null && running)
            Text(
              'PID $_pid',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool running = _isRunning == true;
    // Editing the angle/duration of a sweep already in progress would be
    // ambiguous (which value does the app apply, and when?) -- so the
    // fields are locked while a sweep is running; stop it first to change them.
    final bool fieldsEnabled = !running && !_startInFlight && !_stopInFlight;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Field of View Sweep',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  'The pan servo oscillates between the given angle and its '
                  'mirror on the other side of center, holding each side for '
                  'the given duration.',
                  style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600),
                ),
                const SizedBox(height: 20),
                TextFormField(
                  controller: _angleController,
                  enabled: fieldsEnabled,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  autovalidateMode: AutovalidateMode.onUserInteraction,
                  validator: _validateAngle,
                  decoration: const InputDecoration(
                    labelText: 'Field of View (degrees, 0-180)',
                    prefixIcon: Icon(Icons.rotate_right_outlined),
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _secondsController,
                  enabled: fieldsEnabled,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  autovalidateMode: AutovalidateMode.onUserInteraction,
                  validator: _validateSeconds,
                  decoration: const InputDecoration(
                    labelText: 'Hold Duration (seconds, 0.05-5)',
                    prefixIcon: Icon(Icons.timer_outlined),
                  ),
                ),
                const SizedBox(height: 24),
                _buildStatusCard(),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: (_startInFlight || running) ? null : _startSweep,
                          icon: _startInFlight
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                  ),
                                )
                              : const Icon(Icons.play_arrow),
                          label: const Text('Start Sweep'),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: (_stopInFlight || !running) ? null : _stopSweep,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.redAccent,
                            disabledBackgroundColor: Colors.blueGrey.shade100,
                          ),
                          icon: _stopInFlight
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                  ),
                                )
                              : const Icon(Icons.stop),
                          label: const Text('Stop Sweep'),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
