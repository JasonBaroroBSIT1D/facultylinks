/// Plain-language labels for faculty app (readable, professional).
class UiStrings {
  static const kraHelp =
      'KRA (Key Result Area) — the four areas used to review your work: Instruction, Research, Extension, and Professional Development.';

  static const estimatedPoints = 'Estimated points';
  static const estimatedPointsHelp = 'Your current self-assessment estimate.';
  static const verifiedPoints = 'Reviewer-verified points';
  static const verifiedPointsHelp = 'Points checked by your reviewer.';
  static const whatIfPoints = 'What-if points';
  static const whatIfPointsHelp = 'Practice changes that do not affect your saved assessment.';

  static const rankRulesPending =
      'Rank requirements are not set yet. You can still explore your KRA points.';

  static const simDisclaimer =
      'Simulation results are for preparation only. Official rank decisions remain with authorized committees.';

  static String docStatusLabel(String status) {
    switch (status) {
      case 'approved':
        return 'Approved';
      case 'rejected':
        return 'Not accepted';
      case 'correction_requested':
        return 'Needs changes';
      case 'pending':
      default:
        return 'Pending review';
    }
  }

  static const emptyDocuments =
      'You have no documents yet. Tap Add Document to begin.';

  static const uploadDemoNote =
      'This app picks files on your device only (demonstration). Server upload comes later.';
}
