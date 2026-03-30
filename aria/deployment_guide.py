#!/usr/bin/env python3
"""
ARIA Deployment Helper

Production deployment guide and automation script.
Handles local, Docker, and cloud deployment scenarios.
"""

import sys
from pathlib import Path
from typing import Dict, List
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


class DeploymentMode(str, Enum):
    """Supported deployment modes."""
    LOCAL = "local"                    # Single machine
    DOCKER = "docker"                 # Containerized
    KUBERNETES = "kubernetes"         # K8s cluster
    SERVERLESS = "serverless"         # Lambda/Cloud Functions
    HYBRID = "hybrid"                 # On-prem + cloud


class DeploymentGuide:
    """Production deployment guidance."""
    
    DEPLOYMENT_PROFILES = {
        "development": {
            "mode": DeploymentMode.LOCAL,
            "concurrency": 1,
            "memory_limit_gb": 4,
            "cache_mode": "memory",
            "monitoring": "minimal",
            "autoscale": False,
            "description": "Single machine development"
        },
        "production-local": {
            "mode": DeploymentMode.LOCAL,
            "concurrency": 4,
            "memory_limit_gb": 16,
            "cache_mode": "disk",
            "monitoring": "standard",
            "autoscale": False,
            "description": "High-performance single machine (Mac Studio)"
        },
        "production-docker": {
            "mode": DeploymentMode.DOCKER,
            "concurrency": 8,
            "memory_limit_gb": 32,
            "cache_mode": "distributed",
            "monitoring": "comprehensive",
            "autoscale": True,
            "description": "Containerized multi-instance deployment"
        },
        "production-k8s": {
            "mode": DeploymentMode.KUBERNETES,
            "concurrency": 16,
            "memory_limit_gb": 64,
            "cache_mode": "distributed",
            "monitoring": "full",
            "autoscale": True,
            "description": "Kubernetes cluster (cloud-native)"
        },
    }
    
    DEPLOYMENT_SCRIPTS = {
        "local": """
# 1. Install ARIA in production mode
pip install -e .

# 2. Pre-load model
aria analyze "What is machine learning?"

# 3. Start API server
aria-server --host 0.0.0.0 --port 8000 --workers 4

# 4. Run CLI interface
aria
""",
        "docker": """
# 1. Build Docker image
docker build -t aria:latest .

# 2. Run container with GPU access
docker run -d \\
  --name aria-server \\
  -p 8000:8000 \\
  -v ~/.cache/huggingface:/root/.cache/huggingface \\
  -v ./models_cache:/app/models_cache \\
  aria:latest \\
  aria-server --host 0.0.0.0 --port 8000

# 3. Check logs
docker logs -f aria-server

# 4. Health check
curl http://localhost:8000/health
""",
        "kubernetes": """
# 1. Create namespace
kubectl create namespace aria

# 2. Create ConfigMap for models
kubectl create configmap aria-models \\
  --from-file=models_cache/ \\
  -n aria

# 3. Deploy ARIA service
kubectl apply -f k8s/aria-deployment.yaml -n aria

# 4. Expose service
kubectl expose deployment aria-server \\
  --type=LoadBalancer \\
  --port=8000 \\
  -n aria

# 5. Monitor deployment
kubectl logs -f deployment/aria-server -n aria
kubectl top pods -n aria
""",
    }
    
    DOCKERFILE_TEMPLATE = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    libopenblas-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 aria
USER aria

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["aria-server", "--host", "0.0.0.0", "--port", "8000"]
"""
    
    K8S_DEPLOYMENT_TEMPLATE = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aria-server
  labels:
    app: aria
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aria
  template:
    metadata:
      labels:
        app: aria
    spec:
      containers:
      - name: aria
        image: aria:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 5
        volumeMounts:
        - name: model-cache
          mountPath: /app/models_cache
      volumes:
      - name: model-cache
        configMap:
          name: aria-models
---
apiVersion: v1
kind: Service
metadata:
  name: aria-service
spec:
  type: LoadBalancer
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  selector:
    app: aria
"""
    
    @classmethod
    def print_deployment_guide(cls, mode: str = "production-docker"):
        """Print deployment guide for given mode."""
        if mode not in cls.DEPLOYMENT_PROFILES:
            console.print(f"[red]Unknown mode: {mode}[/red]")
            console.print(f"Available modes: {list(cls.DEPLOYMENT_PROFILES.keys())}")
            return
        
        profile = cls.DEPLOYMENT_PROFILES[mode]
        
        console.print(Panel(
            f"[bold cyan]ARIA Deployment Guide: {mode.upper()}[/bold cyan]\n"
            f"{profile['description']}",
            border_style="cyan"
        ))
        
        # Configuration table
        config_items = [
            ("Deployment Mode", profile["mode"].value),
            ("Concurrency", f"{profile['concurrency']} workers"),
            ("Memory Limit", f"{profile['memory_limit_gb']}GB"),
            ("Cache Mode", profile["cache_mode"]),
            ("Monitoring", profile["monitoring"]),
            ("Auto-scaling", "Enabled" if profile["autoscale"] else "Disabled"),
        ]
        
        console.print("\n[bold]Configuration[/bold]")
        for key, value in config_items:
            console.print(f"  {key:<20} {value}")
        
        # Deployment steps
        console.print("\n[bold]Deployment Steps[/bold]")
        console.print("-" * 70)
        
        if mode == "production-local":
            steps = cls.DEPLOYMENT_SCRIPTS["local"].strip().split("\n")
        elif mode == "production-docker":
            steps = cls.DEPLOYMENT_SCRIPTS["docker"].strip().split("\n")
        elif mode == "production-k8s":
            steps = cls.DEPLOYMENT_SCRIPTS["kubernetes"].strip().split("\n")
        else:
            steps = ["Custom deployment"]
        
        for i, step in enumerate(steps, 1):
            if not step.strip():
                continue
            if step.startswith("#"):
                console.print(f"\n  [bold]{step}[/bold]")
            else:
                console.print(f"  [dim]{step}[/dim]")
        
        # Verification checklist
        console.print("\n[bold]Post-Deployment Checklist[/bold]")
        console.print("-" * 70)
        checklist = [
            "Service starts without errors",
            "Health endpoint responds (GET /health)",
            "Can process basic query",
            "Metrics are being recorded",
            "Model cache is functional",
            "Memory pressure is acceptable",
            "Response latency is <2s for simple queries",
        ]
        for item in checklist:
            console.print(f"  ☐ {item}")
    
    @classmethod
    def generate_dockerfile(cls, output_path: Path = None):
        """Generate production Dockerfile."""
        if output_path is None:
            output_path = Path("Dockerfile.prod")
        
        output_path.write_text(cls.DOCKERFILE_TEMPLATE.lstrip())
        console.print(f"[green]✓[/green] Dockerfile generated: {output_path}")
    
    @classmethod
    def generate_k8s_manifest(cls, output_path: Path = None):
        """Generate Kubernetes manifest."""
        if output_path is None:
            output_path = Path("k8s/aria-deployment.yaml")
            output_path.parent.mkdir(exist_ok=True)
        
        output_path.write_text(cls.K8S_DEPLOYMENT_TEMPLATE.lstrip())
        console.print(f"[green]✓[/green] K8s manifest generated: {output_path}")
    
    @classmethod
    def print_all_modes(cls):
        """Print all available deployment modes."""
        console.print(Panel(
            "[bold cyan]Available Deployment Modes[/bold cyan]",
            border_style="cyan"
        ))
        
        for mode_name, profile in cls.DEPLOYMENT_PROFILES.items():
            console.print(f"\n[bold]{mode_name}[/bold]")
            console.print(f"  {profile['description']}")
            console.print(f"  Mode: {profile['mode'].value} | Workers: {profile['concurrency']} | Memory: {profile['memory_limit_gb']}GB")


def show_help():
    """Show deployment helper usage."""
    DeploymentGuide.print_all_modes()
    
    console.print("\n[bold]Usage[/bold]")
    console.print("-" * 70)
    console.print("""
  python deployments/deployment_guide.py <mode>
  
Available modes:
  development            - Single machine development
  production-local       - High-performance local deployment
  production-docker      - Containerized multi-instance
  production-k8s         - Kubernetes cluster

Examples:
  python deployments/deployment_guide.py production-local
  python deployments/deployment_guide.py production-docker
  python deployments/deployment_guide.py production-k8s
    """)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ARIA Deployment Helper")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=list(DeploymentGuide.DEPLOYMENT_PROFILES.keys()),
        help="Deployment mode"
    )
    parser.add_argument("--dockerfile", action="store_true", help="Generate Dockerfile")
    parser.add_argument("--k8s", action="store_true", help="Generate K8s manifest")
    parser.add_argument("--all", action="store_true", help="Show all modes")
    
    args = parser.parse_args()
    
    if args.all or (not args.mode and not args.dockerfile and not args.k8s):
        show_help()
    else:
        if args.dockerfile:
            DeploymentGuide.generate_dockerfile()
        if args.k8s:
            DeploymentGuide.generate_k8s_manifest()
        if args.mode:
            DeploymentGuide.print_deployment_guide(args.mode)
