import 'package:flutter/material.dart';

class ForgotPasswordScreen extends StatelessWidget {
  const ForgotPasswordScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Password recovery')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              color: Colors.amber.shade50,
              child: const Padding(
                padding: EdgeInsets.all(12),
                child: Text('Demonstration only. Email and verification codes are simulated until backend integration.'),
              ),
            ),
            const SizedBox(height: 16),
            const TextField(decoration: InputDecoration(labelText: 'Email')),
            const SizedBox(height: 12),
            const TextField(decoration: InputDecoration(labelText: 'Verification code (demo: 123456)')),
            const SizedBox(height: 12),
            const TextField(obscureText: true, decoration: InputDecoration(labelText: 'New password')),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Demo reset recorded locally only')));
                Navigator.pop(context);
              },
              child: const Text('Update password (demo)'),
            ),
          ],
        ),
      ),
    );
  }
}
