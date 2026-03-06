# REST API Reference

MADSci provides 7 manager services, each with a REST API built on FastAPI.
Click any manager below to view its full interactive API documentation.

## Manager APIs

| Manager | Default Port | API Docs | OpenAPI Spec |
|---------|:------------:|----------|--------------|
| Lab Manager | 8000 | [View API](./lab-manager.html) | [JSON](../api-specs/lab-manager.json) |
| Event Manager | 8001 | [View API](./event-manager.html) | [JSON](../api-specs/event-manager.json) |
| Experiment Manager | 8002 | [View API](./experiment-manager.html) | [JSON](../api-specs/experiment-manager.json) |
| Resource Manager | 8003 | [View API](./resource-manager.html) | [JSON](../api-specs/resource-manager.json) |
| Data Manager | 8004 | [View API](./data-manager.html) | [JSON](../api-specs/data-manager.json) |
| Workcell Manager | 8005 | [View API](./workcell-manager.html) | [JSON](../api-specs/workcell-manager.json) |
| Location Manager | 8006 | [View API](./location-manager.html) | [JSON](../api-specs/location-manager.json) |

## Common Endpoints

All managers expose these standard endpoints:

- `GET /health` -- Health check with status and version info
- `GET /settings` -- Current manager settings (secrets redacted)

## Live Documentation

When running locally, each manager also serves interactive docs at:

- **Swagger UI**: `http://localhost:{port}/docs`
- **ReDoc**: `http://localhost:{port}/redoc`

## Regenerating API Specs

To update the API specs after modifying endpoints:

```bash
just api-specs        # Export OpenAPI JSON specs
just rest-api-docs    # Generate Redoc HTML pages (includes api-specs)
```
