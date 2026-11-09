/** Pure helpers for achievement folder/review UI (safe for Node unit tests). */

export function formatFileSize(bytes) {
  if (bytes == null || bytes <= 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function fileTypeLabel(doc) {
  const mime = (doc?.mimeType || '').toLowerCase();
  if (mime.includes('pdf')) return 'PDF';
  if (mime.includes('png')) return 'PNG';
  if (mime.includes('jpeg') || mime.includes('jpg')) return 'JPEG';
  if (mime.includes('webp')) return 'WebP';
  const ext = (doc?.fileName || '').split('.').pop();
  return ext ? ext.toUpperCase() : 'File';
}

export function indicatorDisplayName(catalog, indicatorId) {
  if (!catalog?.kras) return indicatorId || '—';
  for (const kra of catalog.kras) {
    for (const crit of kra.criteria || []) {
      for (const ind of crit.indicators || []) {
        if (ind.id === indicatorId) return ind.name || indicatorId;
      }
    }
  }
  return indicatorId || '—';
}

export function formatCompactUploadDate(raw) {
  if (!raw) return '—';
  try {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return String(raw).slice(0, 10);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return String(raw).slice(0, 10);
  }
}

export function achievementReviewStatusLabel(status) {
  const map = {
    approved: 'Approved',
    pending: 'Pending review',
    correction_requested: 'Needs changes',
    rejected: 'Rejected',
  };
  return map[status] || (status ? String(status).replace(/_/g, ' ') : 'Pending review');
}

const DESIGNATION_LEVEL_LABELS = {
  institutional: 'Institutional level',
  college_department: 'College / department level',
};

const DESIGNATION_ROLE_LABELS = {
  president: 'President',
  vice_president: 'Vice president',
  chancellor: 'Chancellor',
  vice_chancellor: 'Vice chancellor',
  campus_director: 'Campus director',
  faculty_trustee: 'Faculty trustee',
  office_director: 'Office director',
  university_secretary: 'University secretary',
  project_head: 'Project head',
  inst_committee_chair: 'Institutional committee chair',
  inst_committee_member: 'Institutional committee member',
  inst_coordinator: 'Institutional coordinator',
  dean: 'Dean',
  associate_dean: 'Associate dean',
  college_secretary: 'College secretary',
  department_head: 'Department head',
  program_chair: 'Program chair',
  dept_committee_chair: 'Department committee chair',
  dept_committee_member: 'Department committee member',
  dept_coordinator: 'Department coordinator',
};

export function formatDesignationLevel(value) {
  if (!value) return '';
  const key = String(value).trim().toLowerCase();
  return DESIGNATION_LEVEL_LABELS[key] || String(value).replace(/_/g, ' ');
}

export function formatDesignationRole(value) {
  if (!value) return '';
  const key = String(value).trim().toLowerCase();
  return DESIGNATION_ROLE_LABELS[key] || String(value).replace(/_/g, ' ');
}

export function formatAchievementContextLine(achievement) {
  if (!achievement || typeof achievement !== 'object') return '';
  const parts = [];
  const level = formatDesignationLevel(achievement.designationLevel);
  const role = formatDesignationRole(achievement.designationRole);
  if (level) parts.push(level);
  if (role) parts.push(role);
  if (achievement.serviceScope) parts.push(String(achievement.serviceScope).replace(/_/g, ' '));
  if (achievement.extensionRole) parts.push(String(achievement.extensionRole).replace(/_/g, ' '));
  return parts.join(' · ');
}

export function criterionBackLabel(criterionId) {
  const letter = (criterionId || '').match(/^kra-(?:I|II|III)-([A-D])$/i)?.[1];
  if (letter) return `Back to Criterion ${letter.toUpperCase()}`;
  if (criterionId === 'kra-I-A') return 'Back to Criterion A';
  return 'Back to workspace';
}

export function criterionReviewPageTitle(criterionId) {
  const letter = (criterionId || '').match(/^kra-(?:I|II|III)-([A-D])$/i)?.[1];
  if (letter) return `Criterion ${letter.toUpperCase()} review`;
  return 'Achievement review';
}

export function rulePermittedPoints(achievement) {
  if (achievement?.ruleExpectedPoints != null) return Number(achievement.ruleExpectedPoints);
  if (achievement?.permittedMax != null) return Number(achievement.permittedMax);
  return null;
}

export function groupAchievementsByIndicator(list) {
  const map = new Map();
  for (const a of list) {
    const key = a.indicatorId || 'unknown';
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(a);
  }
  return map;
}
