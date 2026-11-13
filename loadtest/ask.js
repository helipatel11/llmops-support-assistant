// /ask at fixed CONCURRENCY (closed model): each virtual user waits for its answer before
// asking again. Shows whether more concurrency buys more throughput, or only longer queues.
//   VUS=2 DURATION=90s k6 run loadtest/ask.js
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, params, questions, pick, SUMMARY_STATS } from './common.js';

export const options = {
  summaryTrendStats: SUMMARY_STATS,
  scenarios: {
    ask: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 1),
      duration: __ENV.DURATION || '90s',
    },
  },
};

export default function () {
  const res = http.post(`${BASE_URL}/ask`, JSON.stringify({ question: pick(questions) }),
    params('ask', '120s'));
  check(res, { 'status 200': (r) => r.status === 200 });
}
