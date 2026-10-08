## Latest
- Branch `main` (only remote branch on disk). Last commit 2025-09-30: "Implement Joined-Table Inheritance for User/Admin, Setup Service Layer, and Refactor Auth".

## Purpose
A private Spring Boot REST API with User and Admin entities using joined-table inheritance, a service layer, and authentication. It is not a data-science artifact.

## Stack
Java with Spring Boot 3.5.5 (parent POM), Spring Security, Spring Data repositories, Maven wrapper, Dockerfile and docker-compose, JUnit integration tests.

## Key modules
- `/home/user/helpteachers-api/src/main/java/net/helpteachers/api/model/User.java` and `Admin.java` — inheritance entities.
- `/home/user/helpteachers-api/src/main/java/net/helpteachers/api/service/UserService.java` — service layer.
- `/home/user/helpteachers-api/src/main/java/net/helpteachers/api/config/SecurityConfig.java` — security configuration.
- `/home/user/helpteachers-api/src/test/java/net/helpteachers/api/repository/UserRepositoryTest.java` — repository test.

## Reusable for dsdk
- none.

## Evidence quality
- Not assessed beyond the file list. An integration-test base class exists but was not run.

## Open questions
- Should this private repo be in the dsdk inventory at all?
