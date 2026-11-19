/// Plain-language labels for faculty app (readable, professional).
class UiStrings {
  static const estimatedPoints = 'Estimated points';
  static const estimatedPointsHelp = 'Your current self-assessment estimate.';
  static const verifiedPoints = 'Reviewer-verified points';
  static const verifiedPointsHelp = 'Points checked by your reviewer.';

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

  static const uploadDocumentHint =
      'Add your files or scan printed documents. You can attach more than one document.';

  /// @Deprecated — use [uploadDocumentHint]
  static const uploadPdfServerNote = uploadDocumentHint;

  static const takePhotoLabel = 'Take photo';
  static const scanWithCameraLabel = 'Scan with Camera';
  static const chooseFileLabel = 'Choose File';
  static const addFilesLabel = 'Add files';
  static const cameraPermissionDenied =
      'Camera permission is required to take a photo. Enable it in system settings, then try again.';

  static const setSefEvalCardTitle = 'SET / SEF Evaluation';
  static const setSefEvalCardBody =
      'Add evaluation files or scans. You can attach more than one document. We read the semesters from clear text.';

  static const specialStatusCardTitle = 'Special Status';
  static const specialStatusCardBody =
      'Upload supporting documents for leave or other circumstances that apply to you.';

  static const setSefUploadHint = uploadDocumentHint;
}
