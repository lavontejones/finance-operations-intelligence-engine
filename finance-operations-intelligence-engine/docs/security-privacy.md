# Security and privacy notes

This repository contains invented company names, invented transactions, and invented amounts. It contains no customer, employee, bank, or client data.

For deployment, use least-privilege roles, single sign-on, multi-factor authentication, encrypted transport, encrypted storage, managed secrets, retention rules, backup restoration tests, and monitored audit logs. Do not store raw bank credentials in application configuration. Do not allow an LLM to make accounting decisions without deterministic validation, source evidence, and human approval.

The API demonstration has no authentication because it is local-only teaching code. Add authentication and authorization before any network deployment.
