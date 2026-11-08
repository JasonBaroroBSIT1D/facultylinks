import 'package:flutter/material.dart';

import 'auth_contact.dart';
import 'fl_logo.dart';

/// Logo header for login and password recovery.
class AuthBrandingHeader extends StatelessWidget {
  final bool onDark;
  const AuthBrandingHeader({super.key, this.onDark = true});

  @override
  Widget build(BuildContext context) {
    return const FlBrandCompact(centered: true);
  }
}

void showInstitutionAdminContact(BuildContext context) => showFacultyLinkAdminContact(context);
