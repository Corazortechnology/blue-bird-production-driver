/**
 * Load test: POST /api/monitor/frame (multipart: driver_id, session_id, frame JPEG).
 * Requires: scripts/loadtest/frame.jpg (see README.md — curl placeholder image).
 *
 * Run from repo root:
 *   k6 run scripts/loadtest/monitor-frame-load.js
 *
 * Tune `stages` — start small; ML/fusion paths can OOM a single pod.
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

// Loaded once; k6 resolves paths relative to *this script's directory* (same folder as frame.jpg)
const jpeg = open('frame.jpg', 'b');

export const options = {
  stages: [
    { duration: '1m', target: 5 },
    { duration: '2m', target: 15 },
    { duration: '2m', target: 30 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<15000'],
  },
};

export default function () {
  const driverId = `loadtest-d-${__VU}`;
  const sessionId = `loadtest-s-${__VU}-${__ITER}`;

  const payload = {
    driver_id: driverId,
    session_id: sessionId,
    frame: http.file(jpeg, 'frame.jpg', 'image/jpeg'),
  };

  const res = http.post('https://api.corazor.com/api/monitor/frame', payload);

  check(res, {
    'status 200': (r) => r.status === 200,
  });

  // ~2 fps per VU — adjust sleep to mimic your app (e.g. 0.5 = 2 req/s per user)
  sleep(0.5);
}
