import { ASSESSMENT_CATALOG } from '../core/assessment-definitions.js';
import { DEFAULT_INSTITUTION_CONFIG } from '../core/institution-config.js';
import { ConfigRepository, ensureAssessmentConfig } from './config-repository.js';
import { estimateEntryPoints } from '../core/scoring.js';

export const MOCK_STORE_STORAGE_KEY = 'facultylink_demo_state_v1';
const STORAGE_KEY = MOCK_STORE_STORAGE_KEY;

const DEFAULT_STATE = () => ({
  configPublished: ASSESSMENT_CATALOG.version,
  configDraft: null,
  institutionConfig: DEFAULT_INSTITUTION_CONFIG(),
  faculty: [
    {
      id: 'fac-001',
      employeeId: 'USTP-F-1001',
      firstName: 'Juan',
      lastName: 'Dela Cruz',
      email: 'faculty@ustp.demo',
      rank: 'Instructor I',
      department: 'College of Engineering',
      status: 'active',
      reviewerId: 'rev-001',
      phone: '+63 912 000 1001',
    },
    {
      id: 'fac-002',
      employeeId: 'USTP-F-1002',
      firstName: 'Maria',
      lastName: 'Santos',
      email: 'maria.santos@ustp.demo',
      rank: 'Assistant Professor I',
      department: 'College of IT',
      status: 'active',
      reviewerId: 'rev-001',
      phone: '+63 912 000 1002',
    },
    {
      id: 'fac-003',
      employeeId: 'USTP-F-1003',
      firstName: 'Ana',
      lastName: 'Reyes',
      email: 'ana.reyes@ustp.demo',
      rank: 'Instructor II',
      department: 'College of Education',
      status: 'inactive',
      reviewerId: 'rev-001',
    },
  ],
  reviewers: [
    {
      id: 'rev-001',
      employeeId: 'USTP-R-2001',
      firstName: 'Elena',
      lastName: 'Mendoza',
      email: 'reviewer@ustp.demo',
      department: 'Academic Affairs',
      status: 'active',
      assignedFacultyIds: ['fac-001', 'fac-002', 'fac-003'],
    },
    {
      id: 'rev-002',
      employeeId: 'USTP-R-2002',
      firstName: 'Carlos',
      lastName: 'Rivera',
      email: 'carlos.rivera@ustp.demo',
      department: 'Research Office',
      status: 'active',
      assignedFacultyIds: [],
    },
  ],
  admins: [
    {
      id: 'adm-001',
      name: 'System Administrator',
      email: 'admin@ustp.demo',
      role: 'admin',
    },
  ],
  assessments: {
    'fac-001': seedFaculty001(),
    'fac-002': { setSef: { SET: [], SEF: [] }, entries: {} },
  },
  documents: seedDocuments(),
  activity: [
    { id: 'act-1', at: new Date().toISOString(), actor: 'reviewer@ustp.demo', text: 'Approved SET document for Juan Dela Cruz (AY 2024–2025, 1st Sem).' },
    { id: 'act-2', at: new Date(Date.now() - 86400000).toISOString(), actor: 'admin@ustp.demo', text: 'Published assessment configuration v2022-jc3-demo-1.' },
  ],
  notifications: [
    { id: 'n1', facultyId: 'fac-001', title: 'Document approved', body: 'Your SET rating evidence for 2024–2025 1st Sem was approved.', read: false, at: new Date().toISOString() },
    { id: 'n2', facultyId: 'fac-001', title: 'Correction requested', body: 'Journal article PDF needs clearer ISSN metadata.', read: false, at: new Date(Date.now() - 3600000).toISOString() },
  ],
});

function seedFaculty001() {
  return {
    setSef: {
      SET: [92, 94, null, null, null, null],
      SEF: [95, 96, null, null, null, null],
    },
    entries: {
      'kra-II-A-3': [
        {
          id: 'ent-j1',
          title: 'IoT-Based Classroom Monitoring',
          date: '2025-06-01',
          authorship: 'sole',
          contributionPercent: 100,
          estimatedPoints: 50,
          reviewStatus: 'pending',
        },
      ],
      'kra-IV-B-2': [
        {
          id: 'ent-conf1',
          title: 'Research Capacity Building Workshop',
          date: '2025-03-12',
          scope: 'local',
          estimatedPoints: 1,
          reviewStatus: 'approved',
          reviewerVerifiedPoints: 1,
        },
      ],
    },
  };
}

function seedDocuments() {
  return [
    {
      id: 'doc-set-1',
      facultyId: 'fac-001',
      kraId: 'kra-I',
      criterionId: 'kra-I-A',
      indicatorId: 'kra-I-A-set',
      folder: 'SET',
      fileName: 'SET_2024-2025_1stSem.pdf',
      fileType: 'application/pdf',
      academicYear: '2024-2025',
      semester: '1st Sem',
      rating: 94,
      submittedAt: '2025-11-01',
      reviewStatus: 'approved',
      estimatedPoints: null,
      verifiedPoints: null,
      ocrStatus: 'simulated',
      ocrText: 'SIMULATED OCR — Student Evaluation of Teachers\nFaculty: Juan Dela Cruz\nRating: 4.70 / 5.00 (94%)\nAcademic Year: 2024-2025 First Semester',
      remarks: '',
      history: [{ at: '2025-11-02', by: 'reviewer@ustp.demo', action: 'approved', note: 'Rating matches COPC form.' }],
    },
    {
      id: 'doc-journal-1',
      facultyId: 'fac-001',
      kraId: 'kra-II',
      criterionId: 'kra-II-A',
      indicatorId: 'kra-II-A-3',
      fileName: 'Journal_Article_IoT.pdf',
      fileType: 'application/pdf',
      submittedAt: '2025-10-20',
      reviewStatus: 'correction_requested',
      estimatedPoints: 50,
      verifiedPoints: null,
      ocrStatus: 'simulated',
      ocrText: 'SIMULATED OCR — Title: IoT-Based Classroom Monitoring\nISSN: [low confidence]',
      remarks: 'Please re-upload with visible ISSN on first page.',
      history: [{ at: '2025-10-22', by: 'reviewer@ustp.demo', action: 'correction_requested', note: 'ISSN not legible.' }],
      linkedEntryId: 'ent-j1',
    },
    {
      id: 'doc-draft-1',
      facultyId: 'fac-001',
      kraId: 'kra-IV',
      criterionId: 'kra-IV-B',
      indicatorId: 'kra-IV-B-2',
      fileName: 'Workshop_Certificate.pdf',
      fileType: 'application/pdf',
      submittedAt: '2025-09-01',
      reviewStatus: 'approved',
      estimatedPoints: 1,
      verifiedPoints: 1,
      ocrStatus: 'simulated',
      ocrText: 'SIMULATED OCR — Certificate of Participation — Local seminar',
      remarks: '',
      history: [{ at: '2025-09-03', by: 'reviewer@ustp.demo', action: 'approved', note: '' }],
      linkedEntryId: 'ent-conf1',
    },
  ];
}

export class MockStore {
  static load() {
    let s;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) s = JSON.parse(raw);
    } catch (_) {
      /* ignore */
    }
    if (!s) {
      s = DEFAULT_STATE();
    }
    const hadVersionedConfig = Boolean(s.assessmentConfig?.versions?.length);
    ensureAssessmentConfig(s);
    const activeId = s.assessmentConfig?.activePublishedId;
    let dirty = !hadVersionedConfig;
    Object.keys(s.assessments || {}).forEach((fid) => {
      const before = s.assessments[fid].configVersionId;
      ConfigRepository.pinFacultyConfigVersion(s, fid, s.assessments[fid].configVersionId || activeId);
      if (!before && s.assessments[fid].configVersionId) dirty = true;
    });
    if (dirty) MockStore.save(s, { notify: false });
    return s;
  }

  static save(state, { notify = true } = {}) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    if (notify) window.dispatchEvent(new CustomEvent('fl-state-changed'));
    return state;
  }

  static reset() {
    localStorage.removeItem(STORAGE_KEY);
    return MockStore.load();
  }

  static getDocumentStats() {
    const state = MockStore.load();
    const stats = { pending: 0, approved: 0, rejected: 0, correction_requested: 0 };
    for (const d of state.documents) {
      stats[d.reviewStatus] = (stats[d.reviewStatus] || 0) + 1;
    }
    return stats;
  }

  static updateDocument(id, patch) {
    const state = MockStore.load();
    const idx = state.documents.findIndex((d) => d.id === id);
    if (idx >= 0) {
      state.documents[idx] = { ...state.documents[idx], ...patch };
      MockStore.save(state);
    }
    return state.documents[idx];
  }

  static upsertFaculty(faculty) {
    const state = MockStore.load();
    const idx = state.faculty.findIndex((f) => f.id === faculty.id);
    if (idx >= 0) state.faculty[idx] = { ...state.faculty[idx], ...faculty };
    else state.faculty.push({ ...faculty, id: faculty.id || `fac-${Date.now()}` });
    if (!state.assessments[faculty.id]) {
      state.assessments[faculty.id] = { setSef: { SET: [], SEF: [] }, entries: {} };
      const activeId = state.assessmentConfig?.activePublishedId;
      if (activeId) ConfigRepository.pinFacultyConfigVersion(state, faculty.id, activeId);
    }
    MockStore.save(state);
    return faculty;
  }

  static upsertReviewer(rev) {
    const state = MockStore.load();
    const idx = state.reviewers.findIndex((r) => r.id === rev.id);
    if (idx >= 0) state.reviewers[idx] = { ...state.reviewers[idx], ...rev };
    else {
      state.reviewers.push({
        ...rev,
        id: rev.id || `rev-${Date.now()}`,
        assignedFacultyIds: rev.assignedFacultyIds ?? [],
      });
    }
    MockStore.save(state);
    return rev;
  }

  static logActivity(text, actor) {
    const state = MockStore.load();
    state.activity.unshift({ id: `act-${Date.now()}`, at: new Date().toISOString(), actor, text });
    MockStore.save(state);
  }
}

export function syncEntryPointsFromDocument(doc) {
  const state = MockStore.load();
  const assessment = state.assessments[doc.facultyId];
  if (!assessment || !doc.linkedEntryId) return;
  const entries = assessment.entries[doc.indicatorId] || [];
  const e = entries.find((x) => x.id === doc.linkedEntryId);
  if (e) {
    e.reviewStatus = doc.reviewStatus;
    if (doc.verifiedPoints != null) e.reviewerVerifiedPoints = doc.verifiedPoints;
    else if (doc.estimatedPoints != null) e.estimatedPoints = doc.estimatedPoints;
  }
  MockStore.save(state);
}
