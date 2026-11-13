// Shared helpers for the k6 load tests. Data comes from the repo's held-out sets.
import { SharedArray } from 'k6/data';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
// Request params per endpoint (k6 0.52 has no object spread, so build them here).
export function params(endpoint, timeout) {
  const p = { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: endpoint } };
  if (timeout) p.timeout = timeout;
  return p;
}

export const tickets = new SharedArray('tickets', () =>
  open('../training/data/tickets_test.csv').split('\n').slice(1)
    .filter((l) => l.trim())
    .map((l) => (l.startsWith('"') ? l.slice(1, l.lastIndexOf('"')) : l.slice(0, l.lastIndexOf(','))))
);

export const questions = new SharedArray('questions', () =>
  open('../evaluation/golden_questions.jsonl').split('\n')
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l).question)
);

export const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

// Percentiles reported for every trend metric.
export const SUMMARY_STATS = ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'];
