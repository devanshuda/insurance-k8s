Comprehensive Guide: Building and Deploying a Microservices Application on Kubernetes
=====================================================================================

Table of Contents
-----------------

1.  [Project Overview and Learning Objectives](#1-project-overview-and-learning-objectives)
    
2.  [Architectural Design](#2-architectural-design)
    
3.  [Prerequisites and Environment Setup](#3-prerequisites-and-environment-setup)
    
4.  [Project Structure](#4-project-structure)
    
5.  [Component 1: The Redis Cache](#5-component-1-the-redis-cache)
    
6.  [Component 2: The Insurance API](#6-component-2-the-insurance-api)
    
7.  [Component 3: The Frontend UI](#7-component-3-the-frontend-ui)
    
8.  [Kubernetes Manifests Deep Dive](#8-kubernetes-manifests-deep-dive)
    
9.  [Deployment Execution Strategy](#9-deployment-execution-strategy)
    
10.  [Troubleshooting and Debugging (Session History)](#10-troubleshooting-and-debugging-session-history)
    
11.  [Advanced Kubernetes Operations](#11-advanced-kubernetes-operations)
    
12.  [Cleanup and Teardown](#12-cleanup-and-teardown)
    

1\. Project Overview and Learning Objectives
--------------------------------------------

The purpose of this project is to provide a hands-on, localized environment to learn Kubernetes (k8s) orchestration using a real-world microservices architecture.

We are building a simulated **Insurance Application System**. The workflow dictates that a user selects a catalog item (Car, Dog, Child), fills out basic applicant details, and reviews a dynamically generated price quote based on their selection. The data is temporarily cached until the user confirms the purchase.

### Key Kubernetes Concepts Covered:

*   **Containerization:** Building lightweight Docker images for Python applications.
    
*   **Deployments:** Managing stateless application replicas and defining container specs.
    
*   **Services:** Abstracting pod IP addresses to provide stable internal DNS and networking.
    
*   **State Management:** Integrating a stateful cache (Redis) with stateless APIs.
    
*   **Local Orchestration:** Using kind (Kubernetes in Docker) to simulate a multi-node cluster locally without cloud costs.
    
*   **Debugging:** Utilizing kubectl logs and rollout restarts to fix live application errors.
    

2\. Architectural Design
------------------------

To properly demonstrate distributed systems, this application is decoupled into three distinct tiers:

1.  **Frontend Web UI (Flask):** A Python Flask application responsible strictly for serving HTML pages and routing user traffic. It holds no business logic and relies entirely on the API to process data.
    
2.  **Insurance Business API (FastAPI):** A high-performance Python FastAPI service. It acts as the brain of the operation, validating incoming payloads, calculating fixed pricing (Car=2000, Dog=1000, Child=750), generating unique session IDs, and communicating with the cache.
    
3.  **In-Memory Cache (Redis):** An official Redis container used to store the user's unconfirmed application data with a Time-To-Live (TTL). This simulates how real-world e-commerce sites hold cart data before checkout.
    

### Data Flow Diagram

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   [ User Browser ] ---> (Port 5000) ---> [ Frontend Pod ]                                             |                                        (HTTP POST)                                             v                                     [ API Service ]                                             |                                        (TCP 6379)                                             v                                     [ Redis Cache ]   `

3\. Prerequisites and Environment Setup
---------------------------------------

To execute this project, specific DevOps tools must be installed. This environment utilizes Docker to act as the foundational hardware for the Kubernetes nodes.

*   **Docker Desktop:** The underlying container engine. Must be actively running in the background.
    
*   **Go (Golang):** (Optional but recommended) Used to compile kind from source if package managers are unavailable.
    
*   **kind (Kubernetes in Docker):** A tool for running local Kubernetes clusters using Docker container "nodes".
    
*   **kubectl:** The Kubernetes command-line tool, used to communicate with the cluster's API server.
    

**Installation (General Unix/Linux/macOS pattern):**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Verify Docker  docker --version  # Verify Kind  kind --version  # Verify Kubectl  kubectl version --client   `

4\. Project Structure
---------------------

The project relies on strict separation of concerns. Create the following directory tree on your local machine:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   insurance-k8s/  │  ├── api/  │   ├── main.py  │   └── Dockerfile  │  ├── frontend/  │   ├── app.py  │   ├── templates/  │   │   ├── catalog.html  │   │   ├── form.html  │   │   └── confirm.html  │   └── Dockerfile  │  └── k8s/      ├── redis.yaml      ├── api.yaml      └── frontend.yaml   `

5\. Component 1: The Redis Cache
--------------------------------

Unlike the Frontend and API, we do not need to write code for Redis. We pull the official image from Docker Hub. Redis operates on port 6379. The API will connect to it using the Kubernetes internal DNS name (which matches the Service name defined in the YAML files).

6\. Component 2: The Insurance API
----------------------------------

The API handles the core business logic. It relies on the redis python library to store application state.

### api/main.py

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   from fastapi import FastAPI, HTTPException  from pydantic import BaseModel  import redis  import uuid  import os  import json  app = FastAPI()  # Connect to Redis using the Kubernetes service DNS name  # Fallback to 'redis-service' if env var is missing  REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")  r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)  PRICING = {      "car": 2000,      "dog": 1000,      "child": 750  }  class ApplicationData(BaseModel):      catalog_item: str      name: str      address: str      item_age: int      years_of_insurance: int  @app.post("/api/apply")  def create_application(data: ApplicationData):      if data.catalog_item not in PRICING:          raise HTTPException(status_code=400, detail="Invalid catalog item")      app_id = str(uuid.uuid4())      total_price = PRICING[data.catalog_item]      payload = data.model_dump()      payload["total_price"] = total_price      payload["status"] = "Pending"      # Store in Redis for 1 hour (3600 seconds)      r.setex(app_id, 3600, json.dumps(payload))      return {"application_id": app_id}  @app.get("/api/application/{app_id}")  def get_application(app_id: str):      data = r.get(app_id)      if not data:          raise HTTPException(status_code=404, detail="Application not found")      return json.loads(data)  @app.post("/api/confirm/{app_id}")  def confirm_application(app_id: str):      data = r.get(app_id)      if not data:          raise HTTPException(status_code=404, detail="Application not found")      payload = json.loads(data)      payload["status"] = "Confirmed"      # Simulating saving to a persistent DB by removing from cache      r.delete(app_id)      return {"message": "Insurance Confirmed Successfully!", "details": payload}   `

### api/Dockerfile

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   FROM python:3.11-slim  WORKDIR /app  RUN pip install fastapi uvicorn redis pydantic  COPY main.py .  EXPOSE 8000  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]   `

7\. Component 3: The Frontend UI
--------------------------------

The frontend uses Flask and Jinja2 templates to render the user interface.

### frontend/app.py

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   from flask import Flask, render_template, request, redirect, url_for  import requests  import os  app = Flask(__name__)  # Relying on internal K8s DNS to resolve the API  API_URL = os.getenv("API_URL", "http://insurance-api-service:8000")  @app.route('/')  def catalog():      return render_template('catalog.html')  @app.route('/form/')  def form(item):      return render_template('form.html', item=item)  @app.route('/submit-form', methods=['POST'])  def submit_form():      payload = {          "catalog_item": request.form['catalog_item'],          "name": request.form['name'],          "address": request.form['address'],          "item_age": int(request.form['item_age']),          "years_of_insurance": int(request.form['years_of_insurance'])      }      response = requests.post(f"{API_URL}/api/apply", json=payload)      if response.status_code == 200:          app_id = response.json().get("application_id")          return redirect(url_for('confirm', app_id=app_id))      return "Error processing request", 400  @app.route('/confirm/')  def confirm(app_id):      response = requests.get(f"{API_URL}/api/application/{app_id}")      if response.status_code == 200:          data = response.json()          return render_template('confirm.html', app_id=app_id, data=data)      return "Application expired or not found", 404  @app.route('/final-confirm/', methods=['POST'])  def final_confirm(app_id):      response = requests.post(f"{API_URL}/api/confirm/{app_id}")      if response.status_code == 200:          return "  Success! Your insurance policy is confirmed. ============================================  [Go Home]('/')"      return "Failed to confirm insurance", 400  if __name__ == '__main__':      app.run(host='0.0.0.0', port=5000)   `

### HTML Templates (frontend/templates/)

**catalog.html**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   Select Insurance Catalog ========================  [Car Insurance (INR 2000)](/form/car)  [Dog Insurance (INR 1000)](/form/dog)  [Child Insurance (INR 750)](/form/child)   `

**form.html**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   Apply for {{ item | upper }} Insurance ======================================            Name:            Address:            Age of {{ item }}:            Years of Insurance:            Review Application   `

**confirm.html**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   Confirm Your Selection ======================  **Category:** {{ data.catalog_item }}  **Name:** {{ data.name }}  **Address:** {{ data.address }}  **Item Age:** {{ data.item_age }}  **Duration:** {{ data.years_of_insurance }} Years  Total Fixed Price: INR {{ data.total_price }} ---------------------------------------------      Confirm & Buy   `

### frontend/Dockerfile

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   FROM python:3.11-slim  WORKDIR /app  RUN pip install flask requests  COPY . .  EXPOSE 5000  CMD ["python", "app.py"]   `

8\. Kubernetes Manifests Deep Dive
----------------------------------

Kubernetes uses YAML files to declare the desired state of the infrastructure.

### Understanding the Specs

*   **Deployment:** Ensures that a specified number of replica Pods (containers) are running at any given time.
    
*   **imagePullPolicy: Never:** This is a crucial setting for local kind development. It forces Kubernetes to look for the Docker image locally within the cluster node rather than attempting to download it from the public internet.
    
*   **Service:** Provides a static IP and DNS name for the pods, which might be constantly created or destroyed.
    

### k8s/redis.yaml

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   apiVersion: apps/v1  kind: Deployment  metadata:    name: redis-deployment  spec:    replicas: 1    selector:      matchLabels:        app: redis    template:      metadata:        labels:          app: redis      spec:        containers:        - name: redis          image: redis:7-alpine          ports:          - containerPort: 6379  ---  apiVersion: v1  kind: Service  metadata:    name: redis-service  spec:    selector:      app: redis    ports:      - protocol: TCP        port: 6379        targetPort: 6379   `

### k8s/api.yaml

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   apiVersion: apps/v1  kind: Deployment  metadata:    name: insurance-api-deployment  spec:    replicas: 2    selector:      matchLabels:        app: insurance-api    template:      metadata:        labels:          app: insurance-api      spec:        containers:        - name: insurance-api          image: insurance-api:latest          imagePullPolicy: Never          ports:          - containerPort: 8000          env:          - name: REDIS_HOST            value: "redis-service" # Resolves to the Service above  ---  apiVersion: v1  kind: Service  metadata:    name: insurance-api-service  spec:    selector:      app: insurance-api    ports:      - protocol: TCP        port: 8000        targetPort: 8000   `

### k8s/frontend.yaml

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   apiVersion: apps/v1  kind: Deployment  metadata:    name: frontend-deployment  spec:    replicas: 2    selector:      matchLabels:        app: frontend    template:      metadata:        labels:          app: frontend      spec:        containers:        - name: frontend          image: frontend-app:latest          imagePullPolicy: Never          ports:          - containerPort: 5000          env:          - name: API_URL            value: "http://insurance-api-service:8000"  ---  apiVersion: v1  kind: Service  metadata:    name: frontend-service  spec:    selector:      app: frontend    ports:      - protocol: TCP        port: 5000        targetPort: 5000   `

9\. Deployment Execution Strategy
---------------------------------

This sequence is required to boot the application from source code to a live Kubernetes instance.

**Step 1: Initialize the Cluster**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kind create cluster --name insurance   `

_Creates a Docker container that acts as a full K8s node._

**Step 2: Build Application Images**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   docker build -t insurance-api:latest ./api  docker build -t frontend-app:latest ./frontend   `

_Compiles the Python code into runnable Docker containers._

**Step 3: Sideload Images to Kind**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kind load docker-image insurance-api:latest --name insurance  kind load docker-image frontend-app:latest --name insurance   `

_Transfers the local images into the virtual cluster's internal registry._

**Step 4: Apply Infrastructure Code**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kubectl apply -f ./k8s/   `

_Submits the YAML configurations to the Kubernetes Control Plane._

**Step 5: Verify Deployment Health**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kubectl get pods -w   `

_Watch the pods transition from ContainerCreating to Running._

**Step 6: Expose the Application to Host**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kubectl port-forward svc/frontend-service 5000:5000   `

_Bridges the host machine's port 5000 directly into the cluster's frontend service. The app is now accessible at http://localhost:5000._

10\. Troubleshooting and Debugging (Session History)
----------------------------------------------------

During the live deployment of this architecture, we encountered and successfully resolved several real-world debugging scenarios. Documenting these is vital for understanding K8s operations.

### Incident 1: Pods Stuck in Error State

**Symptom:** After applying the manifests, kubectl get pods showed the frontend pods in Error or CrashLoopBackOff state.**Diagnosis Command Used:** kubectl logs -l app=frontend**Root Cause A (Image Loading):** Images were loaded into a cluster named education, but the cluster was created as insurance. The pods could not pull the image.**Root Cause B (Code Bug):** The Python code included an invalid import (render\_html from flask), causing an immediate crash on boot.**Resolution:** Code was corrected, image rebuilt, and pods restarted using kubectl rollout restart deployment frontend-deployment.

### Incident 2: Internal Server Error (HTTP 500) on UI Click

**Symptom:** The web app loaded successfully, but clicking a catalog button (e.g., Car) resulted in a Flask 500 error page.**Diagnosis Command Used:** kubectl logs -l app=frontend**Log Output:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   jinja2.exceptions.UndefinedError: 'data' is undefined    File "/app/templates/form.html", line 2, in top-level template code        **Category:** {{ data.catalog_item }}   `

**Root Cause:** A templating error. Code intended for the confirm.html page (which receives the data variable) was accidentally placed in form.html (which does not receive that variable).**Resolution:** 1. HTML templates were corrected.2. The image was rebuilt using --no-cache to ensure strict layer invalidation.3. The image was reloaded into kind.4. The deployment was restarted via kubectl rollout restart.

11\. Advanced Kubernetes Operations
-----------------------------------

With a healthy cluster, one can execute advanced administrative commands.

### Interacting with Stateful Pods (Exec)

To verify data is actually being cached, you can open a shell directly inside the running Redis container:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`# 1. Get the exact pod name  kubectl get pods -l app=redis  # 2. Exec into the pod  kubectl exec -it  -- redis-cli  # 3. View cached keys inside Redis  127.0.0.1:6379> keys *  127.0.0.1:6379> get` 

### Dynamic Scaling

Kubernetes allows instantaneous horizontal scaling. To handle simulated heavy web traffic:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kubectl scale deployment frontend-deployment --replicas=5   `

Running kubectl get pods will instantly show 5 frontend containers running. The K8s Service automatically load-balances traffic among all 5.

### Testing Self-Healing

Kubernetes constantly monitors state. If a container crashes, K8s revives it.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`kubectl delete pod` 

Immediately running kubectl get pods will reveal K8s terminating the deleted pod while concurrently spinning up a fresh one to maintain the desired replica count defined in the YAML.

12\. Cleanup and Teardown
-------------------------

Because kind provisions everything within Docker, teardown is exceptionally clean and does not leave residual files or background services running on the host OS.

To destroy the cluster, network rules, and all associated container data:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   kind delete cluster --name insurance   `