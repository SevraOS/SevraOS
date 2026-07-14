"""
HELIOS OS + SEVRA AI
AI Vitals Consumer (Section 12, 19)
"""

import json
import asyncio
import structlog
from redis.asyncio import Redis

from ai.config import ai_config
from ai.schemas.inference import InferenceRequest
from ai.anomaly_detection.engine import AnomalyDetector
from ai.risk_scoring.engine import RiskEngine
from ai.prediction_engine.aggregator import PredictionAggregator
from ai.alert_engine.generator import AlertEngine

logger = structlog.get_logger(__name__)

class AIVitalsConsumer:
    """
    Consumes Normalized Vitals, runs the AI pipeline, and publishes results.
    """
    def __init__(self):
        self.redis = Redis.from_url(ai_config.REDIS_URL, decode_responses=True)
        self.stream_key = "stream:normalized.events"
        self.consumer_group = "ai_inference_group"
        self.consumer_name = "ai_worker_1"
        self._running = False

    async def initialize(self):
        try:
            await self.redis.xgroup_create(self.stream_key, self.consumer_group, mkstream=True)
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error("redis_group_create_failed", error=str(e))

    async def run(self):
        self._running = True
        logger.info("ai_consumer_started", group=self.consumer_group)
        
        while self._running:
            try:
                # 1. Read from stream
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=ai_config.CONSUMER_BATCH_SIZE,
                    block=ai_config.CONSUMER_BLOCK_MS
                )
                
                if not messages:
                    continue
                    
                for stream, records in messages:
                    for record_id, data in records:
                        await self._process_message(record_id, data)
                        
            except Exception as e:
                logger.error("ai_consumer_loop_error", error=str(e))
                await asyncio.sleep(2)

    async def _process_message(self, record_id: str, data: dict):
        try:
            payload_str = data.get("payload")
            if not payload_str:
                return
                
            payload = json.loads(payload_str)
            if payload.get("event_type") != "vital":
                await self.redis.xack(self.stream_key, self.consumer_group, record_id)
                return
                
            patient_id = payload["patient_id"]
            metric = payload["metric"]
            value = payload["value"]
            
            # --- AI PIPELINE EXECUTION (Section 19) ---
            
            # 1. Anomaly Detection
            anomaly = AnomalyDetector.detect(patient_id, metric, value)
            
            # 2. Risk Scoring (Simplified input for demo)
            risk = RiskEngine.calculate_mews({"patient_id": patient_id, metric: value})
            
            # 3. ONNX Inference (Mocked features array)
            # inference_res = model_manager.execute("deterioration_v1", [value, risk.value])
            inference_res = {"prediction": min(value/150.0, 1.0), "confidence": 0.9}
            
            # 4. Aggregation
            prediction = PredictionAggregator.aggregate(
                patient_id, inference_res, risk, anomaly
            )
            
            # 5. Alert Evaluation
            alert = AlertEngine.evaluate(prediction)
            
            # 6. Publish to Dashboard WebSockets & Storage Streams
            await self._publish_results(patient_id, prediction, alert)
            
            # 7. Acknowledge message
            await self.redis.xack(self.stream_key, self.consumer_group, record_id)
            
        except Exception as e:
            logger.error("ai_processing_failed", record_id=record_id, error=str(e))

    async def _publish_results(self, patient_id, prediction, alert):
        """Publish events for Storage (Database Service) and Live WebSockets."""
        pipe = self.redis.pipeline()
        
        # For Dashboard WebSockets
        ws_channel = f"dashboard:channels:patient:{patient_id}:predictions"
        pipe.publish(ws_channel, prediction.model_dump_json())
        
        # For Database Service to persist
        pipe.xadd("stream:ai.predictions", {"payload": prediction.model_dump_json()})
        
        if alert:
            ws_alert_channel = f"dashboard:channels:patient:{patient_id}:alerts"
            pipe.publish(ws_alert_channel, alert.model_dump_json())
            pipe.xadd("stream:ai.alerts", {"payload": alert.model_dump_json()})
            
        await pipe.execute()
