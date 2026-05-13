module.exports = {
  apps: [
    // ── Backend — FastAPI via uvicorn ─────────────────────────
    {
      name: 'backend',
      script: 'python3',
      args: '-m uvicorn main:app --host 0.0.0.0 --port 8000',
      cwd: './backend',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONIOENCODING: 'utf-8',
      },
    },
  ],
};
