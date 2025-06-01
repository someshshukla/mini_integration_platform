# Architecture Diagram

```mermaid
graph TD
    A[Client] --> B[CRM Service (Port 5000)]
    B --> C{Retry Logic}
    C -->|Success| D[Inventory Service (Port 5001)]
    C -->|Fail| E[Log Error]
    D --> F[Package Store]
    B --> G[Customer Store]
```
