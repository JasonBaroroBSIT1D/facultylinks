import 'package:flutter/material.dart';

import '../../repositories/mock_repository.dart';
import '../../theme/app_spacing.dart';
import '../../widgets/assigned_reviewer_card.dart';

class ProfileTab extends StatefulWidget {
  final MockRepository repo;
  final Future<void> Function() onSave;
  final VoidCallback onLogout;
  const ProfileTab({super.key, required this.repo, required this.onSave, required this.onLogout});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<ProfileTab> {
  late TextEditingController _name;
  late TextEditingController _phone;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.repo.profile.name);
    _phone = TextEditingController(text: '+63 912 000 0000');
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: FlLayout.pagePadding,
      children: [
        const FlPageHeader(
          title: 'Profile',
          subtitle: 'Your contact details are saved on this device for the demo.',
        ),
        FlSurfaceCard(
          child: Column(
            children: [
              TextField(controller: _name, decoration: const InputDecoration(labelText: 'Display name')),
              const SizedBox(height: 12),
              TextField(
                enabled: false,
                decoration: InputDecoration(labelText: 'Email', hintText: widget.repo.profile.email),
              ),
              const SizedBox(height: 12),
              TextField(
                enabled: false,
                decoration: InputDecoration(labelText: 'Current rank', hintText: widget.repo.profile.rank),
              ),
              const SizedBox(height: 12),
              TextField(controller: _phone, decoration: const InputDecoration(labelText: 'Phone')),
            ],
          ),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        AssignedReviewerCard(profile: widget.repo.profile),
        const SizedBox(height: FlLayout.sectionGap),
        FilledButton(
          onPressed: () async {
            widget.repo.profile.name = _name.text;
            await widget.repo.save();
            await widget.onSave();
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profile saved on this device.')));
          },
          child: const Text('Save profile'),
        ),
        const SizedBox(height: 10),
        OutlinedButton(onPressed: widget.onLogout, child: const Text('Sign out')),
      ],
    );
  }
}
