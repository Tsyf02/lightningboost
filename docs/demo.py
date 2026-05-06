"""
LightningBoost Demo Script
Run this to test the full system locally
"""
import sys
import os
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from local_agent.monitor import SystemMonitor
from local_agent.router import TaskRouter
from local_agent.optimizer import SystemOptimizer
from shared.models import Task, SystemMetrics
from shared.config import TaskType, MONITOR_INTERVAL
from shared.client import VLLMClient, CloudClient


def demo_system_monitoring():
    """Demo 1: Monitor system metrics"""
    logger.info("\n" + "="*60)
    logger.info("📊 DEMO 1: System Monitoring")
    logger.info("="*60)
    
    monitor = SystemMonitor()
    
    for i in range(3):
        metrics = monitor.get_current_metrics()
        monitor.record_metrics(metrics)
        
        logger.info(f"\n📈 Sample {i+1}:")
        logger.info(f"   RAM:  {metrics.ram_percent:.1f}% ({metrics.ram_available_mb:.0f}MB available)")
        logger.info(f"   CPU:  {metrics.cpu_percent:.1f}%")
        logger.info(f"   Disk: {metrics.disk_percent:.1f}%")
        logger.info(f"   Processes: {metrics.process_count}")
        
        if metrics.top_processes:
            logger.info(f"   Top Process: {metrics.top_processes[0][0]} ({metrics.top_processes[0][2]:.0f}MB)")
        
        time.sleep(1)


def demo_task_routing():
    """Demo 2: Intelligent task routing"""
    logger.info("\n" + "="*60)
    logger.info("🔀 DEMO 2: Intelligent Task Routing")
    logger.info("="*60)
    
    monitor = SystemMonitor()
    router = TaskRouter()
    metrics = monitor.get_current_metrics()
    
    # Test different task types
    tasks = [
        (TaskType.LIGHTWEIGHT, "Simple calculation"),
        (TaskType.TEXT_GENERATION, "Generate a poem about AI"),
        (TaskType.IMAGE_CLASSIFICATION, "Classify image"),
        (TaskType.EMBEDDING, "Create embeddings for text"),
    ]
    
    for task_type, description in tasks:
        task = router.create_task(task_type, description, {})
        decision = router.route_task(task, metrics)
        
        logger.info(f"\n📋 Task: {description}")
        logger.info(f"   Type: {task_type.value}")
        logger.info(f"   Routing: {decision.location.value.upper()}")
        logger.info(f"   Confidence: {decision.confidence:.0%}")
        logger.info(f"   Reasoning: {decision.reasoning}")


def demo_system_optimization():
    """Demo 3: AI-powered recommendations"""
    logger.info("\n" + "="*60)
    logger.info("💡 DEMO 3: AI System Recommendations")
    logger.info("="*60)
    
    monitor = SystemMonitor()
    optimizer = SystemOptimizer()
    metrics = monitor.get_current_metrics()
    
    logger.info(f"\n📊 Current Metrics:")
    logger.info(f"   RAM: {metrics.ram_percent:.1f}%")
    logger.info(f"   CPU: {metrics.cpu_percent:.1f}%")
    
    # Get recommendations
    recommendations = optimizer.analyze_metrics(metrics)
    
    if recommendations:
        logger.info(f"\n🎯 Recommendations ({len(recommendations)}):")
        for rec in recommendations:
            logger.info(f"   [{rec.severity.upper()}] {rec.recommendation}")
    else:
        logger.info("\n✅ No issues detected. System running smoothly!")


def demo_cloud_backend_status():
    """Demo 4: Check cloud backend connectivity"""
    logger.info("\n" + "="*60)
    logger.info("☁️ DEMO 4: Cloud Backend Status")
    logger.info("="*60)
    
    cloud_client = CloudClient()
    vllm_client = VLLMClient()
    
    # Check cloud backend
    logger.info("\nChecking Cloud Backend...")
    if cloud_client.get_health():
        logger.info("✅ Cloud Backend: HEALTHY")
    else:
        logger.warning("⚠️ Cloud Backend: OFFLINE (not running)")
    
    # Check vLLM
    logger.info("\nChecking vLLM Endpoint...")
    if vllm_client.health_check():
        logger.info("✅ vLLM: HEALTHY")
        models = vllm_client.list_models()
        if models:
            logger.info(f"   Available models: {len(models)}")
    else:
        logger.warning("⚠️ vLLM: OFFLINE (not running)")


def main():
    """Run all demos"""
    logger.info("\n")
    logger.info("╔" + "="*58 + "╗")
    logger.info("║" + " "*10 + "🚀 LIGHTNINGBOOST DEMO SCRIPT" + " "*18 + "║")
    logger.info("║" + " "*8 + "AI Task Router for Hybrid Local-Cloud Computing" + " "*4 + "║")
    logger.info("╚" + "="*58 + "╝")
    
    try:
        # Run demos
        demo_system_monitoring()
        demo_task_routing()
        demo_system_optimization()
        demo_cloud_backend_status()
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("✅ DEMO COMPLETED")
        logger.info("="*60)
        
        logger.info("\n📚 Next Steps:")
        logger.info("1. Start cloud backend: python cloud_backend/server.py")
        logger.info("2. Start frontend: streamlit run frontend/app.py")
        logger.info("3. Start local agent: python local_agent/main.py")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
