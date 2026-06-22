.PHONY: backend-dev backend-test frontend-dev frontend-build check danger-check

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test:
	cd backend && python3 -m pytest tests

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

check: backend-test frontend-build

danger-check:
	find . \( -name '*.pt' -o -name '*.pth' -o -name '*.onnx' -o -name '*.mp4' -o -name '*.avi' -o -name '*.mov' -o -name '*.mkv' -o -name '*.webm' \) -not -path './frontend/node_modules/*' -print
