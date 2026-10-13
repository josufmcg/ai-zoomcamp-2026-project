# EFINGES - Functional Specification

This document outlines the functional requirements for **EFINGES**, a software solution designed to help property management firms efficiently manage residential communities, properties, resident communications, financials, and governance.

---

## 1. System Overview & Core Objectives

EFINGES streamlines residential property management by structuring communities into a clear hierarchy, managing individual billing and maintenance records, facilitating internal communication, and enabling democratic resident voting.

* **Target Users:** Property Management Firms (Administrators & Managers) and Residents.
* **Scope Limitation (v1):** Focuses strictly on core operational workflows. Contractors, automatic billing generation, and advanced automated analytics are excluded from this version.

---

## 2. User Roles & Permissions

The system defines three distinct user roles with specific access levels:

| Role | Description & Permissions |
| --- | --- |
| **Administrator** | • Full system-wide control.<br>

<br>• Manages user accounts across the firm.<br>

<br>• Oversees all properties and global reporting. |
| **Manager** | • Manages specific assigned properties, buildings, and units.<br>

<br>• Manages resident profiles and unit assignments.<br>

<br>• Creates and issues manual bills.<br>

<br>• Manages maintenance requests and communicates with residents.<br>

<br>• Creates initiatives and sets up voting parameters. |
| **Resident** | • Views profile and associated property information (apartments, garages, storage units).<br>

<br>• Submits and tracks maintenance requests (incidences).<br>

<br>• Views and checks bills per unit (Pending, Paid, Overdue).<br>

<br>• Votes on active community initiatives.<br>

<br>• Communicates with managers via maintenance request comment threads. |

---

## 3. Property Structure & Tagging System

### Property Hierarchy

* **Communities/Neighborhoods** comprise multiple **Buildings** (or blocks).
* Each Building contains multiple individual **Units** (Apartments, Garages, and Storage Units).
* **Resident Ownership/Tenancy:**
* A resident can own or be assigned multiple units (e.g., an apartment plus a garage and a storage unit).
* Units are managed and billed individually.



### Tagging System

* **Tag Assignment:** Managers can assign custom text tags to buildings or units (e.g., "Block A", "Downtown", "Phase 1").
* **Purpose:** Designed for data organization, grouping, and future metric analysis across multi-building developments.

---

## 4. Bill Management

* **Creation:** Bills are created **manually** by Managers for individual units.
* **Billing Structure:** Each unit receives its own bill (e.g., monthly rent, utilities, or maintenance charges are tracked separately per unit).
* **Bill Statuses:**
* `Pending`: Issued but not yet paid.
* `Paid`: Successfully settled.
* `Overdue`: Past the due date without payment.



---

## 5. Maintenance Requests (Incidences) & Communication

### Lifecycle

Residents can report issues related to their properties. The request lifecycle follows strict manager-controlled transitions:

1. `Submitted` (Logged by the resident)
2. `In Progress` (Acknowledged and being handled by the manager)
3. `Resolved` (Work completed by the manager)
4. `Closed` (Archived/Confirmed by the manager)

### Communication

* **Contextual Discussion:** To keep communication simple and auditable, direct messaging is restricted to comment threads embedded within each maintenance request.
* Managers and related residents exchange updates, questions, and clarifications directly inside the incidence thread.

---

## 6. Initiatives & Voting System

* **Creation:** Managers can create initiatives (e.g., community events, property upgrades, policy changes) and set multi-choice voting options (e.g., Yes/No/Abstain, or custom multi-choice answers).
* **Scoping:** Managers define the target audience/units eligible to vote for a given initiative (e.g., all units in Building A, or all garage owners).
* **Voting Weight:** Voting follows an **one vote per property unit** model. If a resident owns multiple eligible units within the initiative's scope, they receive a vote for each applicable unit.

---
