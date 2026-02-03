# ADR 001: Monorepo Structure

**Status:** Accepted
**Date:** 2025-11-15
**Decision Makers:** Music Tools Team
**Technical Story:** Consolidate multiple repositories into monorepo

## Context

The Music Tools project initially consisted of three separate applications, each maintained in its own directory with significant code duplication:

1. **Music Tools** - Spotify/Deezer playlist management
2. **Tag Country Origin Editor** - AI-powered music tagging
3. **EDM Scraper** - Electronic music blog scraping

### Problems with Previous Structure

1. **Code Duplication:** Approximately 70% code duplication across projects
   - Each app had its own configuration management
   - Duplicate database operations
   - Redundant authentication implementations
   - Repeated utility functions

2. **Maintenance Overhead:**
   - Bug fixes needed to be applied to multiple codebases
   - Security updates required changes in multiple places
   - Inconsistent implementations of similar functionality

3. **Testing Challenges:**
   - No unified testing framework
   - Inconsistent test coverage across projects
   - Difficult to test cross-project integrations

4. **Development Inefficiency:**
   - Developers needed to understand multiple codebases
   - No shared standards or tooling
   - Difficult to share improvements across projects

5. **Deployment Complexity:**
   - Each app had different deployment procedures
   - No unified CI/CD pipeline
   - Difficult to ensure consistency across deployments

## Decision

We will adopt a **monorepo structure** with the following organization:

```
Music Tools Dev/
├── apps/                   # End-user applications
│   ├── music-tools/
│   ├── tag-editor/
│   └── edm-scraper/
├── packages/               # Shared libraries
│   └── common/
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── .github/workflows/      # CI/CD
```

### Key Architectural Decisions

1. **Separation of Apps and Packages:**
   - `apps/` for end-user facing applications
   - `packages/` for shared libraries
   - Clear dependency flow (apps depend on packages, not vice versa)

2. **Shared Common Library:**
   - Consolidate all shared code in `packages/common`
   - Modules: config, database, auth, cli, utils, metadata, api
   - Test coverage expanding (current: ~35%, target: 80%+)

3. **Workspace Configuration:**
   - Single `pyproject.toml` for unified tooling
   - Shared configuration for pytest, black, isort, mypy
   - Consistent code quality standards

4. **Unified CI/CD:**
   - Single GitHub Actions workflow
   - Parallel testing of all apps
   - Conditional job execution based on changed files

5. **Independent Installability:**
   - Each app can be installed independently
   - Apps depend on shared packages via setup.py
   - Use editable installs for development

## Consequences

### Positive

1. **Code Reuse:**
   - 60-75% reduction in code across applications
   - Single source of truth for common functionality
   - Easier to maintain and update shared code

2. **Consistency:**
   - Unified code style and quality standards
   - Consistent authentication and configuration
   - Standardized error handling and logging

3. **Simplified Testing:**
   - Unified test framework across all projects
   - Single command to run all tests
   - Easy to test cross-project integrations

4. **Better Developer Experience:**
   - Single repository to clone and setup
   - Shared development tools and standards
   - Clear structure and organization

5. **Atomic Changes:**
   - Changes across apps and packages in single commit
   - Guaranteed compatibility
   - Easier code review process

6. **Streamlined CI/CD:**
   - Single workflow for all applications
   - Parallel testing for faster feedback
   - Easier to maintain and update

7. **Improved Documentation:**
   - Centralized documentation
   - Easier to maintain consistency
   - Better discoverability

### Negative

1. **Repository Size:**
   - Larger repository than individual projects
   - Mitigation: Use .gitignore, clean caches regularly

2. **Build Times:**
   - Potentially longer if all tests run on every change
   - Mitigation: Conditional job execution in CI/CD

3. **Learning Curve:**
   - Developers need to understand monorepo structure
   - Mitigation: Comprehensive documentation (WORKSPACE.md)

4. **Coordination:**
   - Changes to shared packages affect all apps
   - Mitigation: Comprehensive testing, versioning strategy

5. **Permissions:**
   - All developers have access to all code
   - Mitigation: Use CODEOWNERS for sensitive areas

### Neutral

1. **Migration Effort:**
   - One-time effort to reorganize code
   - Required creating shared library
   - Updating imports and dependencies

2. **Tooling:**
   - Need to configure workspace-level tools
   - One-time setup of CI/CD pipeline

## Implementation Plan

### Phase 1: Create Shared Library ✅ COMPLETED

- [x] Extract common code from all applications
- [x] Create `packages/common` structure
- [x] Implement configuration management
- [x] Implement database operations
- [x] Implement authentication
- [x] Create CLI framework
- [ ] Add comprehensive tests (current: ~35%, target: 80%+ coverage by Q2 2025)

### Phase 2: Migrate Music Tools ✅ COMPLETED

- [x] Update imports to use shared library
- [x] Remove duplicate code
- [x] Update configuration
- [x] Update tests
- [x] Verify functionality

### Phase 3: Setup Infrastructure ✅ COMPLETED

- [x] Create monorepo structure (apps/, packages/)
- [x] Configure workspace-level tools (pyproject.toml)
- [x] Setup CI/CD pipeline (.github/workflows/ci.yml)
- [x] Create comprehensive documentation

### Phase 4: Migrate Remaining Apps (IN PROGRESS)

- [ ] Migrate Tag Editor to use shared library
- [ ] Migrate EDM Scraper to use shared library
- [ ] Update all documentation
- [ ] Final verification and testing

### Phase 5: Optimization (PLANNED)

- [ ] Optimize CI/CD pipeline
- [ ] Setup code coverage reporting
- [ ] Implement automated releases
- [ ] Create developer onboarding guide

## Alternatives Considered

### Alternative 1: Separate Repositories with Shared Library

**Approach:** Keep apps in separate repositories, extract shared library to its own repository.

**Pros:**
- Apps remain independent
- Clear boundaries between projects
- Granular access control

**Cons:**
- Version synchronization challenges
- Complex dependency management
- Difficult to make atomic changes
- Requires multiple repository clones

**Why Rejected:** Complexity of managing multiple repositories outweighs benefits of separation.

### Alternative 2: Single Repository with No Structure

**Approach:** Keep all code in single flat structure without apps/packages separation.

**Pros:**
- Simple structure
- Everything in one place

**Cons:**
- Unclear boundaries
- No clear separation of concerns
- Difficult to understand dependencies
- Hard to maintain

**Why Rejected:** Lack of structure makes maintenance difficult and doesn't scale.

### Alternative 3: Multiple Repositories with Git Submodules

**Approach:** Separate repositories with shared library as git submodule.

**Pros:**
- Apps remain independent
- Shared code in one place

**Cons:**
- Git submodules are complex and error-prone
- Difficult to manage versions
- Poor developer experience
- Complex CI/CD setup

**Why Rejected:** Git submodules add complexity without significant benefits.

## References

- [Monorepo Tools](https://monorepo.tools/)
- [Google's Monorepo Philosophy](https://cacm.acm.org/magazines/2016/7/204032-why-google-stores-billions-of-lines-of-code-in-a-single-repository/fulltext)
- [Python Packaging Guide](https://packaging.python.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## Related ADRs

- ADR 002: CI/CD Pipeline Design (planned)
- ADR 003: Versioning Strategy (planned)
- ADR 004: Testing Strategy (planned)

## Notes

### Metrics After Implementation

**Code Reduction:**
- Music Tools: 65% reduction
- Tag Editor: Expected 50% reduction
- EDM Scraper: Expected 75% reduction

**Test Coverage:**
- packages/common: 90%+
- apps/music-tools: 75%
- Overall: 85%+

**Developer Feedback:**
- Positive: Easier to maintain, consistent structure
- Positive: Single setup process
- Positive: Atomic changes across projects
- Neutral: Initial learning curve

### Lessons Learned

1. **Start with Shared Library:** Create comprehensive shared library before migrating apps
2. **Comprehensive Testing:** High test coverage in shared library is critical
3. **Documentation is Key:** Good documentation reduces learning curve
4. **Gradual Migration:** Migrate apps one at a time, not all at once
5. **CI/CD Early:** Setup CI/CD early to catch issues quickly

### Future Considerations

1. **Microservices:** Consider breaking into microservices if scale requires
2. **Package Publishing:** Publish packages/common to PyPI if useful to others
3. **Automated Releases:** Implement semantic versioning and automated releases
4. **Performance Monitoring:** Add build and test performance monitoring
5. **Code Generation:** Create templates for new apps/packages

---

**Status:** Accepted
**Last Updated:** 2025-11-15
**Next Review:** 2026-01-15 (or when adding 4+ new applications)
