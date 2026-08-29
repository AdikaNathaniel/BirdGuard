import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Wraps [FlutterSecureStorage] to persist and retrieve the JWT issued by
/// the api-gateway's `/auth/login` (and `/auth/register`) endpoints, so the
/// user doesn't have to log in again every time the app restarts.
class AuthStorage {
  AuthStorage._internal();
  static final AuthStorage instance = AuthStorage._internal();

  static const _tokenKey = 'birdguard_access_token';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<void> saveToken(String token) {
    return _storage.write(key: _tokenKey, value: token);
  }

  Future<String?> readToken() {
    return _storage.read(key: _tokenKey);
  }

  Future<bool> hasToken() async {
    final token = await readToken();
    return token != null && token.isNotEmpty;
  }

  Future<void> clearToken() {
    return _storage.delete(key: _tokenKey);
  }
}
