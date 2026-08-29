import 'dart:async';

import 'package:flutter/material.dart';

import 'fullscreen_camera_page.dart';
import 'login_page.dart';
import 'services/api_client.dart';
import 'services/auth_storage.dart';
import 'widgets/mjpeg_view.dart';

/// URL of the Pi's existing MJPEG camera stream (from `pi_person_detector.py`).
/// This is loaded directly by the Flutter app — it does NOT go through the
/// NestJS backend. CONFIGURE ME: update the host if the Pi's LAN IP changes.
const String cameraFeedUrl = 'http://192.168.43.233:8080/';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Timer? _statusTimer;

  bool? _isRunning; // null = unknown/loading
  String? _pid;
  bool _statusError = false;

  bool _startInFlight = false;
  bool _stopInFlight = false;

  // Bumping this forces the Mjpeg widget to reconnect the stream (used by
  // the "retry" action on the error state).
  int _feedReloadKey = 0;

  @override
  void initState() {
    super.initState();
    _refreshStatus();
    _statusTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _refreshStatus();
    });
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    super.dispose();
  }

  Future<void> _refreshStatus() async {
    try {
      final result = await ApiClient.instance.getDetectorStatus();
      if (!mounted) return;
      setState(() {
        _isRunning = result['running'] == true;
        _pid = result['pid']?.toString();
        _statusError = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _statusError = true;
      });
    }
  }

  Future<void> _startDetector() async {
    setState(() => _startInFlight = true);
    try {
      final result = await ApiClient.instance.startDetector();
      if (!mounted) return;
      final success = result['success'] != false;
      _showSnackBar(
        success ? 'Detector started' : 'Failed to start detector',
        isError: !success,
      );
      await _refreshStatus();
    } on ApiException catch (e) {
      _showSnackBar('Failed to start detector: ${e.message}', isError: true);
    } catch (_) {
      _showSnackBar('Failed to start detector: connection error', isError: true);
    } finally {
      if (mounted) setState(() => _startInFlight = false);
    }
  }

  Future<void> _stopDetector() async {
    setState(() => _stopInFlight = true);
    try {
      final result = await ApiClient.instance.stopDetector();
      if (!mounted) return;
      final success = result['success'] != false;
      _showSnackBar(
        success ? 'Detector stopped' : 'Failed to stop detector',
        isError: !success,
      );
      await _refreshStatus();
    } on ApiException catch (e) {
      _showSnackBar('Failed to stop detector: ${e.message}', isError: true);
    } catch (_) {
      _showSnackBar('Failed to stop detector: connection error', isError: true);
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

  Future<void> _logout() async {
    _statusTimer?.cancel();
    await AuthStorage.instance.clearToken();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginPage()),
      (route) => false,
    );
  }

  Widget _buildCameraFeed() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Container(
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300, width: 1.5),
          borderRadius: BorderRadius.circular(16),
        ),
        width: double.infinity,
        height: 260,
        child: Stack(
          fit: StackFit.expand,
          children: [
            MjpegView(
              key: ValueKey(_feedReloadKey),
              url: cameraFeedUrl,
              fit: BoxFit.cover,
              loadingBuilder: (context) => const Center(
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF1976D2)),
                ),
              ),
              errorBuilder: (context, error) {
                return Container(
                  color: Colors.grey.shade100,
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.videocam_off_outlined, size: 40, color: Colors.grey.shade500),
                        const SizedBox(height: 8),
                        Text(
                          'Camera feed unavailable',
                          style: TextStyle(color: Colors.grey.shade700),
                        ),
                        const SizedBox(height: 8),
                        IconButton(
                          icon: const Icon(Icons.refresh, color: Color(0xFF1976D2)),
                          tooltip: 'Retry',
                          onPressed: () {
                            setState(() => _feedReloadKey++);
                          },
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            Positioned(
              bottom: 8,
              right: 8,
              child: Material(
                color: Colors.black.withValues(alpha: 0.45),
                shape: const CircleBorder(),
                child: IconButton(
                  icon: const Icon(Icons.fullscreen, color: Colors.white),
                  tooltip: 'Full screen',
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const FullscreenCameraPage(cameraUrl: cameraFeedUrl),
                      ),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusRow() {
    final bool running = _isRunning == true;
    final bool unknown = _isRunning == null || _statusError;

    final Color dotColor = unknown
        ? Colors.grey
        : (running ? Colors.green : Colors.grey);

    String label;
    if (_statusError && _isRunning == null) {
      label = 'Detector: Unknown (status unavailable)';
    } else if (unknown) {
      label = 'Detector: Checking…';
    } else {
      label = running ? 'Detector: Running' : 'Detector: Stopped';
    }

    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: dotColor,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
          ),
        ),
        if (_pid != null && running)
          Text(
            'PID $_pid',
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool running = _isRunning == true;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('BirdGuard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: _logout,
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Live Camera Feed',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              _buildCameraFeed(),
              const SizedBox(height: 24),
              _buildStatusRow(),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: (_startInFlight || running) ? null : _startDetector,
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
                        label: const Text('Start Detector'),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: (_stopInFlight || !running) ? null : _stopDetector,
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
                        label: const Text('Stop Detector'),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
