/// Plain-language labels for faculty app (readable, professional).
class UiStrings {
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

  static const uploadPdfServerNote =
      'PDFs and photos are uploaded securely for OCR and reviewer verification. '
      'Take photo uses your camera to capture an image — it is not an automatic document scan with edge detection or crop.';

  static const takePhotoLabel = 'Take photo';
  static const chooseFileLabel = 'Choose file';
  static const cameraPermissionDenied =
      'Camera permission is required to take a photo. Enable it in system settings, then try again.';
  static const setSefCameraNotSupported =
      'SET / SEF evaluation uses a specialized PDF reader. Photos and other images are not supported for this document type — choose a PDF instead.';

  static const setSefEvalCardTitle = 'SET / SEF Evaluation';
  static const setSefEvalCardBody =
      'Upload your evaluation PDF. It may contain SET, SEF, or both. We read the semesters from the file.';

  static const specialStatusCardTitle = 'Special Status';
  static const specialStatusCardBody =
      'Upload supporting documents for leave or other circumstances that apply to you.';

  static const setSefUploadHint =
      'Choose one PDF from your phone or computer. Camera photos are not accepted for SET / SEF because that pipeline only reads PDF text. You can add a short description if you like.';
}
