import 'package:flutter/material.dart';

void showFacultyLinkAdminContact(BuildContext context) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (ctx) => const Padding(
      padding: EdgeInsets.fromLTRB(24, 8, 24, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Institution administrator', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          SizedBox(height: 12),
          Text('Office of Academic Affairs'),
          Text('eval@ustp.edu.ph'),
          Text('+63 88 531 8000'),
        ],
      ),
    ),
  );
}
