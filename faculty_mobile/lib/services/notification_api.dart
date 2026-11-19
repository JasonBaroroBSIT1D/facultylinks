import 'api_client.dart';

class NotificationApi {
  static Future<void> markRead(String notificationId) async {
    final res = await ApiClient.patch('/api/faculty/notifications/$notificationId/read', body: '{}');
    if (res.statusCode != 200) {
      throw Exception('Could not update notification');
    }
  }
}