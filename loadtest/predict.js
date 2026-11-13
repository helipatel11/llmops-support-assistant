// /predict at a fixed ARRIVAL RATE (open model): requests arrive whether or not earlier
// ones finished, like real users. If the server cannot keep up, k6 reports
// dropped_iterations: that is the saturation signal.
//   RATE=50 DURATION=45s k6 run loadtest/predict.js
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, params, tickets, pick, SUMMARY_STATS } from './common.js';

const RATE = Number(__ENV.RATE || 10);

export const options = {
  summaryTrendStats: SUMMARY_STATS,
  scenarios: {
    predict: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: __ENV.DURATION || '45s',
      preAllocatedVUs: Math.max(10, RATE),
      maxVUs: Math.max(50, RATE * 4),
    },
  },
};

export default function () {
  const res = http.post(`${BASE_URL}/predict`, JSON.stringify({ text: pick(tickets) }),
    params('predict'));
  check(res, { 'status 200': (r) => r.status === 200 });
}
