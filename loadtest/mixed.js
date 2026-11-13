// Realistic mix (open model): PREDICT_RATE tickets/s plus one question every ASK_EVERY seconds.
// Used as the SLO baseline.
//   PREDICT_RATE=5 ASK_EVERY=4 DURATION=3m k6 run loadtest/mixed.js
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, params, tickets, questions, pick, SUMMARY_STATS } from './common.js';

const DURATION = __ENV.DURATION || '3m';

export const options = {
  summaryTrendStats: SUMMARY_STATS,
  scenarios: {
    predict: {
      executor: 'constant-arrival-rate', exec: 'predict',
      rate: Number(__ENV.PREDICT_RATE || 5), timeUnit: '1s', duration: DURATION,
      preAllocatedVUs: 10, maxVUs: 50,
    },
    ask: {
      executor: 'constant-arrival-rate', exec: 'ask',
      rate: 1, timeUnit: `${Number(__ENV.ASK_EVERY || 4)}s`, duration: DURATION,
      preAllocatedVUs: 4, maxVUs: 20,
    },
  },
  // Per-endpoint latency in the summary.
  thresholds: {
    'http_req_duration{endpoint:predict}': ['p(95)>=0'],
    'http_req_duration{endpoint:ask}': ['p(95)>=0'],
    'http_req_failed{endpoint:predict}': ['rate>=0'],
    'http_req_failed{endpoint:ask}': ['rate>=0'],
  },
};

export function predict() {
  const res = http.post(`${BASE_URL}/predict`, JSON.stringify({ text: pick(tickets) }),
    params('predict'));
  check(res, { 'predict 200': (r) => r.status === 200 });
}

export function ask() {
  const res = http.post(`${BASE_URL}/ask`, JSON.stringify({ question: pick(questions) }),
    params('ask', '120s'));
  check(res, { 'ask 200': (r) => r.status === 200 });
}
