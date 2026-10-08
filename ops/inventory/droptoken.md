## Latest
- Branch `master` (only remote branch on disk). Last commit 2021-02-15, Samuel Mahan: "Completed work for drop token game".

## Purpose
A Java Dropwizard shim for a Drop Token (connect-four-style) take-home game API. It covers game creation, moves, status, and player quit. The README says it was provided as a starting point by a third party. It is not a data-science artifact.

## Stack
Java 8, Maven (`pom.xml` and a shaded `dependency-reduced-pom.xml`), Dropwizard.

## Key modules
- `/home/user/samuelpmahan/droptoken/src/main/java/com/_98point6/droptoken/DropTokenResource.java` — REST resource.
- `/home/user/samuelpmahan/droptoken/src/main/java/com/_98point6/droptoken/handler/PostMoveHandler.java` — move handling.
- `/home/user/samuelpmahan/droptoken/src/main/java/com/_98point6/droptoken/model/common/Game.java` — game model.

## Reusable for dsdk
- none.

## Evidence quality
- Not assessed beyond the file list. It is take-home code that the README describes as a shim.

## Open questions
- Should this repo be excluded from the dsdk inventory entirely? It appears to be unrelated.
