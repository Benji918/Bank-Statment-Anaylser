module.export = {
    apps: [
        // FastAPI application
        {
            name: 'bank-statement-analyzer',
            script: 'venv/bin/uvicorn',
            interpreter: "./venv/bin/python",
            args: "main:app --host 0.0.0.0 --port 8000",
            watch: false,
            cwd:  "/root/Bank-Statment-Anaylser/",
            exec_mode: "fork"
        },

        // Celery process
        {
            name: "celery-worker",
            script: "venv/bin/celery",
            args: "-A app.tasks.celery_app worker -l info",
            interpreter: "./venv/bin/python",
            exec_mode: "fork",
            instances: 2,
            autorestart: true,
            watch: false,
            cwd: "/root/Bank-Statment-Anaylser/"

        }
    ]
}