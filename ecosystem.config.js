module.export = {
    apps: [
        {
            name: "celery-worker",
            script: "venv/bin/celery",
            args: "-A app.tasks.celery_app worker -l info",
            interpreter: "./venv/bin/python",
            exec_mode: "fork",
            instances: 2,
            autorestart: true,
            watch: false,
            cwd: "/root/Bank-Statment-Anaylser/",

        }
    ]
}