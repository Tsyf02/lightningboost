"""
AI-powered system optimization recommendations
"""
import logging
import sys
import os
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import SystemRecommendation, SystemMetrics
from shared.prompts import get_system_tips_prompt
from shared.client import VLLMClient
from shared.config import VLLM_MODEL

logger = logging.getLogger(__name__)


class SystemOptimizer:
    """Generate AI-powered system optimization recommendations"""

    def __init__(self, vllm_client: VLLMClient = None):
        self.vllm_client = vllm_client or VLLMClient()

    def analyze_metrics(self, metrics: SystemMetrics) -> List[SystemRecommendation]:
        """Generate recommendations based on system metrics"""
        recommendations = []
        
        # High memory usage
        if metrics.ram_percent > 80:
            recommendations.append(SystemRecommendation(
                severity="high",
                recommendation=f"RAM usage is critical ({metrics.ram_percent:.1f}%). Consider closing applications or enabling virtual memory.",
                estimated_ram_freed_mb=500
            ))
        elif metrics.ram_percent > 60:
            recommendations.append(SystemRecommendation(
                severity="medium",
                recommendation=f"RAM usage is elevated ({metrics.ram_percent:.1f}%). Close unnecessary tabs/applications.",
                estimated_ram_freed_mb=200
            ))
        
        # High CPU usage
        if metrics.cpu_percent > 80:
            recommendations.append(SystemRecommendation(
                severity="high",
                recommendation=f"CPU usage is high ({metrics.cpu_percent:.1f}%). Consider offloading tasks to cloud.",
            ))
        
        # Low available memory
        if metrics.ram_available_mb < 500:
            recommendations.append(SystemRecommendation(
                severity="high",
                recommendation=f"Available RAM is critically low ({metrics.ram_available_mb:.0f}MB). Clean up memory immediately.",
                estimated_ram_freed_mb=metrics.ram_used_mb * 0.2  # estimate 20% freed
            ))
        
        # Top process-specific recommendations
        if metrics.top_processes:
            top_process = metrics.top_processes[0]
            if top_process[2] > 500:  # > 500MB
                recommendations.append(SystemRecommendation(
                    severity="medium",
                    recommendation=f"{top_process[0]} is using {top_process[2]:.0f}MB. Consider closing it if not needed.",
                    process_to_target=top_process[0],
                    estimated_ram_freed_mb=top_process[2]
                ))
        
        return recommendations

    def get_ai_recommendations(self, metrics: SystemMetrics) -> str:
        """Get AI-generated recommendations using vLLM"""
        try:
            if not self.vllm_client.health_check():
                logger.warning("vLLM not available, using rule-based recommendations")
                return self._get_rule_based_recommendations(metrics)
            
            prompt = get_system_tips_prompt(
                metrics.ram_percent,
                metrics.cpu_percent,
                metrics.top_processes
            )
            
            response = self.vllm_client.generate(
                prompt=prompt,
                model=VLLM_MODEL,
                max_tokens=256
            )
            return response or "System is running normally."
        except Exception as e:
            logger.error(f"Failed to get AI recommendations: {e}")
            return self._get_rule_based_recommendations(metrics)

    def _get_rule_based_recommendations(self, metrics: SystemMetrics) -> str:
        """Fallback rule-based recommendations"""
        recommendations = self.analyze_metrics(metrics)
        
        if not recommendations:
            return "✅ System is running smoothly! No optimization needed."
        
        tips = "🔧 Optimization Tips:\n"
        for rec in recommendations:
            if rec.severity == "high":
                tips += f"⚠️ {rec.recommendation}\n"
            else:
                tips += f"ℹ️ {rec.recommendation}\n"
        
        return tips
