export type WorkflowStatus =
  | 'idle'
  | 'context'
  | 'risk'
  | 'pendingApproval'
  | 'clarification'
  | 'execution'
  | 'sandbox'
  | 'repair'
  | 'finished'
  | 'failed'
  | 'rejected';

export type EventType =
  | 'task.received'
  | 'context.search.completed'
  | 'prompt.expanded'
  | 'risk.preflight.completed'
  | 'hitl.approval.requested'
  | 'hitl.approved'
  | 'hitl.rejected'
  | 'hitl.clarification.requested'
  | 'compute.route.selected'
  | 'generation.started'
  | 'generation.completed'
  | 'sandbox.review.completed'
  | 'repair.started'
  | 'repair.completed'
  | 'workflow.finished'
  | 'workflow.failed';

export type WorkflowEvent = {
  id: string;
  type: EventType;
  label: string;
  detail: string;
  timestamp: string;
};

export type ReferenceRepo = {
  name: string;
  stars: string;
  signal: string;
};

export type RiskFinding = {
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  mitigation: string;
};

export type RouteDecision = {
  difficulty: number;
  model: string;
  provider: string;
  budget: string;
  latency: string;
  rationale: string;
};

export const CLOD_AI_MODEL = 'GPT OSS 120B';

export type ReviewResult = {
  status: 'pending' | 'failed' | 'passed';
  summary: string;
  tests: string[];
};

export type CodeArtifact = {
  title: string;
  language: string;
  summary: string;
  patch: string;
};

export type DemoCase = {
  title: string;
  request: string;
  whyItWorks: string;
};

export type WorkflowState = {
  taskId?: number;
  status: WorkflowStatus;
  userRequest: string;
  prompt: string;
  confidence: number;
  references: ReferenceRepo[];
  risks: RiskFinding[];
  route?: RouteDecision;
  code?: CodeArtifact;
  repairAttempts: number;
  maxRepairAttempts: number;
  review: ReviewResult;
  events: WorkflowEvent[];
};

export const defaultRequest =
  'Audit a TypeScript wallet integration for unsafe transaction signing, add tests, and return a maintainer-ready patch summary.';

export const demoCases: DemoCase[] = [
  {
    title: 'Wallet signing audit',
    request: defaultRequest,
    whyItWorks: 'Shows security context retrieval, HITL approval, routed generation, and one sandbox repair.',
  },
  {
    title: 'CI flake stabilizer',
    request:
      'Find why our Playwright checkout test flakes on retry, add deterministic waits, and keep the change isolated to the test helper.',
    whyItWorks: 'Shows that the prompt template can turn vague debugging into constrained implementation work.',
  },
  {
    title: 'API schema migration',
    request:
      'Refactor the user settings API response to include notification preferences without breaking old clients.',
    whyItWorks: 'Demonstrates difficulty scoring for compatibility risk and regression-test requirements.',
  },
];

export const initialState: WorkflowState = {
  status: 'idle',
  userRequest: defaultRequest,
  prompt: '',
  confidence: 0,
  references: [],
  risks: [],
  repairAttempts: 0,
  maxRepairAttempts: 3,
  review: {
    status: 'pending',
    summary: 'No sandbox review has run yet.',
    tests: [],
  },
  events: [],
};

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const now = () =>
  new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date());

let sequence = 0;

export const createEvent = (type: EventType, label: string, detail: string): WorkflowEvent => ({
  id: `${Date.now()}-${sequence++}`,
  type,
  label,
  detail,
  timestamp: now(),
});

export const addEvent = (
  state: WorkflowState,
  type: EventType,
  label: string,
  detail: string,
): WorkflowState => ({
  ...state,
  events: [createEvent(type, label, detail), ...state.events],
});

export const calculateDifficulty = (confidence: number, riskCount: number, request: string) => {
  const securityWeight = /wallet|auth|payment|permission|security|audit|transaction/i.test(request) ? 1 : 0;
  const migrationWeight = /migration|refactor|schema|compatibility|legacy/i.test(request) ? 1 : 0;
  const ambiguityPenalty = confidence < 75 ? 1 : 0;
  return Math.min(5, Math.max(1, 1 + Math.ceil(riskCount / 2) + securityWeight + migrationWeight + ambiguityPenalty));
};

export const mockClodContextSearch = async (request: string) => {
  await wait(420);

  const references: ReferenceRepo[] = [
    {
      name: 'safe-global/safe-smart-account',
      stars: '2.4k',
      signal: 'High-signal multisig transaction validation patterns',
    },
    {
      name: 'OpenZeppelin/openzeppelin-contracts',
      stars: '25k',
      signal: 'Battle-tested access control and security test conventions',
    },
    {
      name: 'wevm/wagmi',
      stars: '9.8k',
      signal: 'Typed wallet interaction and connector ergonomics',
    },
  ];

  const confidence = request.length > 80 ? 88 : 64;
  const prompt = `# Agent System Prompt

## Mission
Transform the user's request into a narrow, reviewable code change. Do not infer hidden requirements. Surface ambiguity before generation.

## User Request
${request}

## Retrieved Context
${references.map((repo) => `- ${repo.name} (${repo.stars}): ${repo.signal}`).join('\n')}

## Structured Requirements
- Locate the implementation surface before editing.
- Preserve existing public APIs unless a security guard requires an explicit type change.
- Add deterministic regression tests for every risky behavior changed.
- Return a maintainer-readable patch summary and test evidence.

## Acceptance Criteria
- Static checks pass.
- Tests include at least one failure-path assertion.
- The patch remains scoped to the approved request.

## Unknowns To Confirm
- Target repository conventions.
- Existing test runner and CI command.
- Whether the project allows breaking API changes.`;

  return { references, prompt, confidence };
};

export const mockAiPreflight = async () => {
  await wait(420);

  const risks: RiskFinding[] = [
    {
      title: 'Silent chain mismatch',
      severity: 'high',
      mitigation: 'Require explicit chain ID checks before signing or broadcasting.',
    },
    {
      title: 'Overbroad token approvals',
      severity: 'critical',
      mitigation: 'Reject unlimited approvals unless the user explicitly approved that policy.',
    },
    {
      title: 'Mock-only regression tests',
      severity: 'medium',
      mitigation: 'Test both payload validation and user-facing failure states.',
    },
    {
      title: 'Hidden retry loop',
      severity: 'medium',
      mitigation: 'Cap repair attempts and persist each failure reason.',
    },
  ];

  return risks;
};

export const appendRiskGuide = (prompt: string, risks: RiskFinding[]) => `${prompt}

## Negative Constraints From AI Preflight
${risks.map((risk) => `- [${risk.severity.toUpperCase()}] ${risk.title}: ${risk.mitigation}`).join('\n')}`;

export const mockClodRoute = async (
  confidence: number,
  riskCount: number,
  request: string,
): Promise<RouteDecision> => {
  await wait(420);
  const difficulty = calculateDifficulty(confidence, riskCount, request);
  const highDifficulty = difficulty >= 4;

  return {
    difficulty,
    model: CLOD_AI_MODEL,
    provider: 'Clod.io GPT OSS 120B route',
    budget: highDifficulty ? '$4.80 cap' : '$1.20 cap',
    latency: highDifficulty ? 'balanced reasoning window' : 'fast coding lane',
    rationale: highDifficulty
      ? 'Security-sensitive or compatibility-heavy work runs through GPT OSS 120B with a stricter budget cap.'
      : 'Moderate implementation risk still uses GPT OSS 120B through the lower-cost Clod lane.',
  };
};

export const mockGenerateCode = async (): Promise<CodeArtifact> => {
  await wait(520);
  return {
    title: 'transactionSigningGuard.ts',
    language: 'ts',
    summary:
      'Generated a narrow signing guard, rejected unsafe approval payloads, and added regression coverage hooks.',
    patch: `export function assertSafeTransaction(tx: PreparedTransaction) {
  if (!tx.chainId) throw new Error('Missing chainId');
  if (tx.approval === 'unbounded') throw new Error('Unbounded approval requires explicit user approval');
  if (tx.chainId !== tx.expectedChainId) throw new Error('Cross-chain replay risk');
  return tx;
}`,
  };
};

export const mockSandboxReview = async (attempt: number): Promise<ReviewResult> => {
  await wait(520);

  if (attempt === 0) {
    return {
      status: 'failed',
      summary: 'TREX sandbox found one missing rejection test for cross-chain payload replay.',
      tests: ['typecheck: passed', 'unit: failed', 'security-regression: failed'],
    };
  }

  return {
    status: 'passed',
    summary: 'Sandbox checks passed after adding replay rejection coverage and tightening signer guards.',
    tests: ['typecheck: passed', 'unit: passed', 'security-regression: passed'],
  };
};

export const mockRepair = async (attempt: number) => {
  await wait(440);
  return `Repair attempt ${attempt} added cross-chain replay coverage and normalized transaction validation errors.`;
};
