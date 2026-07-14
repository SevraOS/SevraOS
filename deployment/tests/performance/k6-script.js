// HELIOS OS + SEVRA AI
// k6 Load Testing Framework (Section 17)

import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
    stages: [
        { duration: '30s', target: 1000 }, // Ramp up to 1000 users
        { duration: '1m', target: 1000 },  // Hold at 1000 users
        { duration: '30s', target: 0 },    // Ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<200'], // 95% of requests must complete below 200ms
        errors: ['rate<0.01'],            // Error rate must be strictly less than 1%
    },
};

const BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';
const TOKEN = 'mock_token';

export default function () {
    // 1. REST API Load Test
    let res = http.get(`${BASE_URL}/api/v1/patients`, {
        headers: { Authorization: `Bearer ${TOKEN}` },
    });
    
    let success = check(res, {
        'status is 200': (r) => r.status === 200,
    });
    errorRate.add(!success);
    
    sleep(1);

    // 2. WebSocket Stress Test
    let wsRes = ws.connect(`${WS_URL}/ws/stream?token=${TOKEN}`, function (socket) {
        socket.on('open', () => {
            socket.send(JSON.stringify({ action: 'subscribe', channel: 'patient:pt-123:vitals' }));
        });

        socket.on('message', (data) => {
            // Process incoming vital
        });

        socket.setTimeout(function () {
            socket.close();
        }, 10000); // Close after 10s
    });

    check(wsRes, { 'websocket status is 101': (r) => r && r.status === 101 });
}
