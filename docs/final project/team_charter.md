# Team Charter: Real-Time Crypto Volatility Detection System

**Project:** Building a Production REST API for Crypto Volatility Prediction  
**Course:** Foundations of Operationalizing AI (CMU Heinz)  
**Timeline:** Week 4-7 (November 2025)  
**Team Size:** 5 Members

---

## 1. Project Vision

Transform the individual crypto volatility detection model (F1=0.9984) into a production-grade REST API service that can serve real-time predictions to downstream systems (dashboards, trading bots, alerting systems).

## 2. Team Roles & Responsibilities

### **Role 1: Tech Lead / API Architect**
**Primary Owner:** TBD  
**Responsibilities:**
- Overall system architecture and technical decisions
- FastAPI application design and endpoint specifications
- Code review and merge approvals
- Integration of all components (Kafka, MLflow, API)
- Performance optimization and bottleneck identification

**Deliverables:**
- API design documentation
- System architecture diagrams
- Technical decision records

---

### **Role 2: ML Engineer / Model Operations**
**Primary Owner:** TBD  
**Responsibilities:**
- Model selection and performance validation
- Model versioning and artifact management
- Feature engineering pipeline maintenance
- Model monitoring and drift detection
- MLflow integration and experiment tracking

**Deliverables:**
- Model card and performance reports
- Feature definitions and schemas
- Model retraining procedures
- Performance benchmarking results

---

### **Role 3: Data Engineer / Streaming Infrastructure**
**Primary Owner:** TBD  
**Responsibilities:**
- Kafka setup and topic management
- WebSocket to Kafka data ingestion
- Data quality validation
- Streaming pipeline monitoring
- Feature engineering computation

**Deliverables:**
- Kafka topic schemas
- Data quality reports
- Streaming pipeline documentation
- Performance metrics (throughput, latency)

---

### **Role 4: DevOps / Infrastructure Engineer**
**Primary Owner:** TBD  
**Responsibilities:**
- Docker containerization (Dockerfile, docker-compose)
- CI/CD pipeline setup
- Deployment automation
- Monitoring and alerting (Prometheus, Grafana)
- Infrastructure as Code (IaC)

**Deliverables:**
- Dockerfiles and compose configurations
- Deployment runbooks
- Monitoring dashboards
- Health check and alerting setup

---

### **Role 5: QA / Testing Lead**
**Primary Owner:** TBD  
**Responsibilities:**
- API testing strategy and test suites
- End-to-end integration testing
- Load testing and performance validation
- Documentation review and validation
- Bug tracking and regression testing

**Deliverables:**
- Test plans and test cases
- Automated test suites (unit, integration, load)
- Test coverage reports
- Bug reports and issue tracking

---

## 3. Communication Plan

### **Meeting Schedule**
- **Daily Standups:** 15 minutes, async (Slack/Teams)
  - What I did yesterday
  - What I'm doing today
  - Any blockers
  
- **Weekly Sync:** 1 hour, synchronous (Zoom/In-person)
  - Progress review against milestones
  - Demo current work
  - Plan next week's tasks
  - Resolve blockers

- **Sprint Reviews:** End of each week (Weeks 4, 5, 6, 7)
  - Demo to instructor/TA
  - Gather feedback
  - Adjust priorities

### **Communication Channels**
- **Slack/Teams:** Day-to-day coordination, quick questions
- **GitHub Issues:** Task tracking, bug reports, feature requests
- **GitHub PRs:** Code reviews (require 1 approval before merge)
- **Shared Docs:** Google Docs for collaborative writing
- **Email:** Official communications with instructor

### **Response Time Expectations**
- **Urgent (system down):** 2 hours
- **High priority (blocking work):** Same day
- **Normal priority:** Within 24 hours
- **Low priority:** Within 48 hours

---

## 4. Decision-Making Process

### **Technical Decisions**
- **Minor (library choice, code style):** Individual developer decides, notify team
- **Medium (API design, feature changes):** Tech Lead decides after team discussion
- **Major (architecture change, technology switch):** Team vote, majority rules

### **Conflict Resolution**
1. **Level 1:** Discuss 1-on-1 between affected parties
2. **Level 2:** Bring to Tech Lead for mediation
3. **Level 3:** Escalate to team vote
4. **Level 4:** Instructor arbitration (if team deadlocked)

---

## 5. Work Distribution & Ownership

### **Week 4: API Foundation** (Current Week)
| Component | Owner | Status |
|-----------|-------|--------|
| FastAPI endpoints | Role 1 | ✅ Complete |
| Model selection | Role 2 | ✅ Complete |
| Docker setup | Role 4 | ✅ Complete |
| API testing | Role 5 | ✅ Complete |
| Kafka infrastructure | Role 3 | ✅ Complete |

### **Week 5: Integration & Monitoring**
| Component | Owner | Status |
|-----------|-------|--------|
| Real-time prediction pipeline | Role 1 + 3 | 🔄 Planned |
| Prometheus metrics | Role 4 | 🔄 Planned |
| Model monitoring | Role 2 | 🔄 Planned |
| Load testing | Role 5 | 🔄 Planned |
| Documentation | All | 🔄 Planned |

### **Week 6: Optimization & Scaling**
| Component | Owner | Status |
|-----------|-------|--------|
| Performance tuning | Role 1 | 🔄 Planned |
| Batch prediction endpoint | Role 1 + 2 | 🔄 Planned |
| CI/CD pipeline | Role 4 | 🔄 Planned |
| Regression testing | Role 5 | 🔄 Planned |

### **Week 7: Final Polish & Presentation**
| Component | Owner | Status |
|-----------|-------|--------|
| Demo preparation | All | 🔄 Planned |
| Final documentation | All | 🔄 Planned |
| Presentation slides | Role 1 | 🔄 Planned |
| Video demo | Role 4 | 🔄 Planned |

---

## 6. Quality Standards

### **Code Quality**
- All code must pass linting (flake8, black)
- Unit tests required for new functions
- Code coverage target: 80%+
- PR reviews required before merge
- Descriptive commit messages

### **Documentation Standards**
- README for each major component
- Docstrings for all functions/classes
- API documentation (Swagger/OpenAPI)
- Architecture diagrams (Mermaid/draw.io)
- Runbooks for deployment/operations

### **Testing Standards**
- Unit tests: 80%+ coverage
- Integration tests: All critical paths
- Load tests: 100+ concurrent requests
- Health checks: All services monitored

---

## 7. Git Workflow

### **Branch Strategy**
- `main`: Production-ready code (protected)
- `develop`: Integration branch for week's work
- `feature/<name>`: Individual features
- `bugfix/<name>`: Bug fixes
- `hotfix/<name>`: Urgent production fixes

### **Commit Conventions**
```
<type>(<scope>): <subject>

Types: feat, fix, docs, test, refactor, chore
Examples:
  feat(api): add batch prediction endpoint
  fix(kafka): resolve consumer group lag
  docs(readme): update deployment instructions
```

### **PR Process**
1. Create feature branch from `develop`
2. Implement feature with tests
3. Open PR with description and test results
4. Request review from relevant role owner
5. Address review comments
6. Merge after approval (squash commits)

---

## 8. Risk Management

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Model performance degrades | High | Monitor metrics weekly, retrain if needed |
| API downtime | High | Health checks, auto-restart, redundancy |
| Team member unavailable | Medium | Cross-training, documentation |
| Scope creep | Medium | Weekly scope reviews, prioritize ruthlessly |
| Integration issues | Medium | Early integration testing, staging environment |
| Docker/Kafka issues | Medium | Backup local development setup |

---

## 9. Success Metrics

### **Technical Metrics**
- API uptime: 99%+
- Response latency: <100ms (p95)
- Model F1 score: >0.99
- Test coverage: 80%+
- Zero critical bugs in production

### **Team Metrics**
- All deliverables on time
- All team members contribute equally
- Code review turnaround: <24 hours
- Meeting attendance: 90%+

### **Learning Outcomes**
- Each member deploys to production at least once
- Each member conducts code review
- Each member presents in final demo
- Team completes retrospective with lessons learned

---

## 10. Team Agreement

By signing below, team members commit to:
- Completing assigned work on time
- Communicating proactively about blockers
- Reviewing others' code constructively
- Attending scheduled meetings
- Supporting teammates when needed
- Maintaining professional conduct

**Signatures:**

| Name | Role | Date | Signature |
|------|------|------|-----------|
| __________ | Tech Lead | ______ | __________ |
| __________ | ML Engineer | ______ | __________ |
| __________ | Data Engineer | ______ | __________ |
| __________ | DevOps | ______ | __________ |
| __________ | QA Lead | ______ | __________ |

---

## 11. Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-26 | 1.0 | Initial charter | Team |

---

**Last Updated:** November 26, 2025  
**Next Review:** December 3, 2025 (Week 5)
