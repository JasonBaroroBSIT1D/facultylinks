import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Shared expandable criterion row for KRA I–IV assessment screens.
///
/// Starts collapsed unless [initiallyExpanded] or a prior PageStorage value says otherwise.
/// Expansion is keyed by [kraId] + [criterionId] so switching KRAs does not mix state.
class AssessmentCriterionTile extends StatefulWidget {
  final String kraId;
  final String criterionId;
  final String title;
  final List<Widget> children;
  final bool initiallyExpanded;

  AssessmentCriterionTile({
    required this.kraId,
    required this.criterionId,
    required this.title,
    required this.children,
    this.initiallyExpanded = false,
  }) : super(key: PageStorageKey<String>('criterion-$kraId-$criterionId'));

  @override
  State<AssessmentCriterionTile> createState() => _AssessmentCriterionTileState();
}

class _AssessmentCriterionTileState extends State<AssessmentCriterionTile> {
  late bool _expanded;
  bool _readStorage = false;

  Object get _storageId => 'expanded-${widget.kraId}-${widget.criterionId}';

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
  }

  @override
  void didUpdateWidget(covariant AssessmentCriterionTile oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initiallyExpanded && !_expanded) {
      _expanded = true;
      _writeExpanded(true);
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_readStorage) return;
    _readStorage = true;
    final stored = PageStorage.maybeOf(context)?.readState(context, identifier: _storageId);
    if (stored is bool) {
      _expanded = stored || widget.initiallyExpanded;
    } else if (widget.initiallyExpanded) {
      _expanded = true;
    }
  }

  void _writeExpanded(bool value) {
    PageStorage.maybeOf(context)?.writeState(context, value, identifier: _storageId);
  }

  void _toggle() {
    setState(() {
      _expanded = !_expanded;
      _writeExpanded(_expanded);
    });
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final titleStyle = TextStyle(
      fontSize: scale.scale(14),
      fontWeight: FontWeight.w600,
      color: AppColors.textMain,
      height: 1.35,
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.cardWhite,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: _toggle,
                borderRadius: BorderRadius.circular(12),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 48),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Text(
                            widget.title,
                            style: titleStyle,
                            softWrap: true,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Icon(
                          _expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                          color: AppColors.primaryBlue,
                          size: scale.scale(28).clamp(24.0, 32.0),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            AnimatedSize(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeInOut,
              alignment: Alignment.topCenter,
              child: _expanded
                  ? Column(
                      key: ValueKey('criterion-body-${widget.kraId}-${widget.criterionId}'),
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Divider(height: 1, thickness: 1, color: AppColors.border),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(2, 2, 2, 6),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: widget.children,
                          ),
                        ),
                      ],
                    )
                  : const SizedBox(width: double.infinity),
            ),
          ],
        ),
      ),
    );
  }
}
