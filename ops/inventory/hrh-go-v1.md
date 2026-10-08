## Latest
- Branch `main` (only remote branch on disk). Last commit 2025-07-15: "add Location and Address files (#15)".

## Purpose
A private Go API for a school directory, teacher wishlists, admin, and public search, with domain value types for address and location. It is not a data-science artifact.

## Stack
Go (`go.mod`), `cmd/api/main.go`, Dockerfile, golangci-lint config, `.env.example`.

## Key modules
- `/home/user/hrh-go-v1/internal/shared/domain/location.go` — `Location` value type with validation and `DistanceTo`, which uses the Haversine formula and returns kilometers.
- `/home/user/hrh-go-v1/internal/shared/domain/address.go` — address value type.
- `/home/user/hrh-go-v1/internal/schooldirectory/service.go` — school directory service.
- `/home/user/hrh-go-v1/internal/publicsearch/service.go` — public search.

## Reusable for dsdk
- A4 — `/home/user/hrh-go-v1/internal/shared/domain/location.go` — validated coordinates and great-circle distance in km; a small geodesic reference.

## Evidence quality
- Low-medium. Domain tests exist (`address_test.go`, `location_test.go`) but were not run.

## Open questions
- Should this private repo be in the dsdk inventory at all?
