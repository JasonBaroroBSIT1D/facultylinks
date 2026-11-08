import 'package:flutter/material.dart';

/// Official FacultyLink logo (original supplied artwork).
class FlLogo extends StatelessWidget {
  static const String assetPath = 'assets/branding/FacultyLink-logo.jpg';

  final double? width;
  final double? height;

  const FlLogo({super.key, this.width, this.height});

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      assetPath,
      width: width,
      height: height,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      semanticLabel: 'FacultyLink',
    );
  }
}

/// Splash / about-style placements.
class FlLogoFull extends FlLogo {
  const FlLogoFull({super.key, super.width, super.height});
}

/// Login / header row — single lockup image (wordmark is in the artwork).
class FlBrandCompact extends StatelessWidget {
  final bool centered;
  final double height;

  const FlBrandCompact({
    super.key,
    this.centered = false,
    this.height = 72,
  });

  @override
  Widget build(BuildContext context) {
    final logo = FlLogo(height: height);
    if (!centered) return logo;
    return Center(child: logo);
  }
}
