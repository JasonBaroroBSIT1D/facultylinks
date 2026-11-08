import 'package:flutter/material.dart';

import 'app_theme.dart';

class FlLayout {
  static const pagePadding = EdgeInsets.fromLTRB(16, 8, 16, 24);
  static const cardPadding = EdgeInsets.all(16);
  static const cardRadius = 20.0;
  static const sectionGap = 12.0;
  static const homeSectionGap = 12.0;
}

class FlPageHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;

  const FlPageHeader({super.key, required this.title, this.subtitle, this.trailing});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: scale.scale(28),
                    fontWeight: FontWeight.w700,
                    color: AppColors.textMain,
                    height: 1.2,
                  ),
                ),
              ),
              if (trailing != null) trailing!,
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 6),
            Text(
              subtitle!,
              style: TextStyle(fontSize: scale.scale(17), color: AppColors.textMuted, height: 1.45),
            ),
          ],
        ],
      ),
    );
  }
}

class FlSectionTitle extends StatelessWidget {
  final String text;
  const FlSectionTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10, top: 4),
      child: Text(
        text,
        style: TextStyle(
          fontSize: scale.scale(21),
          fontWeight: FontWeight.w700,
          color: AppColors.textMain,
        ),
      ),
    );
  }
}

class FlSurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;

  const FlSurfaceCard({super.key, required this.child, this.padding, this.onTap});

  @override
  Widget build(BuildContext context) {
    final decor = BoxDecoration(
      color: AppColors.cardWhite,
      borderRadius: BorderRadius.circular(FlLayout.cardRadius),
      border: Border.all(color: AppColors.border),
      boxShadow: [
        BoxShadow(
          color: AppColors.navyDeep.withValues(alpha: 0.06),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
      ],
    );

    Widget inner = Padding(padding: padding ?? FlLayout.cardPadding, child: child);

    if (onTap == null) {
      return DecoratedBox(decoration: decor, child: inner);
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(FlLayout.cardRadius),
        child: Ink(decoration: decor, child: inner),
      ),
    );
  }
}

class FlTextBadge extends StatelessWidget {
  final String label;
  final bool compact;
  const FlTextBadge(this.label, {super.key, this.compact = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 10 : 12, vertical: compact ? 4 : 6),
      decoration: BoxDecoration(
        color: AppColors.primarySoft,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: compact ? 13 : 15,
          fontWeight: FontWeight.w600,
          color: AppColors.textMain,
        ),
      ),
    );
  }
}

class FlHomeSectionLabel extends StatelessWidget {
  final String text;
  const FlHomeSectionLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: TextStyle(
          fontSize: scale.scale(17),
          fontWeight: FontWeight.w700,
          color: AppColors.textMain,
        ),
      ),
    );
  }
}

class FlStatusBadge extends StatelessWidget {
  final String label;
  const FlStatusBadge(this.label, {super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: AppColors.yellowSoft,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textMain),
      ),
    );
  }
}

class FlYellowButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool expanded;
  final bool compact;

  const FlYellowButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.expanded = true,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final btn = ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.warmYellow,
        foregroundColor: AppColors.textMain,
        disabledBackgroundColor: AppColors.warmYellow.withValues(alpha: 0.5),
        minimumSize: Size(48, compact ? 48 : 50),
        padding: compact ? const EdgeInsets.symmetric(horizontal: 16, vertical: 10) : null,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: TextStyle(fontSize: compact ? 15 : 16, fontWeight: FontWeight.w700),
      ),
      child: icon != null
          ? Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 22),
                const SizedBox(width: 8),
                Text(label),
              ],
            )
          : Text(label),
    );
    if (!expanded) return btn;
    return SizedBox(width: double.infinity, child: btn);
  }
}
