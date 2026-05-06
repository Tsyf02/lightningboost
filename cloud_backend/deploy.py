"""
LightningBoost deployment helper for AMD Cloud
"""
import subprocess
import sys
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_docker():
    """Check if Docker is installed"""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        logger.info("✅ Docker available")
        return True
    except subprocess.CalledProcessError:
        logger.error("❌ Docker not found")
        return False


def check_docker_compose():
    """Check if Docker Compose is installed"""
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        logger.info("✅ Docker Compose available")
        return True
    except subprocess.CalledProcessError:
        logger.error("❌ Docker Compose not found")
        return False


def build_images():
    """Build Docker images"""
    logger.info("📦 Building Docker images...")
    try:
        subprocess.run(["docker-compose", "build"], check=True)
        logger.info("✅ Images built successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Build failed: {e}")
        return False


def start_services():
    """Start all services"""
    logger.info("🚀 Starting services...")
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        logger.info("✅ Services started")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to start services: {e}")
        return False


def stop_services():
    """Stop all services"""
    logger.info("⛔ Stopping services...")
    try:
        subprocess.run(["docker-compose", "down"], check=True)
        logger.info("✅ Services stopped")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to stop services: {e}")
        return False


def view_logs():
    """View service logs"""
    try:
        subprocess.run(["docker-compose", "logs", "-f"])
    except KeyboardInterrupt:
        logger.info("📋 Logs stopped")


def status():
    """Show service status"""
    try:
        subprocess.run(["docker-compose", "ps"])
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to get status: {e}")


def main():
    """Main deployment workflow"""
    logger.info("🎯 LightningBoost Deployment Assistant")
    logger.info("=" * 50)
    
    # Check prerequisites
    if not check_docker() or not check_docker_compose():
        logger.error("❌ Missing prerequisites. Please install Docker and Docker Compose.")
        sys.exit(1)
    
    # Menu
    while True:
        print("\n📋 Deployment Menu:")
        print("1. Build images")
        print("2. Start services")
        print("3. Stop services")
        print("4. View logs")
        print("5. Show status")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            build_images()
        elif choice == "2":
            if build_images():
                start_services()
        elif choice == "3":
            stop_services()
        elif choice == "4":
            view_logs()
        elif choice == "5":
            status()
        elif choice == "6":
            logger.info("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    main()
